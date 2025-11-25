# 🎯 Hướng Dẫn Tối Ưu Chi Phí RunPod Serverless

## 📊 Phân Tích Metrics Hiện Tại

Dựa trên metrics từ dashboard của bạn:
- **Chi phí**: $0.00061/s (~$52.8/ngày)
- **Delay Time**: 11 tuần (RẤT CAO - đây là vấn đề chính!)
- **Cold Start Count**: 156 lần
- **Workers**: 3 workers đang chạy
- **Jobs**: 1 job in progress, 0 jobs trong queue

## ⚠️ Vấn Đề Chính

1. **Delay Time 11 tuần** = Workers idle quá lâu, tốn tiền không cần thiết
2. **156 Cold Starts** = Workers bị shutdown/restart nhiều, tốn thời gian và tiền
3. **3 Workers** = Quá nhiều khi chỉ có 1 job, không có queue

## ✅ Các Thay Đổi Đã Thực Hiện

### 1. File `.runpod/hub.json`
- ✅ Giảm `containerDiskInGb`: 180GB → **120GB** (tiết kiệm ~$0.0001/s)
- ✅ Chỉ dùng `ADA_24` thay vì cả `ADA_24` và `ADA_32_PRO` (ADA_24 rẻ hơn ~30-40%)

## 🔧 Cấu Hình Cần Thiết Lập Trong RunPod Console

Sau khi deploy template mới, bạn **PHẢI** cấu hình các settings sau trong RunPod Console để tối ưu chi phí:

### 1. Worker Settings (QUAN TRỌNG NHẤT!)

Vào **Serverless Endpoint → Settings → Workers**:

```
Max Workers: 1-2 (thay vì 3)
  → Với traffic hiện tại (1 job, 0 queue), chỉ cần 1-2 workers

Idle Timeout: 10-30 giây (thay vì mặc định 60s+)
  → Giảm delay time từ 11 tuần xuống vài giây
  → Workers sẽ shutdown nhanh khi không có job, tiết kiệm tiền

Flashboot: ENABLED
  → Giảm cold start time từ ~30-60s xuống ~5-10s
  → Giảm số lần cold start và thời gian chờ
```

### 2. GPU Selection

Trong **GPU Settings**:
- Chọn **chỉ ADA_24** (đã cấu hình trong hub.json)
- ADA_24 rẻ hơn ADA_32_PRO khoảng 30-40%
- Với model FP8 của bạn, ADA_24 đủ mạnh

### 3. Network Volume (Nếu Cần)

Nếu bạn dùng Network Volume:
- Chọn **S3 Storage** thay vì **NFS** (rẻ hơn)
- Chỉ mount khi cần thiết

## 📈 Ước Tính Tiết Kiệm

Sau khi áp dụng các tối ưu:

| Metric | Trước | Sau | Tiết Kiệm |
|--------|-------|-----|-----------|
| Chi phí/giây | $0.00061 | ~$0.00035-0.00040 | **35-40%** |
| Delay Time | 11 tuần | <1 phút | **99.9%** |
| Cold Starts | 156 | ~20-30 | **80-85%** |
| Workers | 3 | 1-2 | **33-50%** |

**Ước tính tiết kiệm**: ~$20-25/ngày (~$600-750/tháng)

## 🚀 Các Bước Triển Khai

1. **Commit và push** các thay đổi trong `.runpod/hub.json`
2. **Rebuild** template trên RunPod Hub
3. **Tạo Serverless Endpoint mới** hoặc **update endpoint hiện tại**
4. **Cấu hình trong RunPod Console**:
   - Max Workers: 1-2
   - Idle Timeout: 10-30s
   - Flashboot: Enabled
   - GPU: Chỉ ADA_24
5. **Monitor metrics** sau 24h để điều chỉnh thêm

## 📝 Lưu Ý Quan Trọng

