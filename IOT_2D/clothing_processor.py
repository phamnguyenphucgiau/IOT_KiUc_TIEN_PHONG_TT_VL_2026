import cv2
import numpy as np
import os

class ClothingProcessor:
    """
    Class to remove background from uploaded clothing image, segment it,
    and map it onto the Live2D clothing texture sheet.
    """

    def make_opaque(self, img_rgba):
        """Fills transparent pixels with the average color of the non-transparent pixels."""
        if img_rgba.shape[2] == 3:
            return img_rgba
        bgr = img_rgba[:, :, :3]
        alpha = img_rgba[:, :, 3]
        mask = alpha > 10
        if np.any(mask):
            avg_color = np.mean(bgr[mask], axis=0).astype(np.uint8).tolist()
        else:
            avg_color = [255, 255, 255]
        
        opaque = bgr.copy()
        opaque[alpha <= 10] = avg_color
        return opaque

    def remove_background(self, img):
        """Removes background from BGR image using GrabCut and contour filling."""
        h, w = img.shape[:2]
        
        # Create initial mask
        mask = np.zeros(img.shape[:2], np.uint8)
        
        # Bounding box excluding 5% border
        border_w = int(w * 0.05)
        border_h = int(h * 0.05)
        rect = (border_w, border_h, w - 2 * border_w, h - 2 * border_h)
        
        bgdModel = np.zeros((1, 65), np.float64)
        fgdModel = np.zeros((1, 65), np.float64)
        
        # Run GrabCut
        cv2.grabCut(img, mask, rect, bgdModel, fgdModel, 6, cv2.GC_INIT_WITH_RECT)
        
        # Get foreground mask (definite + probable foreground)
        fg_mask = np.where((mask == 1) | (mask == 3), 255, 0).astype('uint8')
        
        # Fill holes inside the shirt mask
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            for idx in range(len(contours)):
                cv2.drawContours(fg_mask, contours, idx, 255, -1)
                
        # Clean up borders
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        
        # Smooth boundaries for anti-aliasing
        fg_mask_blurred = cv2.GaussianBlur(fg_mask, (5, 5), 0)
        
        # Create RGBA image
        rgba = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        rgba[:, :, 3] = fg_mask_blurred
        
        # Crop to foreground bounding box
        coords = cv2.findNonZero(fg_mask)
        if coords is not None:
            x, y, crop_w, crop_h = cv2.boundingRect(coords)
            # Add 10px padding
            pad = 10
            x_pad = max(0, x - pad)
            y_pad = max(0, y - pad)
            w_pad = min(w - x_pad, crop_w + 2 * pad)
            h_pad = min(h - y_pad, crop_h + 2 * pad)
            return rgba[y_pad:y_pad+h_pad, x_pad:x_pad+w_pad]
        
        return rgba

    def process_and_map(self, input_image_path, base_atlas_path, output_atlas_path):
        """
        Runs the background removal on the input clothing image,
        then segments, warps, and merges it into the base atlas.
        """
        # 1. Load image
        img = cv2.imread(input_image_path)
        if img is None:
            raise ValueError(f"Could not load image: {input_image_path}")
            
        # 2. Remove background
        shirt_transparent = self.remove_background(img)
        sh, sw = shirt_transparent.shape[:2]
        
        # 3. Load base atlas
        atlas = cv2.imread(base_atlas_path, cv2.IMREAD_UNCHANGED)
        if atlas is None:
            raise ValueError(f"Could not load base atlas: {base_atlas_path}")
            
        out_atlas = atlas.copy()
        
        # 4. Segment shirt parts
        collar_crop = shirt_transparent[0:int(sh*0.22), int(sw*0.3):int(sw*0.7)]
        body_crop = shirt_transparent[int(sh*0.18):, int(sw*0.2):int(sw*0.8)]
        left_sleeve_crop = shirt_transparent[int(sh*0.15):, 0:int(sw*0.35)]
        right_sleeve_crop = shirt_transparent[int(sh*0.15):, int(sw*0.65):sw]
        
        # 5. Make opaque to prevent transparent holes
        collar_opaque = self.make_opaque(collar_crop)
        body_opaque = self.make_opaque(body_crop)
        left_sleeve_opaque = self.make_opaque(left_sleeve_crop)
        right_sleeve_opaque = self.make_opaque(right_sleeve_crop)
        
        components = [
            { "name": "collar", "x": 1608, "y": 605, "w": 371, "h": 512, "source": collar_opaque },
            { "name": "body", "x": 57, "y": 990, "w": 654, "h": 1042, "source": body_opaque },
            { "name": "left_sleeve_upper", "x": 905, "y": 28, "w": 377, "h": 636, "source": left_sleeve_opaque },
            { "name": "right_sleeve_upper", "x": 1319, "y": 10, "w": 377, "h": 636, "source": right_sleeve_opaque },
            { "name": "left_sleeve_lower", "x": 1064, "y": 1076, "w": 340, "h": 639, "source": left_sleeve_opaque },
            { "name": "right_sleeve_lower", "x": 682, "y": 1080, "w": 340, "h": 642, "source": right_sleeve_opaque },
            { "name": "left_sleeve_cuff", "x": 1386, "y": 1349, "w": 566, "h": 194, "source": left_sleeve_opaque },
            { "name": "right_sleeve_cuff", "x": 1379, "y": 1124, "w": 557, "h": 224, "source": right_sleeve_opaque }
        ]
        
        # Clear suit jacket lapels
        lapels = [
            { "x": 1314, "y": 509, "w": 192, "h": 584 },
            { "x": 1108, "y": 489, "w": 192, "h": 584 }
        ]
        for lapel in lapels:
            x, y, w, h = lapel["x"], lapel["y"], lapel["w"], lapel["h"]
            out_atlas[y:y+h, x:x+w] = 0
            
        # Map each component
        for comp in components:
            x, y, w, h = comp["x"], comp["y"], comp["w"], comp["h"]
            src = comp["source"]
            
            # Crop original mask
            orig_crop = atlas[y:y+h, x:x+w]
            
            # Resize source to target rect
            src_resized = cv2.resize(src, (w, h), interpolation=cv2.INTER_LANCZOS4)
            
            # Create RGBA and apply alpha mask
            mapped_rgba = cv2.cvtColor(src_resized, cv2.COLOR_BGR2BGRA)
            mapped_rgba[:, :, 3] = orig_crop[:, :, 3]
            
            # Paste back
            out_atlas[y:y+h, x:x+w] = mapped_rgba
            
        # Save composite atlas
        cv2.imwrite(output_atlas_path, out_atlas)
        return True
