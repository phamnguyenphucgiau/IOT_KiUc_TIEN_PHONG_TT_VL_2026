from PIL import Image
import numpy as np
from typing import List

class TexturePatcher:
    """
    Patches a Live2D texture by tinting specific regions (skin, eyes, hair)
    based on provided target colors, preserving shading by manipulating the HSV color space.
    """

    def _rgb_to_hsv_numpy(self, rgb: np.ndarray) -> np.ndarray:
        """Vectorized conversion of an RGB image array to HSV."""
        # Input: rgb is an array of shape (..., 3)
        # Assumes RGB values are in range [0, 255]
        rgb_norm = rgb / 255.0
        
        cmax = rgb_norm.max(-1)
        cmin = rgb_norm.min(-1)
        delta = cmax - cmin

        h = np.zeros_like(cmax)
        s = np.zeros_like(cmax)
        v = cmax

        # Hue calculation
        mask = delta != 0
        r, g, b = rgb_norm[..., 0], rgb_norm[..., 1], rgb_norm[..., 2]
        
        h[mask & (cmax == r)] = (60 * ((g[mask & (cmax == r)] - b[mask & (cmax == r)]) / delta[mask & (cmax == r)]) + 360) % 360
        h[mask & (cmax == g)] = (60 * ((b[mask & (cmax == g)] - r[mask & (cmax == g)]) / delta[mask & (cmax == g)]) + 120)
        h[mask & (cmax == b)] = (60 * ((r[mask & (cmax == b)] - g[mask & (cmax == b)]) / delta[mask & (cmax == b)]) + 240)
        h /= 360.0 # Normalize H to [0, 1]

        # Saturation calculation
        s[cmax != 0] = delta[cmax != 0] / cmax[cmax != 0]

        return np.stack([h, s, v], axis=-1)

    def _hsv_to_rgb_numpy(self, hsv: np.ndarray) -> np.ndarray:
        """Vectorized conversion of an HSV image array to RGB."""
        # Input: hsv is an array of shape (..., 3) with H, S, V in range [0, 1]
        h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
        h *= 360

        c = v * s
        x = c * (1 - np.abs(np.fmod(h / 60.0, 2) - 1))
        m = v - c

        rgb_prime = np.zeros_like(hsv)

        # Conditions for different hue ranges
        idx = (h >= 0) & (h < 60)
        rgb_prime[idx] = np.array([c[idx], x[idx], np.zeros_like(c[idx])]).T
        idx = (h >= 60) & (h < 120)
        rgb_prime[idx] = np.array([x[idx], c[idx], np.zeros_like(c[idx])]).T
        idx = (h >= 120) & (h < 180)
        rgb_prime[idx] = np.array([np.zeros_like(c[idx]), c[idx], x[idx]]).T
        idx = (h >= 180) & (h < 240)
        rgb_prime[idx] = np.array([np.zeros_like(c[idx]), x[idx], c[idx]]).T
        idx = (h >= 240) & (h < 300)
        rgb_prime[idx] = np.array([x[idx], np.zeros_like(c[idx]), c[idx]]).T
        idx = (h >= 300) & (h <= 360)
        rgb_prime[idx] = np.array([c[idx], np.zeros_like(c[idx]), x[idx]]).T

        return (rgb_prime + m[..., np.newaxis]) * 255
    
    def patch(self,
              base_texture_path: str,
              skin_color: List[int],
              eye_color: List[int],
              hair_color: List[int],
              output_path: str) -> str:
        """
        Loads a base texture, tints it with the given colors, and saves the result.

        Args:
            base_texture_path: Path to the source texture_00.png.
            skin_color: Target [R, G, B] for skin.
            eye_color: Target [R, G, B] for eyes.
            hair_color: Target [R, G, B] for hair.
            output_path: Path to save the new patched texture.

        Returns:
            The output_path where the file was saved.
        """
        try:
            # 1. Load the original texture
            img = Image.open(base_texture_path).convert('RGBA')
            pixels = img.load()

            # Get target HSV values from the input colors
            target_h_skin, target_s_skin, _ = self._rgb_to_hsv_pixel(*skin_color)
            target_h_eye, _, _ = self._rgb_to_hsv_pixel(*eye_color)
            target_h_hair, target_s_hair, target_v_hair = self._rgb_to_hsv_pixel(*hair_color)

            width, height = img.size
            for y in range(height):
                for x in range(width):
                    r, g, b, a = pixels[x, y]

                    # Skip transparent pixels
                    if a == 0:
                        continue

                    h, s, v = self._rgb_to_hsv_pixel(r, g, b)

                    # 2. Detect and tint skin region (Improved)
                    # This improved detection range is more robust for various skin tones.
                    # H: 5-50 degrees (covers a wide range of skin hues from pinkish to yellowish)
                    # S: > 20% (to avoid grayscale/desaturated colors)
                    # V: > 30% (to avoid near-black colors)
                    if 5/360 < h < 50/360 and s > 0.20 and v > 0.30:
                        # Blend the original saturation with the target's saturation for a more natural tint.
                        # This helps if the source and target skin tones have different vibrancy.
                        new_s = (s * 0.5) + (target_s_skin * 0.5)

                        new_r, new_g, new_b = self._hsv_to_rgb_pixel(target_h_skin, new_s, v)
                        pixels[x, y] = (new_r, new_g, new_b, a)
                        continue

                    # 3. Detect and tint eye region
                    # HSV range for the original blue eyes (H: 200-240 deg)
                    if 200/360 < h < 240/360 and s > 0.5:
                        new_r, new_g, new_b = self._hsv_to_rgb_pixel(target_h_eye, s, v)
                        pixels[x, y] = (new_r, new_g, new_b, a)
                        continue

                    # 4. Detect and tint hair region
                    # HSV range for the original dark purple-gray hair (H: 240-280 deg, V < 50%)
                    if 240/360 < h < 280/360 and v < 0.5:
                        # --- Advanced Hair Tinting ---
                        # This method remaps hue, saturation, and value to allow for
                        # significant color changes like black to blonde while preserving shading.

                        # a) Set the hue to the target hair hue.
                        new_h = target_h_hair

                        # b) Blend the saturation, giving more weight to the target color's saturation.
                        new_s = (s * 0.3) + (target_s_hair * 0.7)

                        # c) Remap the value (brightness) to the target color's brightness range.
                        # This preserves the original shading (relative darks and lights).
                        v_min_orig = 0.05  # Estimated darkest value in original hair texture
                        v_max_orig = 0.5   # Estimated brightest value in original hair texture
                        
                        # Calculate how far the current pixel's value is within the original range (0.0 to 1.0)
                        if (v_max_orig - v_min_orig) == 0:
                            v_remap_ratio = 0.5
                        else:
                            v_remap_ratio = (v - v_min_orig) / (v_max_orig - v_min_orig)
                        
                        v_remap_ratio = max(0.0, min(1.0, v_remap_ratio)) # Clamp to [0, 1]

                        # Define the new value range based on the target hair color's brightness.
                        # A light color (blonde) will have a high target_v_hair, creating a bright range.
                        # A dark color (brown) will have a low target_v_hair, creating a dark range.
                        v_min_new = target_v_hair * 0.3
                        v_max_new = min(1.0, target_v_hair * 1.2 + 0.1)
                        
                        new_v = v_min_new + v_remap_ratio * (v_max_new - v_min_new)

                        new_r, new_g, new_b = self._hsv_to_rgb_pixel(new_h, new_s, new_v)
                        pixels[x, y] = (new_r, new_g, new_b, a)
                        continue

            # 5. Save the new texture
            img.save(output_path)
            return output_path

        except FileNotFoundError:
            print(f"Error: Base texture not found at {base_texture_path}")
            raise
        except Exception as e:
            print(f"An error occurred during texture patching: {e}")
            raise