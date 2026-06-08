import os
import replicate
import requests
from dotenv import load_dotenv
from typing import Optional

class AnimeGenerator:
    """
    Generates an anime-style image from a real portrait using the Replicate API.
    """

    def __init__(self):
        """Initializes the AnimeGenerator and loads the Replicate API token."""
        load_dotenv()
        self.api_token = os.getenv("REPLICATE_API_TOKEN")
        if not self.api_token:
            print("Warning: REPLICATE_API_TOKEN not found in .env file. Anime generation will fail.")
        else:
            # Set the token for the replicate library
            os.environ["REPLICATE_API_TOKEN"] = self.api_token

    def generate(self, image_path: str, output_path: str) -> Optional[str]:
        """
        Calls the Replicate API to convert the image and saves it locally.

        Args:
            image_path: Path to the input portrait image.
            output_path: Path to save the downloaded anime image.

        Returns:
            The local path to the generated anime image, or None on failure.
        """
        if not self.api_token:
            return None

        try:
            with open(image_path, "rb") as image_file:
                # Using "fofr/face-to-many" as it's versatile for style transfer
                output = replicate.run(
                    "fofr/face-to-many:35cea9c3170d6b2a2f513584873104225a04351000a4f7b239c39f1538b78534",
                    input={
                        "image": image_file,
                        "style": "anime style, 2d illustration, clean lineart, soft shading, high quality",
                        "negative_prompt": "realistic, 3d, photo, blurry, low quality"
                    }
                )
            
            # Output is typically a list of URLs
            if output and isinstance(output, list) and len(output) > 0:
                image_url = output[0]
                response = requests.get(image_url, stream=True)
                response.raise_for_status()
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return output_path
            return None
        except Exception as e:
            print(f"An error occurred during anime generation: {e}")
            return None