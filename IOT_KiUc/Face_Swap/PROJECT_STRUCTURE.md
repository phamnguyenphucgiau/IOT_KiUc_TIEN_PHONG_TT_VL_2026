# 📁 Cấu Trúc Dự Án Face Swap AI

Hướng dẫn chi tiết về cấu trúc thư mục và mục đích của từng file trong dự án.

## 📋 Sơ Đồ Thư Mục

```
Face_Swap/
│
├── 📄 Core Python Files (Các file Python chính)
│   ├── app.py                          # Flask API server chính
│   ├── face_swapper.py                 # Lớp Face Swapper cơ bản
│   ├── advanced_face_swapper.py        # Face Swapper nâng cao
│   ├── main.py                         # CLI interface
│   └── utils.py                        # Các hàm tiện ích
│
├── 🌐 Frontend Files (Các file giao diện web)
│   ├── index.html                      # Trang HTML chính
│   ├── app.js                          # JavaScript logic
│   └── style.css                       # CSS styling
│
├── 📦 Configuration Files (Các file cấu hình)
│   ├── requirements.txt                # Python dependencies
│   ├── config.ini                      # Cấu hình ứng dụng
│   └── .gitignore                      # Git ignore rules
│
├── 🐳 Deployment Files (Các file deployment)
│   ├── Dockerfile                      # Container image
│   ├── docker-compose.yml              # Docker compose config
│   ├── setup.bat                       # Windows setup script
│   └── setup.sh                        # Linux/macOS setup script
│
├── 📚 Documentation (Tài liệu)
│   ├── README.md                       # File hướng dẫn chính
│   └── PROJECT_STRUCTURE.md            # File này
│
├── 📁 Directories (Thư mục)
│   ├── models/                         # Thư mục chứa AI models
│   │   └── shape_predictor_68_face_landmarks.dat
│   ├── uploads/                        # Ảnh upload tạm thời
│   ├── outputs/                        # Ảnh kết quả
│   └── __pycache__/                    # Python cache (auto)
│
└── 📄 Virtual Environment (Tự động tạo)
    └── venv/                           # Python virtual environment
```

## 📄 Mô Tả Chi Tiết Các File

### Core Python Files

#### `app.py` - Flask API Server
- **Chức Năng**: Máy chủ Flask chính, xử lý API requests
- **Endpoints**:
  - `GET /api/health` - Kiểm tra trạng thái
  - `POST /api/swap-faces` - Đổi mặt từ file upload
  - `POST /api/swap-faces-advanced` - Đổi mặt nâng cao (Base64)
  - `POST /api/detect-faces` - Phát hiện khuôn mặt
- **Sử Dụng**: `python app.py`

#### `face_swapper.py` - Basic Face Swapper Class
- **Chức Năng**: Lớp cơ bản để thực hiện face swap
- **Phương Thức Chính**:
  - `swap_faces()` - Đổi mặt
  - `swap_faces_from_files()` - Đổi mặt từ files
  - `get_face_mask()` - Tạo mặt nạ
  - `warp_face()` - Biến dạng khuôn mặt
  - `blend_faces()` - Trộn khuôn mặt
- **Thư Viện**: OpenCV, dlib, NumPy

#### `advanced_face_swapper.py` - Advanced Features
- **Chức Năng**: Phiên bản nâng cao với tính năng bổ sung
- **Tính Năng**:
  - Color correction (Hiệu chỉnh màu)
  - Seamless cloning (Ghép không ranh)
  - Batch processing (Xử lý lô)
  - Enhanced mask (Mặt nạ nâng cao)
- **Phương Thức**: `swap_faces_advanced()`, `seamless_clone()`, `color_correct()`

#### `main.py` - Command Line Interface
- **Chức Năng**: Interface dòng lệnh để xử lý face swap
- **Cách Dùng**: 
  ```bash
  python main.py --source source.jpg --target target.jpg --output result.jpg
  ```
- **Tùy Chọn**:
  - `-s, --source` - Ảnh nguồn
  - `-t, --target` - Ảnh đích
  - `-o, --output` - File output
  - `--gpu` - Sử dụng GPU

#### `utils.py` - Utility Functions
- **Lớp**:
  - `ImageUtils` - Xử lý ảnh
  - `FileUtils` - Xử lý file
  - `Base64Utils` - Xử lý Base64
  - `ValidationUtils` - Xác thực
  - `PerformanceUtils` - Đo hiệu suất

### Frontend Files

#### `index.html` - Main Web Interface
- **Chức Năng**: Giao diện web chính
- **Thành Phần**:
  - Header với tiêu đề
  - Upload section (2 ảnh)
  - Control buttons
  - Loading indicator
  - Result display
  - Error messages
  - Footer

