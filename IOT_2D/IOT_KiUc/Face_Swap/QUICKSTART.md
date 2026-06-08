# 🚀 Quick Start Guide - Face Swap AI

Hướng dẫn nhanh để bắt đầu sử dụng hệ thống Face Swap AI

## ⏱️ 5 Phút Setup

### Windows

1. **Mở PowerShell/CMD** trong thư mục Face_Swap
2. **Chạy setup script**:
   ```bash
   .\setup.bat
   ```
3. **Download model**:
   - Tải từ: http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
   - Giải nén vào: `models/` folder
4. **Khởi động**:
   ```bash
   python app.py
   ```
5. **Mở browser**:
   - Truy cập: http://localhost:5000

### Linux/macOS

1. **Mở Terminal** trong thư mục Face_Swap
2. **Chạy setup script**:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```
3. **Download model**:
   ```bash
   cd models
   wget http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
   bzip2 -d shape_predictor_68_face_landmarks.dat.bz2
   cd ..
   ```
4. **Kích hoạt virtual environment**:
   ```bash
   source venv/bin/activate
   ```
5. **Khởi động**:
   ```bash
   python app.py
   ```
6. **Mở browser**:
   - Truy cập: http://localhost:5000

## 📸 Sử Dụng Web Interface

### Bước 1: Upload Ảnh Nguồn
- Nhấp vào **"Chọn ảnh nguồn..."**
- Chọn ảnh có khuôn mặt cần lấy
- Ảnh sẽ được hiển thị trong preview

### Bước 2: Upload Ảnh Đích
- Nhấp vào **"Chọn ảnh đích..."**
- Chọn ảnh có khuôn mặt cần thay thế
- Ảnh sẽ được hiển thị trong preview

### Bước 3: Thực Hiện Đổi Mặt
- Nhấp nút **"✨ Bắt Đầu Đổi Mặt"**
- Chờ xử lý (15-30 giây tùy cấu hình)
- Kết quả sẽ xuất hiện ở dưới

### Bước 4: Tải Hoặc Chia Sẻ
- **Tải Ảnh**: Nhấp **"⬇️ Tải Ảnh Kết Quả"**
- **Chia Sẻ**: Nhấp **"📤 Chia Sẻ"** (nếu hỗ trợ)

## 💻 Command Line Usage

### Cơ Bản

```bash
python main.py --source source.jpg --target target.jpg --output result.jpg
```

### Với Tùy Chọn

```bash
# Đơn giản
python main.py -s source.jpg -t target.jpg -o result.jpg

# Với GPU (nếu có)
python main.py -s source.jpg -t target.jpg -o result.jpg --gpu
```

## 🐍 Python API Usage

### Cơ Bản

```python
from face_swapper import FaceSwapper

# Khởi tạo
swapper = FaceSwapper()

# Đổi mặt từ files
swapper.swap_faces_from_files('source.jpg', 'target.jpg', 'result.jpg')
```

### Nâng Cao

```python
from advanced_face_swapper import AdvancedFaceSwapper
import cv2

# Khởi tạo
swapper = AdvancedFaceSwapper(use_gpu=False)

# Load ảnh
source = cv2.imread('source.jpg')
target = cv2.imread('target.jpg')

# Đổi mặt với các tùy chọn
result = swapper.swap_faces_advanced(
    source,
    target,
    blur_strength=1.0,
    blend_strength=1.0,
    color_correction=True,
    seamless=True
)

# Lưu kết quả
cv2.imwrite('result.jpg', result)
```

## 🔌 REST API Usage

### Curl Example

```bash
curl -X POST http://localhost:5000/api/swap-faces \
  -F "source_image=@source.jpg" \
  -F "target_image=@target.jpg" \
  > result.json
```

### JavaScript/Fetch

```javascript
const formData = new FormData();
formData.append('source_image', sourceFile);
formData.append('target_image', targetFile);

const response = await fetch('http://localhost:5000/api/swap-faces', {
    method: 'POST',
    body: formData
});

const data = await response.json();
console.log(data.image); // Base64 image
```

## 🐳 Docker Usage

### Build & Run

```bash
# Build image
docker build -t face-swap-ai .

# Run container
docker run -p 5000:5000 -v $(pwd)/uploads:/app/uploads -v $(pwd)/outputs:/app/outputs face-swap-ai
```

### Docker Compose

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f
```

## ⚠️ Lỗi Thường Gặp

### ❌ "No Python"
**Giải pháp**: Cài Python 3.8+ từ https://www.python.org/

### ❌ "dlib not found"
**Giải pháp**:
```bash
pip install --upgrade dlib
# hoặc
pip install dlib --no-binary dlib
```

### ❌ "Model not found"
**Giải pháp**:
1. Tạo thư mục `models/`
2. Download model từ: http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
3. Giải nén vào `models/`

### ❌ "No face detected"
**Giải pháp**:
- Ảnh cần có khuôn mặt rõ ràng, tối thiểu 50x50 pixels
- Thử ảnh khác hoặc tăng độ sáng

### ❌ "Connection refused"
**Giải pháp**:
- Đảm bảo Flask server đang chạy
- Kiểm tra port 5000 không bị chiếm dụng
- Thử restart server

## 📊 Hiệu Suất Tỷ Chiểu

| Ảnh | CPU i5 | GPU GTX 1080 |
|-----|--------|-------------|
| 1080p | 15-30s | 2-5s |
| 720p | 5-10s | 1-2s |
| 480p | 2-5s | <1s |

## 💡 Tips & Tricks

### Tối Ưu Hóa Tốc Độ
1. Giảm kích thước ảnh
2. Sử dụng GPU nếu có
3. Chạy một process lúc một

### Cải Thiện Chất Lượng
1. Sử dụng ảnh chất lượng cao
2. Bật color correction
3. Sử dụng seamless blending
4. Đảm bảo khuôn mặt rõ ràng

### Debugging
1. Kiểm tra console log
2. Xem file log: `face_swap.log`
3. Chạy examples.py để test

## 📚 Tài Liệu Thêm

- [README.md](README.md) - Hướng dẫn đầy đủ
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Cấu trúc dự án
- [API Documentation](README.md#-api-documentation) - API endpoints
- [examples.py](examples.py) - Code examples

## 🎯 Tiếp Theo

1. ✅ Setup và khởi động
2. ✅ Thử upload ảnh test
3. ✅ Xem kết quả
4. 📖 Đọc README đầy đủ
5. 🔧 Tùy chỉnh theo nhu cầu

## 📞 Hỗ Trợ

Nếu gặp vấn đề:
1. Kiểm tra [README.md](README.md)
2. Xem [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
3. Chạy examples.py
4. Kiểm tra console errors

---

**Happy Face Swapping! 🎭**
