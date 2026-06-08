# 🔧 Face Swap Lỗi - Hướng Dẫn Sửa

## 📋 Vấn Đề Phát Hiện

Lỗi "Face swap failed" từ `app_face_swap.py` được gây bởi các vấn đề sau:

### 1. **Đường Dẫn Tương Đối (Relative Paths) trong `config.py`**
   - **Vấn đề**: File `config.py` sử dụng đường dẫn tương đối như `"./face_swap/weights/..."` thay vì đường dẫn tuyệt đối
   - **Nguyên nhân**: Khi subprocess chạy, thư mục hiện tại có thể khác so với thư mục chứa models
   - **Kết quả**: Models không được tìm thấy, dẫn đến lỗi import

### 2. **Thiếu sys.path Mapping trong Python Subprocess**
   - **Vấn đề**: `run_local_swap.py` import từ `config` và `face_swap.face_swap` nhưng backend directory không được thêm vào `sys.path`
   - **Nguyên nhân**: Module import có thể thất bại nếu Python không biết backend directory ở đâu
   - **Kết quả**: Import errors, subprocess thất bại

### 3. **Model Loading tại Module Import Time**
   - **Vấn đề**: `face_swap.py` tải tất cả models tại thời điểm import (module level)
   - **Nguyên nhân**: Nếu models không tìm được, toàn bộ import sẽ thất bại mà không có thông báo lỗi chi tiết
   - **Kết quả**: Không rõ nguyên nhân lỗi, khó debug

### 4. **GPU Context Issue (ctx_id=1)**
   - **Vấn đề**: `retinaface_det_model.prepare(ctx_id=1)` giả định GPU khả dụng
   - **Nguyên nhân**: Hệ thống có thể chỉ có CPU
   - **Kết quả**: Model preparation thất bại trên CPU-only systems

---

## ✅ Các Sửa Chữa Đã Thực Hiện

### File 1: `Video-Face-Swap/backend/config.py`
**Thay đổi**:
- ✓ Sử dụng đường dẫn tuyệt đối dựa trên vị trí script
- ✓ Thêm validation kiểm tra models có tồn tại không
- ✓ Thêm cảnh báo nếu models không tìm được

```python
# ❌ Trước
UPLOAD_FOLDER = "./uploaded_videos"
RETINAFACE_MODEL_PATH = "./face_swap/weights/det_10g.onnx"

# ✅ Sau
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BACKEND_DIR, "uploaded_videos")
RETINAFACE_MODEL_PATH = os.path.join(BACKEND_DIR, "face_swap/weights/det_10g.onnx")
```

---

### File 2: `Video-Face-Swap/backend/run_local_swap.py`
**Thay đổi**:
- ✓ Thêm backend directory vào `sys.path`
- ✓ Thêm try-except wrapper cho exception handling
- ✓ Thêm traceback để debug

```python
# ✅ Thêm vào đầu file
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# ✅ Thêm error handling
if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
```

---

### File 3: `Video-Face-Swap/backend/face_swap/face_swap.py`
**Thay đổi**:
- ✓ Thêm sys.path mapping
- ✓ Model loading với error handling (không fail toàn bộ import)
- ✓ Thay đổi `ctx_id=1` thành `ctx_id=0` (dùng cho CPU/mặc định)
- ✓ Thêm validation kiểm tra models trước khi sử dụng

```python
# ✅ Model loading with error handling
try:
    print("⏳ Loading RetinaFace model...")
    retinaface_det_model = RetinaFace(RETINAFACE_MODEL_PATH, providers=PROVIDERS)
    retinaface_det_model.prepare(ctx_id=0, input_size=(640, 640), det_thresh=0.5)
    print("✓ RetinaFace model loaded")
except Exception as e:
    print(f"❌ Error loading RetinaFace model: {e}")
    retinaface_det_model = None

# ✅ Validation in crop_faces()
def crop_faces(video_path: str, uid: str):
    if retinaface_det_model is None:
        raise RuntimeError("RetinaFace model failed to load. Cannot detect faces.")
```

---

## 🚀 Cách Kiểm Tra

### 1. Chạy Backend Directly (Debug)
```bash
cd Video-Face-Swap/backend
python run_local_swap.py \
    --source-face "path/to/face.jpg" \
    --target-video "path/to/video.mp4" \
    --output-video "output.mp4"
```

### 2. Chạy Flask App
```bash
python app_face_swap.py
```
Truy cập: `http://localhost:5001`

### 3. Kiểm Tra Logs
Xem output của subprocess để tìm thông báo lỗi chi tiết:
- ✅ `✓ RetinaFace model loaded` = Model tải thành công
- ❌ `❌ Error loading RetinaFace model` = Vấn đề models
- ❌ `No faces were detected` = Không tìm thấy khuôn mặt

---

## 📦 Yêu Cầu Dependencies

Đảm bảo các packages được cài:
```bash
pip install opencv-python numpy onnx onnxruntime scikit-image
```

Kiểm tra models tồn tại:
```
Video-Face-Swap/backend/face_swap/weights/
  ├── det_10g.onnx ✓
  ├── w600k_r50.onnx ✓
  ├── inswapper_128.onnx ✓
  └── gfpgan_1.4.onnx ✓
```

---

## 🔍 Troubleshooting

### Lỗi: "Video-Face-Swap backend not found"
→ Kiểm tra folder `Video-Face-Swap` tồn tại

### Lỗi: "No faces were detected"
→ Video không có khuôn mặt, hoặc khuôn mặt quá nhỏ (< 80x80px)

### Lỗi: "Model loading failed"
→ Models bị thiếu, kiểm tra thư mục weights

### Lỗi: "Unable to read video"
→ Format video không support, thử MP4 thay vì AVI

### Memory Error
→ Video quá dài, thử video ngắn hơn để test

---

## 📝 Tóm Tắt

| Vấn Đề | Lỗi | Sửa |
|--------|------|-----|
| Đường dẫn tương đối | Models not found | Dùng absolute paths |
| sys.path không có backend | Import errors | Thêm sys.path.insert |
| Model loading không handle lỗi | Unclear failures | Thêm try-except |
| ctx_id=1 cho CPU | GPU context error | Đổi thành ctx_id=0 |

✅ **Tất cả các vấn đề đã được sửa!**
