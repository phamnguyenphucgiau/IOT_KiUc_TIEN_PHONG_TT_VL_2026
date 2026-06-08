import os
import cv2
import numpy as np
from PIL import Image

def extract_clothing_parts(image_path, output_dir="extracted_clothing", min_area=500, padding=10, close_kernel_size=5):
    """
    Extracts individual clothing parts from a texture sheet and removes the background.
    Supports both RGBA images (using alpha channel) and RGB images (using auto-detected background).
    """
    print(f"[*] Processing image: {image_path}")
    if not os.path.exists(image_path):
        print(f"[ERROR] File not found: {image_path}")
        return False

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    print(f"[*] Output directory created/verified: {output_dir}")

    # Load original image with PIL to keep high quality and keep alpha channel if present
    pil_img = Image.open(image_path)
    w, h = pil_img.size

    # Convert to OpenCV format (BGRA or BGR)
    cv_img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    
    # Generate binary mask of non-background elements
    if cv_img.shape[2] == 4:
        # Image has alpha channel (RGBA)
        print("[*] Image has alpha channel. Using alpha channel for separation.")
        alpha = cv_img[:, :, 3]
        _, mask = cv2.threshold(alpha, 10, 255, cv2.THRESH_BINARY)
    else:
        # Image does not have alpha (RGB)
        print("[*] Image is RGB. Auto-detecting background color from top-left pixel.")
        # Get background color from top-left pixel
        bg_color = cv_img[0, 0]
        print(f"[*] Detected background color (BGR): {bg_color}")
        
        # Calculate absolute difference from background color
        diff = np.abs(cv_img.astype(np.int32) - bg_color)
        diff_sum = np.sum(diff, axis=2)
        
        # Mask of pixels that are significantly different from background
        mask = (diff_sum > 20).astype(np.uint8) * 255

    # Apply morphological closing to bridge small gaps within parts (e.g. line art, textures)
    if close_kernel_size > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_kernel_size, close_kernel_size))
        mask_closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    else:
        mask_closed = mask.copy()

    # Find contours
    contours, hierarchy = cv2.findContours(mask_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(f"[*] Found {len(contours)} initial components.")

    extracted_count = 0
    metadata = []

    # Sort contours by area descending
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    for idx, cnt in enumerate(contours):
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue  # Skip small noise components

        x, y, w_cnt, h_cnt = cv2.boundingRect(cnt)

        # Apply padding to crop box while staying inside image boundaries
        x_pad = max(0, x - padding)
        y_pad = max(0, y - padding)
        w_pad = min(w - x_pad, w_cnt + 2 * padding)
        h_pad = min(h - y_pad, h_cnt + 2 * padding)

        # Skip if padded area is too small
        if w_pad <= 0 or h_pad <= 0:
            continue

        print(f"[+] Component {extracted_count + 1}: Rect=({x_pad}, {y_pad}, {w_pad}, {h_pad}), Area={area:.1f}")

        # Crop from the original PIL image (preserves color space and quality)
        cropped_pil = pil_img.crop((x_pad, y_pad, x_pad + w_pad, y_pad + h_pad))
        
        # Convert cropped image to RGBA
        cropped_rgba = cropped_pil.convert("RGBA")
        
        # Get the corresponding mask region
        # If the original image was RGB, we need to apply transparency to the background
        if cv_img.shape[2] != 4:
            # We construct an alpha channel for the cropped image based on our mask
            cropped_mask = mask_closed[y_pad:y_pad+h_pad, x_pad:x_pad+w_pad]
            
            # Convert mask to PIL Image and resize if needed
            mask_im = Image.fromarray(cropped_mask).convert("L")
            # Apply mask as alpha channel
            cropped_rgba.putalpha(mask_im)

        # Save cropped part
        out_filename = f"part_{extracted_count + 1:02d}.png"
        out_path = os.path.join(output_dir, out_filename)
        cropped_rgba.save(out_path, "PNG")
        
        metadata.append({
            "id": extracted_count + 1,
            "filename": out_filename,
            "path": out_path,
            "x": x_pad,
            "y": y_pad,
            "width": w_pad,
            "height": h_pad,
            "area": area
        })
        extracted_count += 1

    print(f"[*] Successfully extracted {extracted_count} parts to: {output_dir}")
    return metadata

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Extract individual parts from a texture atlas and remove background.")
    parser.add_argument("image_path", nargs="?", help="Path to the texture sheet image (e.g., texture_01.png or anh1.jpg)")
    parser.add_argument("--output_dir", "-o", default="extracted_clothing", help="Directory to save extracted parts")
    parser.add_argument("--min_area", "-a", type=int, default=500, help="Minimum pixel area for a valid part")
    parser.add_argument("--padding", "-p", type=int, default=10, help="Padding around extracted parts")
    parser.add_argument("--kernel_size", "-k", type=int, default=5, help="Morphological kernel size for closing gaps")

    args = parser.parse_args()

    target_image = args.image_path
    if not target_image:
        # Fallback to defaults
        workspace = "."
        texture_path_1 = os.path.join(workspace, "haru_greeter_pro_jp", "haru_greeter_pro_jp", "runtime", "haru_greeter_t05.2048", "texture_01.png")
        texture_path_2 = os.path.join(workspace, "haru_greeter_pro_jp", "haru_greeter_pro_jp", "runtime", "haru_greeter_t05.2048", "texture_01_custom_alpha.png")
        local_image = os.path.join(workspace, "anh1.jpg")

        if os.path.exists(texture_path_2):
            target_image = texture_path_2
        elif os.path.exists(texture_path_1):
            target_image = texture_path_1
        elif os.path.exists(local_image):
            target_image = local_image

    if target_image:
        extract_clothing_parts(
            target_image, 
            output_dir=args.output_dir, 
            min_area=args.min_area, 
            padding=args.padding, 
            close_kernel_size=args.kernel_size
        )
    else:
        print("[ERROR] No clothing texture sheet found to process. Please specify one: python extract_clothing.py <path_to_image>")

