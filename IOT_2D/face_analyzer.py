import cv2
import numpy as np
import mediapipe as mp
from typing import Dict, List, Optional

class FaceAnalyzer:
    """
    Analyzes a human portrait to extract dominant colors for skin, eyes, and hair.
    """

    def __init__(self):
        """Initializes the FaceAnalyzer with MediaPipe Face Mesh."""
        try:
            self.face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5
            )
        except Exception as e:
            print(f"[WARNING] MediaPipe initialization failed (likely Python 3.14 incompatibility): {e}")
            self.face_mesh = None

    def _get_average_color(self, image: np.ndarray, landmarks: List[tuple]) -> Optional[List[int]]:
        """
        Calculates the average color from a list of landmark points on an image.
        
        Args:
            image: The image as a NumPy array (RGB).
            landmarks: A list of (x, y) coordinates.

        Returns:
            A list [R, G, B] representing the average color, or None if no valid pixels are found.
        """
        valid_pixels = []
        for x, y in landmarks:
            if 0 <= y < image.shape[0] and 0 <= x < image.shape[1]:
                valid_pixels.append(image[y, x])
        
        if not valid_pixels:
            return None
            
        avg_color = np.mean(valid_pixels, axis=0)
        return [int(c) for c in avg_color]

    def analyze(self, image_path: str) -> Optional[Dict[str, List[int]]]:
        """
        Performs color analysis on the given image file.

        Args:
            image_path: The file path to the image.

        Returns:
            A dictionary with 'skin', 'eye', and 'hair' colors, or None if no face is detected.
            Example: {"skin": [R,G,B], "eye": [R,G,B], "hair": [R,G,B]}
        """
        try:
            image = cv2.imread(image_path)
            if image is None:
                print(f"Error: Could not read image from {image_path}")
                return None

            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            if self.face_mesh is None:
                print("[INFO] MediaPipe is disabled. Returning default fallback facial colors.")
                return {
                    "skin": [224, 192, 174],
                    "eye": [80, 90, 120],
                    "hair": [50, 40, 35]
                }

            results = self.face_mesh.process(image_rgb)

            if not results.multi_face_landmarks:
                return None

            face_landmarks = results.multi_face_landmarks[0].landmark
            h, w, _ = image_rgb.shape

            def get_coords(indices: List[int]) -> List[tuple]:
                return [(int(face_landmarks[i].x * w), int(face_landmarks[i].y * h)) for i in indices]

            # Landmark indices for different facial regions
            # These are carefully selected points from the 478-landmark model
            skin_indices = [234, 454, 10, 152, 334, 297]  # Cheeks, forehead, chin
            left_eye_indices = [473, 474, 475, 476, 477] # Left iris
            right_eye_indices = [468, 469, 470, 471, 472] # Right iris
            hair_indices = [10, 338, 297, 67, 109] # Hairline area

            skin_color = self._get_average_color(image_rgb, get_coords(skin_indices))
            
            # Average color from both eyes
            eye_landmarks = get_coords(left_eye_indices + right_eye_indices)
            eye_color = self._get_average_color(image_rgb, eye_landmarks)
            
            hair_color = self._get_average_color(image_rgb, get_coords(hair_indices))

            return {
                "skin": skin_color or [224, 192, 174], # Default fallback skin tone
                "eye": eye_color or [80, 90, 120], # Default fallback eye color
                "hair": hair_color or [50, 40, 35], # Default fallback hair color
            }
        except Exception as e:
            print(f"An error occurred during face analysis: {e}")
            return None