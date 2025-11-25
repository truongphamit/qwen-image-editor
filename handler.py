
import runpod
from runpod.serverless.utils import rp_upload
import os
import websocket
import base64
import json
import uuid
import logging
import urllib.request
import urllib.parse
import binascii  # Base64 에러 처리를 위해 import
import subprocess
import time
from functools import lru_cache


# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CUDA 검사 및 설정


def check_cuda_availability():
    """CUDA 사용 가능 여부를 확인하고 환경 변수를 설정합니다."""
    try:
        import torch
        if torch.cuda.is_available():
            logger.info("✅ CUDA is available and working")
            os.environ['CUDA_VISIBLE_DEVICES'] = '0'
            return True
        else:
            logger.error("❌ CUDA is not available")
            raise RuntimeError("CUDA is required but not available")
    except Exception as e:
        logger.error(f"❌ CUDA check failed: {e}")
        raise RuntimeError(f"CUDA initialization failed: {e}")


# CUDA 검사 실행
try:
    cuda_available = check_cuda_availability()
    if not cuda_available:
        raise RuntimeError("CUDA is not available")
except Exception as e:
    logger.error(f"Fatal error: {e}")
    logger.error("Exiting due to CUDA requirements not met")
    exit(1)


server_address = os.getenv('SERVER_ADDRESS', '127.0.0.1')

# Cache workflow JSON để tránh đọc file mỗi lần


@lru_cache(maxsize=2)
def load_workflow_cached(workflow_path):
    """Load workflow với caching"""
    with open(workflow_path, 'r') as file:
        return json.load(file)


def queue_prompt(prompt, client_id):
    """Queue prompt với client_id"""
    url = f"http://{server_address}:8188/prompt"
    logger.info(f"Queueing prompt to: {url}")
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(url, data=data)
    return json.loads(urllib.request.urlopen(req).read())


def get_image(filename, subfolder, folder_type):
    url = f"http://{server_address}:8188/view"
    logger.info(f"Getting image from: {url}")
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen(f"{url}?{url_values}") as response:
        return response.read()


def get_history(prompt_id):
    url = f"http://{server_address}:8188/history/{prompt_id}"
    logger.info(f"Getting history from: {url}")
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read())


def get_images(ws, prompt, client_id):
    """Get images từ ComfyUI workflow với timeout handling"""
    prompt_id = queue_prompt(prompt, client_id)['prompt_id']
    output_images = {}

    # Wait for execution to complete với timeout
    max_wait_time = 240  # 4 phút max cho execution
    start_time = time.time()

    while True:
        # Check timeout
        if time.time() - start_time > max_wait_time:
            raise Exception(f"Workflow execution timeout sau {max_wait_time}s")

        try:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        break
        except websocket.WebSocketTimeoutException:
            raise Exception("WebSocket timeout trong khi chờ execution")
        except Exception as e:
            logger.warning(f"Error receiving WebSocket message: {e}")
            continue

    history = get_history(prompt_id)[prompt_id]
    for node_id in history['outputs']:
        node_output = history['outputs'][node_id]
        images_output = []
        if 'images' in node_output:
            for image in node_output['images']:
                image_data = get_image(
                    image['filename'], image['subfolder'], image['type'])
                # bytes 객체를 base64로 인코딩하여 JSON 직렬화 가능하게 변환
                if isinstance(image_data, bytes):
                    image_data = base64.b64encode(image_data).decode('utf-8')
                images_output.append(image_data)
        output_images[node_id] = images_output

    return output_images


def load_workflow(workflow_path):
    """Load workflow sử dụng cache"""
    return load_workflow_cached(workflow_path)

# ------------------------------
# 입력 처리 유틸 (path/url/base64)
# ------------------------------


def process_input(input_data, temp_dir, output_filename, input_type):
    """입력 데이터를 처리하여 파일 경로를 반환하는 함수
    - input_type: "path" | "url" | "base64"
    """
    if input_type == "path":
        logger.info(f"📁 경로 입력 처리: {input_data}")
        return input_data
    elif input_type == "url":
        logger.info(f"🌐 URL 입력 처리: {input_data}")
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.abspath(os.path.join(temp_dir, output_filename))
        return download_file_from_url(input_data, file_path)
    elif input_type == "base64":
        logger.info("🔢 Base64 입력 처리")
        return save_base64_to_file(input_data, temp_dir, output_filename)
    else:
        raise Exception(f"지원하지 않는 입력 타입: {input_type}")


