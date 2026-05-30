"""
Utility functions for Face Swap System
Các hàm tiện ích cho hệ thống Face Swap
"""

import os
import cv2
import numpy as np
from PIL import Image
import base64
import io
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageUtils:
    """Công cụ xử lý ảnh"""
    
    @staticmethod
    def resize_image(image, max_width=1280, max_height=720):
        """
        Thay đổi kích thước ảnh với giữ nguyên tỷ lệ
        
        Args:
            image: Ảnh OpenCV
            max_width: Chiều rộng tối đa
            max_height: Chiều cao tối đa
        
        Returns:
            resized_image: Ảnh đã thay đổi kích thước
        """
        height, width = image.shape[:2]
        
        if width > max_width or height > max_height:
            scale = min(max_width / width, max_height / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        return image
    
    @staticmethod
    def enhance_contrast(image, alpha=1.2, beta=10):
        """
        Tăng độ tương phản của ảnh
        
        Args:
            image: Ảnh đầu vào
            alpha: Độ tương phản (1.0 = không thay đổi, > 1.0 = tăng)
            beta: Độ sáng
        
        Returns:
            enhanced: Ảnh được tăng cường
        """
        enhanced = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
        return enhanced
    
    @staticmethod
    def apply_gaussian_blur(image, kernel_size=5):
        """
        Áp dụng bộ lọc Gaussian blur
        
        Args:
            image: Ảnh đầu vào
            kernel_size: Kích thước kernel
        
        Returns:
            blurred: Ảnh đã blur
        """
        return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
    
    @staticmethod
    def crop_face_region(image, face_box, margin=10):
        """
        Cắt vùng mặt từ ảnh
        
        Args:
            image: Ảnh đầu vào
            face_box: (x, y, width, height)
            margin: Biên mở rộng
        
        Returns:
            cropped: Ảnh vùng mặt
        """
        x, y, w, h = face_box
        x1 = max(0, x - margin)
        y1 = max(0, y - margin)
        x2 = min(image.shape[1], x + w + margin)
        y2 = min(image.shape[0], y + h + margin)
        
        return image[y1:y2, x1:x2]
    
    @staticmethod
    def draw_face_boxes(image, faces, color=(0, 255, 0), thickness=2):
        """
        Vẽ hộp quanh các khuôn mặt
        
        Args:
            image: Ảnh đầu vào
            faces: Danh sách face boxes
            color: Màu (BGR)
            thickness: Độ dày đường
        
        Returns:
            drawn: Ảnh với hộp đã vẽ
        """
        drawn = image.copy()
        for face in faces:
            x, y, w, h = face
            cv2.rectangle(drawn, (x, y), (x + w, y + h), color, thickness)
        
        return drawn


class FileUtils:
    """Công cụ xử lý file"""
    
    @staticmethod
    def ensure_directory(directory):
        """
        Đảm bảo thư mục tồn tại, nếu không thì tạo
        
        Args:
            directory: Đường dẫn thư mục
        
        Returns:
            bool: True nếu thành công
        """
        try:
            os.makedirs(directory, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Lỗi tạo thư mục: {e}")
            return False
    
    @staticmethod
    def get_file_size(file_path):
        """
        Lấy kích thước file (MB)
        
        Args:
            file_path: Đường dẫn file
        
        Returns:
            float: Kích thước file (MB)
        """
        try:
            size_bytes = os.path.getsize(file_path)
            return size_bytes / (1024 * 1024)
        except Exception as e:
            logger.error(f"Lỗi lấy kích thước file: {e}")
            return 0
    
    @staticmethod
    def cleanup_old_files(directory, max_age_hours=24):
        """
        Dọn dẹp các file cũ trong thư mục
        
        Args:
            directory: Đường dẫn thư mục
            max_age_hours: Tuổi tối đa của file (giờ)
        
        Returns:
            int: Số file đã xóa
        """
        import time
        
        count = 0
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        try:
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > max_age_seconds:
                        os.remove(file_path)
                        count += 1
                        logger.info(f"Xóa file cũ: {filename}")
        except Exception as e:
            logger.error(f"Lỗi dọn dẹp file: {e}")
        
        return count


class Base64Utils:
    """Công cụ xử lý Base64"""
    
    @staticmethod
    def encode_image_to_base64(image_path):
        """
        Mã hóa ảnh từ file thành Base64
        
        Args:
            image_path: Đường dẫn ảnh
        
        Returns:
            str: Base64 string
        """
        try:
            with open(image_path, 'rb') as img_file:
                return base64.b64encode(img_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Lỗi mã hóa ảnh: {e}")
            return None
    
    @staticmethod
    def decode_base64_to_image(base64_string):
        """
        Giải mã Base64 thành ảnh OpenCV
        
        Args:
            base64_string: Base64 string
        
        Returns:
            image: OpenCV image hoặc None
        """
        try:
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]
            
            img_data = base64.b64decode(base64_string)
            img = Image.open(io.BytesIO(img_data))
            
            # Chuyển PIL image thành OpenCV
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        except Exception as e:
            logger.error(f"Lỗi giải mã Base64: {e}")
            return None
    
    @staticmethod
    def image_to_base64_with_mime(image, format='jpeg'):
        """
        Chuyển đổi OpenCV image thành Base64 với MIME type
        
        Args:
            image: OpenCV image
            format: Format ảnh (jpeg, png)
        
        Returns:
            str: Data URL
        """
        try:
            _, buffer = cv2.imencode(f'.{format}', image)
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            return f'data:image/{format};base64,{img_base64}'
        except Exception as e:
            logger.error(f"Lỗi tạo data URL: {e}")
            return None


class ValidationUtils:
    """Công cụ xác thực"""
    
    @staticmethod
    def is_valid_image(image_path, allowed_extensions=None):
        """
        Kiểm tra xem file có phải ảnh hợp lệ không
        
        Args:
            image_path: Đường dẫn ảnh
            allowed_extensions: Danh sách đuôi được phép
        
        Returns:
            bool: True nếu hợp lệ
        """
        if allowed_extensions is None:
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
        
        if not os.path.exists(image_path):
            return False
        
        _, ext = os.path.splitext(image_path)
        return ext.lower() in allowed_extensions
    
    @staticmethod
    def validate_image_size(image_path, max_size_mb=50):
        """
        Kiểm tra kích thước ảnh
        
        Args:
            image_path: Đường dẫn ảnh
            max_size_mb: Kích thước tối đa (MB)
        
        Returns:
            bool: True nếu hợp lệ
        """
        size_mb = FileUtils.get_file_size(image_path)
        return size_mb <= max_size_mb
    
    @staticmethod
    def validate_image_dimensions(image_path, min_width=100, min_height=100):
        """
        Kiểm tra kích thước ảnh (pixel)
        
        Args:
            image_path: Đường dẫn ảnh
            min_width: Chiều rộng tối thiểu
            min_height: Chiều cao tối thiểu
        
        Returns:
            bool: True nếu hợp lệ
        """
        try:
            img = cv2.imread(image_path)
            if img is None:
                return False
            
            height, width = img.shape[:2]
            return width >= min_width and height >= min_height
        except Exception as e:
            logger.error(f"Lỗi kiểm tra kích thước: {e}")
            return False


class PerformanceUtils:
    """Công cụ đo lường hiệu suất"""
    
    @staticmethod
    def measure_time(func, *args, **kwargs):
        """
        Đo thời gian thực thi của hàm
        
        Args:
            func: Hàm cần đo
            *args, **kwargs: Tham số hàm
        
        Returns:
            tuple: (kết quả, thời gian tính bằng giây)
        """
        import time
        
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        return result, end_time - start_time
    
    @staticmethod
    def get_memory_usage():
        """
        Lấy thông tin sử dụng RAM hiện tại
        
        Returns:
            dict: Thông tin RAM
        """
        import psutil
        
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        
        return {
            'rss_mb': mem_info.rss / (1024 * 1024),  # Resident Set Size
            'vms_mb': mem_info.vms / (1024 * 1024),  # Virtual Memory Size
            'percent': process.memory_percent()
        }


# Backward compatibility
__all__ = [
    'ImageUtils',
    'FileUtils',
    'Base64Utils',
    'ValidationUtils',
    'PerformanceUtils',
    'logger'
]
