# 🎭 Hệ Thống Đổi Mặt AI (Face Swap)

Công nghệ Face Swap tiên tiến sử dụng trí tuệ nhân tạo cho ứng dụng MC Ảo

## 📋 Mục Lục

- [Tính Năng](#tính-năng)
- [Yêu Cầu Hệ Thống](#yêu-cầu-hệ-thống)
- [Cài Đặt](#cài-đặt)
- [Cách Sử Dụng](#cách-sử-dụng)
- [API Documentation](#api-documentation)
- [Kiến Trúc Dự Án](#kiến-trúc-dự-án)
- [Công Nghệ Sử Dụng](#công-nghệ-sử-dụng)
- [Xử Lý Sự Cố](#xử-lý-sự-cố)

## ✨ Tính Năng

- ✅ **Đổi Mặt Tự Động**: Thay thế khuôn mặt trong ảnh/video
- ✅ **Phát Hiện Khuôn Mặt**: Tự động phát hiện và phân tích khuôn mặt
- ✅ **Ghép Mặt Thông Minh**: Trộn mặt một cách tự nhiên với biến dạng affine
- ✅ **API RESTful**: Dễ dàng tích hợp vào các ứng dụng khác
- ✅ **Web Interface**: Giao diện web thân thiện để sử dụng trực tiếp
- ✅ **Hỗ Trợ Nhiều Định Dạng**: PNG, JPG, JPEG, BMP, GIF
- ✅ **Xử Lý Lô**: Có khả năng xử lý nhiều ảnh cùng lúc
- ✅ **Tối Ưu Hiệu Suất**: Hỗ trợ GPU (nếu có)

## 🖥️ Yêu Cầu Hệ Thống

### Phần Cứng
- **CPU**: Intel i5 hoặc tương đương (tối thiểu)
- **RAM**: 8GB (tối thiểu), 16GB (khuyến nghị)
- **GPU**: NVIDIA CUDA-enabled (tùy chọn, để tăng tốc độ)
- **Ổ Cứng**: 5GB không gian trống

### Phần Mềm
- Python 3.8+
- pip hoặc conda package manager
- Modern web browser (Chrome, Firefox, Edge, Safari)

## 📦 Cài Đặt

### 1. Clone hoặc Download Dự Án

```bash
cd Face_Swap
```

### 2. Tạo Virtual Environment (Khuyến Nghị)

**Trên Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Trên macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Cài Đặt Dependencies

```bash
pip install -r requirements.txt
```

### 4. Download Model dlib

Cần tải model `shape_predictor_68_face_landmarks.dat`:

```bash
# Tạo thư mục models
mkdir models

# Download model (khoảng 100MB)
# Từ: http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
# Giải nén vào thư mục models/
```

Hoặc sử dụng Python:
```python
import dlib
# Model sẽ được tải tự động lần đầu tiên
```

## 🚀 Cách Sử Dụng

### Phương Pháp 1: Web Interface

#### Khởi Động Server

```bash
# Bước 1: Khởi động Flask Backend
python app.py
# Server sẽ chạy tại: http://localhost:5000

# Bước 2 (Terminal khác): Mở file index.html trong trình duyệt
# Hoặc truy cập: http://localhost:5000
```

#### Sử Dụng Giao Diện Web

1. Nhấp vào **"Chọn ảnh nguồn..."** để chọn ảnh có khuôn mặt cần lấy
2. Nhấp vào **"Chọn ảnh đích..."** để chọn ảnh có khuôn mặt cần thay thế
3. Nhấp nút **"Bắt Đầu Đổi Mặt"**
4. Đợi xử lý hoàn tất
5. Tải ảnh kết quả hoặc chia sẻ

### Phương Pháp 2: Command Line

```bash
# Cú pháp cơ bản
python main.py --source source.jpg --target target.jpg --output result.jpg

# Ví dụ
python main.py -s mc1.jpg -t mc2.jpg -o mc_swapped.jpg

# Với tùy chọn GPU (nếu có)
python main.py -s source.jpg -t target.jpg -o result.jpg --gpu
```

### Phương Pháp 3: Python Script

```python
from face_swapper import FaceSwapper

# Khởi tạo
swapper = FaceSwapper()

# Đổi mặt từ files
swapper.swap_faces_from_files('source.jpg', 'target.jpg', 'result.jpg')

# Hoặc từ OpenCV Mat
import cv2
source = cv2.imread('source.jpg')
target = cv2.imread('target.jpg')
result = swapper.swap_faces(source, target)
cv2.imwrite('result.jpg', result)
```

## 📡 API Documentation

### Base URL
```
http://localhost:5000/api
```

### Endpoints

#### 1. Health Check
```http
GET /api/health
```

**Response:**
```json
{
  "status": "ok",
  "message": "Face Swap API is running",
  "version": "1.0.0"
}
```

#### 2. Swap Faces (File Upload)
```http
POST /api/swap-faces
Content-Type: multipart/form-data
```

**Parameters:**
- `source_image` (file): Ảnh nguồn
- `target_image` (file): Ảnh đích

**Response:**
```json
{
  "success": true,
  "message": "Đổi mặt thành công",
  "image": "data:image/jpeg;base64,..."
}
```

**Example cURL:**
```bash
curl -X POST http://localhost:5000/api/swap-faces \
  -F "source_image=@source.jpg" \
  -F "target_image=@target.jpg"
```

#### 3. Swap Faces (Base64)
```http
POST /api/swap-faces-advanced
Content-Type: application/json
```

**Parameters:**
```json
{
  "source_image": "data:image/jpeg;base64,...",
  "target_image": "data:image/jpeg;base64,...",
  "blur_strength": 0.5,
  "blend_strength": 0.8
}
```

#### 4. Detect Faces
```http
POST /api/detect-faces
Content-Type: multipart/form-data
```

**Parameters:**
- `image` (file): Ảnh để phát hiện khuôn mặt

**Response:**
```json
{
  "success": true,
  "face_count": 2,
  "faces": [
    {
      "id": 0,
      "x": 100,
      "y": 150,
      "width": 200,
      "height": 250
    }
  ]
}
```

## 📁 Kiến Trúc Dự Án

```
Face_Swap/
├── app.py                          # Flask backend chính
├── face_swapper.py                 # Lớp xử lý face swap
├── main.py                         # CLI interface
├── index.html                      # Giao diện web
├── app.js                          # JavaScript frontend
├── style.css                       # CSS styling
├── requirements.txt                # Python dependencies
├── models/                         # Thư mục models
│   └── shape_predictor_68_face_landmarks.dat
├── uploads/                        # Thư mục upload tạm
├── outputs/                        # Thư mục output kết quả
└── README.md                       # File hướng dẫn (file này)
```

## 🛠️ Công Nghệ Sử Dụng

### Backend
- **Python 3.8+**: Ngôn ngữ lập trình chính
- **OpenCV**: Xử lý ảnh
- **dlib**: Phát hiện khuôn mặt và landmark detection
- **face_recognition**: Nhận diện khuôn mặt
- **NumPy/SciPy**: Xử lý số học
- **Flask**: Web framework

### Frontend
- **HTML5**: Cấu trúc trang
- **CSS3**: Styling với gradient, animation
- **JavaScript (ES6+)**: Interactivity và API calls
- **FileReader API**: Xử lý upload ảnh
- **Canvas API**: Xử lý ảnh phía client

### Khác
- **Pillow**: Xử lý ảnh
- **scikit-image**: Xử lý ảnh nâng cao

## 🔧 Xử Lý Sự Cố

### Lỗi: "RuntimeError: Could not find dlib"

**Giải pháp:**
```bash
pip install --upgrade dlib
# Hoặc build từ source
pip install dlib --no-binary dlib
```

### Lỗi: "Shape Predictor Model not found"

**Giải pháp:**
1. Tạo thư mục `models`
2. Download file từ: http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
3. Giải nén vào thư mục `models/`

### Lỗi: "No face detected"

**Giải pháp:**
- Đảm bảo khuôn mặt rõ ràng và chiếm ít nhất 50x50 pixels
- Kiểm tra độ sáng của ảnh
- Thử các ảnh khác

### Lỗi: "CORS error" trong Web UI

**Giải pháp:**
- Đảm bảo Flask server đang chạy
- Kiểm tra URL: `http://localhost:5000`
- Xóa cache browser hoặc dùng Incognito mode

### Lỗi: Xử lý chậm

**Giải pháp:**
- Giảm kích thước ảnh trước khi xử lý
- Sử dụng GPU nếu có
- Tăng RAM hệ thống
- Chạy chỉ một process lúc một

## 📊 Hiệu Năng

| Ảnh | Độ Phân Giải | CPU (i5) | GPU (GTX 1080) |
|-----|-------------|---------|----------------|
| 1080p | 1920x1080 | 15-30s | 2-5s |
| 720p | 1280x720 | 5-10s | 1-2s |
| 480p | 854x480 | 2-5s | 0.5-1s |

*Thời gian xử lý có thể khác nhau tùy vào hệ thống*

## 📝 Ghi Chú Quan Trọng

1. **Đạo Đức Sử Dụng**: Chỉ sử dụng để giải trí hoặc mục đích hợp pháp
2. **Quyền Riêng Tư**: Tuân thủ quy định về bảo vệ dữ liệu cá nhân
3. **Hiệu Suất**: Hiệu suất tùy thuộc vào chất lượng ảnh và cấu hình hệ thống
4. **Khuôn Mặt Một Mặt**: Hiện tại hỗ trợ thay thế một khuôn mặt tại một thời điểm

## 🤝 Đóng Góp

Nếu bạn muốn cải thiện dự án này:
1. Fork dự án
2. Tạo branch mới
3. Commit thay đổi
4. Push đến branch
5. Mở Pull Request

## 📄 Giấy Phép

Dự án này được phát hành dưới giấy phép MIT.

## 👨‍💻 Tác Giả

Hệ Thống Face Swap AI - 2024

## 📞 Hỗ Trợ

Nếu gặp vấn đề, vui lòng:
1. Kiểm tra file README này
2. Xem xét lỗi trong console
3. Tìm kiếm trên GitHub Issues

---

**Made with ❤️ for MC Ảo**

Last Updated: 2024
