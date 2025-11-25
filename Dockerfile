
# Use specific version of nvidia cuda image
FROM wlsdml1114/multitalk-base:1.7 as runtime

# Install dependencies và tools
RUN apt-get update && apt-get install -y wget curl && \
    rm -rf /var/lib/apt/lists/* && \
    pip install -U "huggingface_hub[hf_transfer]" && \
    pip install --no-cache-dir runpod websocket-client

# Set working directory
WORKDIR /

# Clone ComfyUI và install dependencies
RUN git clone https://github.com/comfyanonymous/ComfyUI.git && \
    cd ComfyUI && \
    pip install --no-cache-dir -r requirements.txt && \
    cd /ComfyUI/custom_nodes/ && \
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git && \
    cd ComfyUI-Manager && \
    pip install --no-cache-dir -r requirements.txt && \
    cd /ComfyUI/custom_nodes/ && \
    git clone https://github.com/kijai/ComfyUI-KJNodes && \
    cd ComfyUI-KJNodes && \
    pip install --no-cache-dir -r requirements.txt

# Download models (parallel downloads để tăng tốc)
RUN mkdir -p /ComfyUI/models/diffusion_models /ComfyUI/models/loras /ComfyUI/models/text_encoders /ComfyUI/models/vae && \
    wget -q https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_edit_2509_fp8_e4m3fn.safetensors -O /ComfyUI/models/diffusion_models/qwen_image_edit_2509_fp8_e4m3fn.safetensors & \
    wget -q https://huggingface.co/lightx2v/Qwen-Image-Lightning/resolve/main/Qwen-Image-Lightning-4steps-V1.0.safetensors -O /ComfyUI/models/loras/Qwen-Image-Lightning-4steps-V1.0.safetensors & \
    wget -q https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors -O /ComfyUI/models/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors & \
    wget -q https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors -O /ComfyUI/models/vae/qwen_image_vae.safetensors && \
    wait

COPY . .
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
