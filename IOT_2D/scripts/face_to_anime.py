#!/usr/bin/env python3
"""
Convert portrait photo to anime 2D face and prepare for Live2D integration
"""

import cv2
import numpy as np
import os
import sys
from pathlib import Path

# Try to import PIL for better image handling
try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import torch
    from torchvision import transforms
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


def convert_to_anime_simple(image_path, output_path, style="cartoon"):
    """
    Convert portrait to anime style using OpenCV filters
    This is a fallback method that works without deep learning
    """
    print(f"[*] Loading image: {image_path}")
    img = cv2.imread(image_path)
    
    if img is None:
        print(f"[ERROR] Cannot load image: {image_path}")
        return False
    
    # Get original dimensions
    height, width = img.shape[:2]
    print(f"[*] Image size: {width}x{height}")
    
    # Convert to RGB for processing
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Apply bilateral filter for cartoon effect
    print("[*] Applying cartoon effect...")
    img_smooth = cv2.bilateralFilter(img_rgb, 9, 75, 75)
    
    # Detect edges
    img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(img_gray, 100, 200)
    edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
    
    # Reduce colors for anime effect
    data = img_smooth.reshape((-1, 3))
    data = np.float32(data)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    ret, label, center = cv2.kmeans(data, 8, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    center = np.uint8(center)
    img_color_reduced = center[label.flatten()]
    img_color_reduced = img_color_reduced.reshape(img_smooth.shape)
    
    # Combine smooth colors with edges
    img_cartoon = cv2.subtract(img_color_reduced, edges)
    
    # Enhance colors
    lab = cv2.cvtColor(img_cartoon, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    img_result = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    
    # Save output
    print(f"[*] Saving anime version to: {output_path}")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img_bgr = cv2.cvtColor(img_result, cv2.COLOR_RGB2BGR)
    cv2.imwrite(output_path, img_bgr)
    
    return True


def extract_face_region(image_path, output_path):
    """
    Extract and focus on face region
    """
    print(f"[*] Extracting face region...")
    img = cv2.imread(image_path)
    
    if img is None:
        print(f"[ERROR] Cannot load image: {image_path}")
        return False
    
    # Load face cascade classifier
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    
    if len(faces) == 0:
        print("[!] No face detected, using full image")
        return False
    
    # Get the largest face
    (x, y, w, h) = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)[0]
    
    # Expand region slightly
    expand = int(0.1 * max(w, h))
    x = max(0, x - expand)
    y = max(0, y - expand)
    w = min(img.shape[1] - x, w + 2 * expand)
    h = min(img.shape[0] - y, h + 2 * expand)
    
    face_img = img[y:y+h, x:x+w]
    
    print(f"[*] Face region extracted: {w}x{h}")
    print(f"[*] Saving face region to: {output_path}")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, face_img)
    
    return True


def upscale_image(image_path, output_path, scale=2):
    """
    Upscale image for better quality
    """
    print(f"[*] Upscaling image by {scale}x...")
    img = cv2.imread(image_path)
    
    if img is None:
        return False
    
    height, width = img.shape[:2]
    img_upscaled = cv2.resize(img, (width * scale, height * scale), 
                               interpolation=cv2.INTER_CUBIC)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, img_upscaled)
    
    return True


def main():
    # Define paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    input_image = project_root / "anh1.jpg"
    
    # Output directories
    output_dir = project_root / "processed_faces"
    output_dir.mkdir(exist_ok=True)
    
    anime_output = output_dir / "anh1_anime.jpg"
    face_output = output_dir / "anh1_face.jpg"
    face_anime_output = output_dir / "anh1_face_anime.jpg"
    upscaled_output = output_dir / "anh1_face_anime_upscaled.jpg"
    
    # Check if input exists
    if not input_image.exists():
        print(f"[ERROR] Input image not found: {input_image}")
        sys.exit(1)
    
    print("=" * 60)
    print("PORTRAIT TO ANIME FACE CONVERTER")
    print("=" * 60)
    
    # Step 1: Convert to anime style
    if convert_to_anime_simple(str(input_image), str(anime_output)):
        print("[+] Anime conversion completed!")
    
    # Step 2: Extract face region
    if extract_face_region(str(input_image), str(face_output)):
        print("[+] Face extraction completed!")
    else:
        print("[!] Using full image as fallback")
    
    # Step 3: Convert extracted face to anime
    if face_output.exists():
        if convert_to_anime_simple(str(face_output), str(face_anime_output)):
            print("[+] Face anime conversion completed!")
            
            # Step 4: Upscale for texture quality
            if upscale_image(str(face_anime_output), str(upscaled_output), scale=2):
                print("[+] Image upscaled for texture!")
    
    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    print(f"Full anime conversion: {anime_output}")
    print(f"Face region: {face_output}")
    print(f"Face anime: {face_anime_output}")
    print(f"Upscaled anime face: {upscaled_output}")
    print("\nUse 'upscaled_output' for Live2D texture replacement!")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