def download_file_from_url(url, output_path):
    """URL에서 파일을 다운로드하는 함수"""
    try:
        result = subprocess.run([
            'wget', '-O', output_path, '--no-verbose', url
        ], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"✅ URL에서 파일을 성공적으로 다운로드했습니다: {url} -> {output_path}")
            return output_path
        else:
            logger.error(f"❌ wget 다운로드 실패: {result.stderr}")
            raise Exception(f"URL 다운로드 실패: {result.stderr}")
    except subprocess.TimeoutExpired:
        logger.error("❌ 다운로드 시간 초과")
        raise Exception("다운로드 시간 초과")
    except Exception as e:
        logger.error(f"❌ 다운로드 중 오류 발생: {e}")
        raise Exception(f"다운로드 중 오류 발생: {e}")


def save_base64_to_file(base64_data, temp_dir, output_filename):
    """Base64 데이터를 파일로 저장하는 함수"""
    try:
        decoded_data = base64.b64decode(base64_data)
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.abspath(os.path.join(temp_dir, output_filename))
        with open(file_path, 'wb') as f:
            f.write(decoded_data)
        logger.info(f"✅ Base64 입력을 '{file_path}' 파일로 저장했습니다.")
        return file_path
    except (binascii.Error, ValueError) as e:
        logger.error(f"❌ Base64 디코딩 실패: {e}")
        raise Exception(f"Base64 디코딩 실패: {e}")