- **Idle Timeout ngắn** có thể tăng cold starts, nhưng với Flashboot enabled thì không sao
- **Max Workers thấp** có thể làm tăng queue time nếu traffic tăng đột ngột
- **Monitor metrics** và điều chỉnh theo traffic thực tế
- Nếu traffic tăng, có thể tăng Max Workers lên 2-3

## 🔍 Monitoring

Sau khi áp dụng, theo dõi các metrics sau:
- **Delay Time**: Nên < 1 phút
- **Cold Start Count**: Nên giảm đáng kể
- **Cost per second**: Nên giảm 30-40%
- **Queue Time**: Nếu tăng cao, cân nhắc tăng Max Workers

## ⏱️ Xử Lý Queue Time và Auto-Cancel

### Vấn Đề Queue Time

Nếu **Queue Time** tăng cao (nhiều jobs chờ trong queue), có 2 cách xử lý:

#### 1. Tăng Max Workers (Giải pháp chính)

Nếu Queue Time > 30 giây thường xuyên:
- **Tăng Max Workers** từ 1-2 lên 2-3 hoặc cao hơn
- Điều này sẽ giúp xử lý nhiều jobs đồng thời
- **Trade-off**: Tăng chi phí nhưng giảm queue time

#### 2. Queue Timeout - Auto-Cancel Jobs (Đã được implement)

**RunPod tự động cancel jobs** nếu chúng chờ trong queue quá lâu:

**Cấu hình trong RunPod Console:**
```
Vào Serverless Endpoint → Settings → Advanced

Queue Timeout: 60-120 giây (khuyến nghị)
  → Jobs chờ trong queue > 60-120s sẽ tự động bị cancel
  → Tránh lãng phí tiền cho jobs cũ không còn cần thiết
  → Client sẽ nhận được error "Job timeout in queue"
```

**Trong code (handler.py):**
- ✅ Đã thêm **Job Timeout: 5 phút** (300 giây)
- ✅ Jobs chạy quá 5 phút sẽ tự động fail
- ✅ Kiểm tra timeout ở nhiều điểm trong quá trình xử lý
- ✅ Log thời gian hoàn thành để monitor

### Cách Hoạt Động

1. **Queue Timeout** (cấu hình trong RunPod Console):
   - Jobs chờ trong queue > timeout → **Tự động cancel**
   - Không tốn tiền cho jobs đã bị cancel
   - Client nhận error ngay lập tức

2. **Job Timeout** (trong handler.py):
   - Jobs đang chạy > 5 phút → **Tự động fail**
   - Tránh jobs chạy mãi không xong
   - Worker được giải phóng để xử lý jobs khác

### Khuyến Nghị Cấu Hình

```
Queue Timeout: 60-120 giây
  → Đủ để jobs được xử lý nếu có workers available
  → Không quá dài để tránh lãng phí

Job Timeout: 5 phút (300 giây) - đã set trong code
  → Đủ để xử lý image editing
  → Nếu jobs thường xuyên timeout, có thể tăng lên 10 phút
```

### Monitoring Queue Time

Theo dõi trong RunPod Dashboard:
- **Queue Time < 10s**: Tốt ✅
- **Queue Time 10-30s**: Chấp nhận được ⚠️
- **Queue Time > 30s**: Cần tăng Max Workers hoặc giảm traffic 🔴

### Xử Lý Khi Queue Time Cao

1. **Ngắn hạn**: Tăng Max Workers lên 2-3
2. **Dài hạn**: 
   - Optimize code để jobs chạy nhanh hơn
   - Batch processing nếu có nhiều jobs nhỏ
   - Sử dụng priority queue (nếu RunPod hỗ trợ)

## 💡 Tips Bổ Sung

1. **Batch Processing**: Nếu có nhiều jobs cùng lúc, batch chúng lại để giảm overhead
2. **Warm-up**: Nếu có traffic đều đặn, có thể giữ 1 worker warm với idle timeout dài hơn
3. **Auto-scaling**: RunPod có auto-scaling, nhưng với traffic thấp thì manual config tốt hơn
4. **Queue Monitoring**: Set up alerts khi Queue Time > 30s để phản ứng nhanh