#### `app.js` - Frontend Logic
- **Chức Năng**: Xử lý frontend interactions
- **Hàm Chính**:
  - `handleSourceImageSelect()` - Xử lý chọn ảnh nguồn
  - `handleTargetImageSelect()` - Xử lý chọn ảnh đích
  - `handleSwapFaces()` - Gọi API đổi mặt
  - `handleDownload()` - Tải ảnh kết quả
  - `handleShare()` - Chia sẻ ảnh
- **Tính Năng**: Drag & drop, preview, error handling

#### `style.css` - Styling
- **Chức Năng**: Tất cả styling cho web interface
- **Tính Năng**:
  - Responsive design
  - Gradient backgrounds
  - Animations
  - Dark/Light compatibility
  - Mobile optimization

### Configuration Files

#### `requirements.txt` - Python Dependencies
- Flask, OpenCV, dlib, NumPy, Pillow, v.v.
- Cài đặt: `pip install -r requirements.txt`

#### `config.ini` - Application Configuration
- Cấu hình server, processing, upload, models, logging
- Định dạng INI cho dễ đọc và tùy chỉnh

#### `.gitignore` - Git Ignore Rules
- Loại trừ __pycache__, venv, uploads, models, logs, v.v.

### Deployment Files

#### `Dockerfile` - Docker Container Definition
- Base image: `python:3.9-slim`
- Cài đặt dependencies, copy files, expose port 5000
- Health check kích hoạt

#### `docker-compose.yml` - Docker Compose Orchestration
- Dịch vụ: `face-swap-api`
- Volumes cho uploads, outputs, models
- Network configuration

#### `setup.bat` - Windows Setup Script
- Tạo venv, cài pip packages, tạo thư mục

#### `setup.sh` - Linux/macOS Setup Script
- Tương tự setup.bat nhưng cho Unix-like systems

### Documentation

#### `README.md` - Main Documentation
- Hướng dẫn cài đặt, sử dụng, API documentation
- Troubleshooting, performance notes

#### `PROJECT_STRUCTURE.md` - This File
- Giải thích chi tiết cấu trúc dự án

## 🔄 Luồng Xử Lý

### Web Interface Flow
```
1. User chọn source image → index.html
2. User chọn target image → index.html
3. Click "Bắt Đầu Đổi Mặt" → app.js
4. app.js gửi POST /api/swap-faces → app.py
5. app.py xử lý → face_swapper.py
6. Kết quả trả về Base64 → app.js
7. Hiển thị trong browser
```

### CLI Flow
```
1. python main.py --source A --target B → main.py
2. Parse arguments
3. Khởi tạo FaceSwapper
4. Gọi swap_faces_from_files() → face_swapper.py
5. Lưu result vào output file
```

### API Flow
```
POST /api/swap-faces
↓
Validate files
↓
Save temporary
↓
Load images (OpenCV)
↓
face_swapper.swap_faces()
↓
Encode result (Base64)
↓
Return JSON response
↓
Clean up temp files
```

## 📊 Kích Thước File Điển Hình

| File | Kích Thước | Ghi Chú |
|------|----------|--------|
| models/shape_predictor... | ~100 MB | Download riêng |
| app.py | ~10 KB | Flask server |
| face_swapper.py | ~8 KB | Core logic |
| advanced_face_swapper.py | ~12 KB | Enhanced features |
| index.html | ~5 KB | Web interface |
| style.css | ~8 KB | Styling |
| app.js | ~6 KB | Frontend logic |
| Dockerfile | ~1 KB | Container def |

## 🔧 Mở Rộng Dự Án

### Thêm Tính Năng Mới

1. **Image Processing**:
   - Thêm hàm mới trong `utils.py` → `ImageUtils`
   - Hoặc tạo file `image_processing.py` mới

2. **API Endpoints**:
   - Thêm route mới trong `app.py`
   - Tạo endpoint mới và xử lý

3. **Frontend**:
   - Thêm HTML elements trong `index.html`
   - Thêm CSS trong `style.css`
   - Thêm JavaScript event handlers trong `app.js`

4. **Advanced Algorithms**:
   - Mở rộng `advanced_face_swapper.py`
   - Thêm phương thức mới

## 📝 Lưu Ý Quan Trọng

1. **Models Directory**: Cần download model dlib (~100MB)
2. **Virtual Environment**: Luôn sử dụng venv để tránh xung đột
3. **Temporary Files**: Upload tự động được dọn dẹp
4. **Large Images**: Tự động resize để tối ưu hiệu suất
5. **GPU Support**: Optional, nếu có NVIDIA CUDA

## 🚀 Quick Start Checklist

- [ ] Clone/Download dự án
- [ ] Chạy `setup.bat` (Windows) hoặc `setup.sh` (Linux/macOS)
- [ ] Download dlib model vào `models/`
- [ ] Chạy `python app.py`
- [ ] Mở `http://localhost:5000` trong browser
- [ ] Upload ảnh và thử Face Swap!

---

Last Updated: 2024