def handler(job):
    """
    Handler function với timeout và queue time checking
    """
    job_input = job.get("input", {})
    job_id = job.get("id", "unknown")

    # Kiểm tra nếu job đã bị cancel (RunPod sẽ tự động cancel jobs trong queue quá lâu)
    # RunPod sẽ không gọi handler nếu job đã bị cancel, nhưng ta vẫn check để chắc chắn
    logger.info(f"Processing job {job_id}")
    logger.info(f"Received job input: {job_input}")

    # Validate input sớm để fail fast
    required_fields = ["prompt", "seed", "width", "height"]
    missing_fields = [
        field for field in required_fields if field not in job_input]
    if missing_fields:
        raise ValueError(f"Missing required fields: {missing_fields}")

    # Timeout cho toàn bộ job (5 phút = 300 giây)
    # Nếu job chạy quá lâu, sẽ raise exception và RunPod sẽ mark job là failed
    job_start_time = time.time()
    JOB_TIMEOUT_SECONDS = 300  # 5 phút

    # Tạo client_id mới cho mỗi job để tránh WebSocket conflicts
    client_id = str(uuid.uuid4())
    task_id = f"task_{uuid.uuid4()}"

    # ------------------------------
    # 이미지 입력 수집 (1개 또는 2개)
    # 지원 키: image_path | image_url | image_base64
    #         image_path_2 | image_url_2 | image_base64_2
    # ------------------------------
    image1_path = None
    image2_path = None

    if "image_path" in job_input:
        image1_path = process_input(
            job_input["image_path"], task_id, "input_image_1.jpg", "path")
    elif "image_url" in job_input:
        image1_path = process_input(
            job_input["image_url"], task_id, "input_image_1.jpg", "url")
    elif "image_base64" in job_input:
        image1_path = process_input(
            job_input["image_base64"], task_id, "input_image_1.jpg", "base64")

    if "image_path_2" in job_input:
        image2_path = process_input(
            job_input["image_path_2"], task_id, "input_image_2.jpg", "path")
    elif "image_url_2" in job_input:
        image2_path = process_input(
            job_input["image_url_2"], task_id, "input_image_2.jpg", "url")
    elif "image_base64_2" in job_input:
        image2_path = process_input(
            job_input["image_base64_2"], task_id, "input_image_2.jpg", "base64")

    if image2_path:
        workflow_path = "/qwen_image_edit_2.json"
    else:
        workflow_path = "/qwen_image_edit_1.json"

    prompt = load_workflow(workflow_path)

    prompt["78"]["inputs"]["image"] = image1_path
    if image2_path:
        prompt["123"]["inputs"]["image"] = image2_path

    prompt["111"]["inputs"]["prompt"] = job_input["prompt"]

    prompt["3"]["inputs"]["seed"] = job_input["seed"]
    prompt["128"]["inputs"]["value"] = job_input["width"]
    prompt["129"]["inputs"]["value"] = job_input["height"]

    # Kiểm tra timeout trước khi tiếp tục
    elapsed_time = time.time() - job_start_time
    if elapsed_time > JOB_TIMEOUT_SECONDS:
        raise Exception(
            f"Job timeout sau {elapsed_time:.1f}s (giới hạn: {JOB_TIMEOUT_SECONDS}s)")

    ws_url = f"ws://{server_address}:8188/ws?clientId={client_id}"
    logger.info(f"Connecting to WebSocket: {ws_url}")

    # 먼저 HTTP 연결이 가능한지 확인
    http_url = f"http://{server_address}:8188/"
    logger.info(f"Checking HTTP connection to: {http_url}")

    # HTTP 연결 확인 (최대 1분, nhưng check timeout mỗi lần)
    max_http_attempts = 60  # Giảm từ 180 xuống 60 để nhanh hơn
    for http_attempt in range(max_http_attempts):
        # Kiểm tra timeout
        elapsed_time = time.time() - job_start_time
        if elapsed_time > JOB_TIMEOUT_SECONDS:
            raise Exception(
                f"Job timeout trong khi chờ HTTP connection ({elapsed_time:.1f}s)")

        try:
            response = urllib.request.urlopen(http_url, timeout=5)
            logger.info(f"HTTP 연결 성공 (시도 {http_attempt+1})")
            break
        except Exception as e:
            logger.warning(
                f"HTTP 연결 실패 (시도 {http_attempt+1}/{max_http_attempts}): {e}")
            if http_attempt == max_http_attempts - 1:
                raise Exception("ComfyUI 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
            time.sleep(1)

    # Kiểm tra timeout trước khi connect WebSocket
    elapsed_time = time.time() - job_start_time
    if elapsed_time > JOB_TIMEOUT_SECONDS:
        raise Exception(
            f"Job timeout trước khi connect WebSocket ({elapsed_time:.1f}s)")

    ws = websocket.WebSocket()
    # 웹소켓 연결 시도 (최대 2분, giảm từ 3 phút)
    max_attempts = int(120/5)  # 2 phút (mỗi 5 giây thử 1 lần)
    for attempt in range(max_attempts):
        # Kiểm tra timeout mỗi lần thử
        elapsed_time = time.time() - job_start_time
        if elapsed_time > JOB_TIMEOUT_SECONDS:
            raise Exception(
                f"Job timeout trong khi chờ WebSocket connection ({elapsed_time:.1f}s)")

        try:
            ws.connect(ws_url)
            logger.info(f"웹소켓 연결 성공 (시도 {attempt+1})")
            break
        except Exception as e:
            logger.warning(f"웹소켓 연결 실패 (시도 {attempt+1}/{max_attempts}): {e}")
            if attempt == max_attempts - 1:
                raise Exception("웹소켓 연결 시간 초과 (2 phút)")
            time.sleep(5)

    # Kiểm tra timeout trước khi xử lý images
    elapsed_time = time.time() - job_start_time
    if elapsed_time > JOB_TIMEOUT_SECONDS:
        ws.close()
        raise Exception(
            f"Job timeout trước khi xử lý images ({elapsed_time:.1f}s)")

    try:
        images = get_images(ws, prompt, client_id)
    finally:
        ws.close()

    # Log thời gian hoàn thành
    total_time = time.time() - job_start_time
    logger.info(f"Job {job_id} hoàn thành trong {total_time:.1f}s")

    # Cleanup temp files (nếu có)
    try:
        import shutil
        temp_dir = f"/tmp/{task_id}" if os.path.exists(
            f"/tmp/{task_id}") else None
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.debug(f"Cleaned up temp directory: {temp_dir}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temp files: {e}")

    # 이미지가 없는 경우 처리
    if not images:
        return {"error": "이미지를 생성할 수 없습니다."}

    # 첫 번째 이미지 반환
    for node_id in images:
        if images[node_id]:
            return {"image": images[node_id][0]}

    return {"error": "이미지를 찾을 수 없습니다."}


# Cấu hình RunPod serverless với timeout
# Job timeout: 5 phút (300 giây) - jobs chạy quá lâu sẽ bị cancel
# Queue timeout được cấu hình trong RunPod Console (xem OPTIMIZATION_GUIDE.md)
runpod.serverless.start({
    "handler": handler,
    # Có thể thêm các config khác ở đây nếu RunPod SDK hỗ trợ
})
