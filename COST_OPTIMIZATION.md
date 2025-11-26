# 💰 Hướng Dẫn Tối Ưu Chi Phí - Giảm Xuống < $0.01/Ảnh

## 📊 Phân Tích Chi Phí Hiện Tại

### Tình Trạng Hiện Tại:
- **Số workers**: 2 workers
- **Chi phí/worker**: $0.00019/s
- **Chi phí tổng**: 2 × $0.00019/s = **$0.00038/s**
- **Execution time trung bình**: ~30-40 giây (từ metrics)
- **Chi phí/ảnh hiện tại**: $0.00038/s × 35s = **~$0.0133/ảnh** ❌

### Mục Tiêu:
- **Chi phí/ảnh**: < **$0.01/ảnh** ✅

## ✅ Các Tối Ưu Đã Thực Hiện

### 1. Giảm Steps Từ 4 Xuống 3 ⭐⭐⭐⭐⭐

**Thay đổi:**
- ✅ `qwen_image_edit_1.json`: `steps: 4` → `steps: 3`
- ✅ `qwen_image_edit_2.json`: `steps: 4` → `steps: 3`

**Tác động:**
- Giảm execution time ~25% (từ 35s xuống ~26s)
- Chất lượng vẫn tốt với Lightning LoRA 4-steps (có thể chạy với 3 steps)
- Không cần thay đổi model

**Tiết kiệm**: ~25% execution time → ~25% chi phí

### 2. Cấu Hình RunPod Console (CẦN THỰC HIỆN)

#### A. Giảm Số Workers Từ 2 Xuống 1 ⭐⭐⭐⭐⭐

**Cách thực hiện:**
1. Vào **RunPod Console → Serverless Endpoint → Settings → Workers**
2. Đặt **Max Workers: 1** (thay vì 2)

**Tác động:**
- Giảm chi phí idle 50% (chỉ 1 worker chạy khi không có job)
- Với traffic hiện tại (1 job, 0 queue), 1 worker đủ
- Nếu traffic tăng, có thể tăng lại lên 2

**Tiết kiệm**: 50% chi phí idle

#### B. Giảm Idle Timeout ⭐⭐⭐⭐

**Cách thực hiện:**
1. Vào **Serverless Endpoint → Settings → Workers**
2. Đặt **Idle Timeout: 10-30 giây** (thay vì mặc định 60s+)

**Tác động:**
- Workers shutdown nhanh khi không có job
- Giảm chi phí idle time
- Với Flashboot enabled, cold start chỉ ~5-10s

**Tiết kiệm**: Giảm delay time và idle cost

#### C. Bật Flashboot ⭐⭐⭐⭐

**Cách thực hiện:**
1. Vào **Serverless Endpoint → Settings → Advanced**
2. Bật **Flashboot: ENABLED**

**Tác động:**
- Giảm cold start time từ ~30-60s xuống ~5-10s
- Giảm số lần cold start
- Giảm thời gian chờ khi có job mới

## 📈 Tính Toán Chi Phí Mới

### Scenario 1: Chỉ Giảm Steps (Giữ 2 Workers)

**Chi phí:**
- Workers: 2 × $0.00019/s = $0.00038/s
- Execution time: ~26s (giảm 25% từ 35s)
- **Chi phí/ảnh**: $0.00038/s × 26s = **$0.00988/ảnh** ✅ (< $0.01)

**Tiết kiệm**: ~26% (từ $0.0133 xuống $0.00988)

### Scenario 2: Giảm Steps + Giảm Workers Xuống 1 (KHUYẾN NGHỊ) ⭐⭐⭐⭐⭐

**Chi phí:**
- Workers: 1 × $0.00019/s = $0.00019/s
- Execution time: ~26s (giảm 25% từ 35s)
- **Chi phí/ảnh**: $0.00019/s × 26s = **$0.00494/ảnh** ✅✅ (< $0.01)

**Tiết kiệm**: ~63% (từ $0.0133 xuống $0.00494)

### Scenario 3: Chỉ Giảm Workers (Giữ 4 Steps)

**Chi phí:**
- Workers: 1 × $0.00019/s = $0.00019/s
- Execution time: ~35s (giữ nguyên)
- **Chi phí/ảnh**: $0.00019/s × 35s = **$0.00665/ảnh** ✅ (< $0.01)

**Tiết kiệm**: ~50% (từ $0.0133 xuống $0.00665)

## 🎯 Khuyến Nghị Thực Hiện

### Bước 1: Deploy Code Mới (Đã Hoàn Thành) ✅

1. ✅ Đã giảm steps từ 4 xuống 3 trong cả 2 workflow files
2. Commit và push code
3. Rebuild template trên RunPod Hub
4. Deploy endpoint mới hoặc update endpoint hiện tại

### Bước 2: Cấu Hình RunPod Console (QUAN TRỌNG!)

Sau khi deploy, **PHẢI** cấu hình trong RunPod Console:

```
1. Max Workers: 1 (thay vì 2)
2. Idle Timeout: 10-30 giây
3. Flashboot: ENABLED
```

### Bước 3: Test và Monitor

1. Test với một vài images để đảm bảo chất lượng OK
2. Monitor metrics sau 24h:
   - Chi phí/ảnh: Nên < $0.01
   - Execution time: Nên giảm ~25%
   - Queue time: Nếu tăng cao, cân nhắc tăng Max Workers lên 2

## 📊 So Sánh Chi Phí

| Scenario | Workers | Steps | Execution Time | Chi Phí/Ảnh | Tiết Kiệm |
|----------|---------|-------|----------------|-------------|-----------|
| **Hiện tại** | 2 | 4 | ~35s | $0.0133 | Baseline |
| **Chỉ giảm steps** | 2 | 3 | ~26s | $0.00988 | 26% ✅ |
| **Chỉ giảm workers** | 1 | 4 | ~35s | $0.00665 | 50% ✅ |
| **Cả hai (KHUYẾN NGHỊ)** | 1 | 3 | ~26s | **$0.00494** | **63%** ✅✅ |

## ⚠️ Lưu Ý Quan Trọng

### 1. Chất Lượng Ảnh
- Lightning LoRA 4-steps có thể chạy tốt với 3 steps
- Nếu chất lượng giảm đáng kể, có thể tăng lại lên 4 steps
- Test với sample images trước khi deploy production

### 2. Traffic và Queue Time
- Nếu traffic tăng đột ngột, có thể tăng Max Workers lên 2
- Monitor Queue Time: Nếu > 30s thường xuyên → tăng workers
- Với Flashboot enabled, cold start nhanh nên không lo lắng về delay

### 3. Balance Chi Phí vs Chất Lượng
- **$0.00494/ảnh** (1 worker + 3 steps): Tối ưu nhất về chi phí
- **$0.00665/ảnh** (1 worker + 4 steps): Cân bằng tốt giữa chi phí và chất lượng
- **$0.00988/ảnh** (2 workers + 3 steps): Nếu cần xử lý nhiều jobs đồng thời

## 🚀 Kết Luận

**Khuyến nghị ngay**: 
1. ✅ **Đã giảm steps từ 4 xuống 3** (code đã được update)
2. ⚠️ **Cần cấu hình RunPod Console**: Giảm Max Workers xuống 1

**Kết quả mong đợi:**
- Chi phí/ảnh: **$0.00494** (< $0.01) ✅
- Tiết kiệm: **~63%** so với hiện tại
- Chất lượng: Vẫn tốt với Lightning LoRA

**Nếu cần chất lượng cao hơn:**
- Giữ 4 steps nhưng giảm workers xuống 1 → **$0.00665/ảnh** (vẫn < $0.01)

