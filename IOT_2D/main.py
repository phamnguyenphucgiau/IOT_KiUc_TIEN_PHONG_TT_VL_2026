import os
import uuid
import shutil
from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Dict, List

from face_analyzer import FaceAnalyzer
from texture_patcher import TexturePatcher
from anime_generator import AnimeGenerator
from clothing_processor import ClothingProcessor

# --- Initialization ---

app = FastAPI(title="Live2D Character Creator API")

# Create necessary directories
os.makedirs("static/patched", exist_ok=True)
os.makedirs("temp_uploads", exist_ok=True)

# Mount static files directory to serve patched textures
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS configuration
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:8080",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:5500", # For VS Code Live Server
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instantiate service classes
face_analyzer = FaceAnalyzer()
texture_patcher = TexturePatcher()
anime_generator = AnimeGenerator()
clothing_processor = ClothingProcessor()

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Welcome to the Live2D Character Creator API"}

@app.post("/api/analyze")
async def analyze_image(file: UploadFile = File(...)):
    """
    Analyzes an uploaded portrait to extract colors and generate an anime version.
    """
    session_id = str(uuid.uuid4())
    upload_path = f"temp_uploads/{session_id}_{file.filename}"
    anime_output_path = f"static/patched/{session_id}_anime.jpg"

    try:
        # Save uploaded file temporarily
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Perform analysis and generation
        color_data = face_analyzer.analyze(upload_path)
        if not color_data:
            raise HTTPException(status_code=400, detail="Could not detect a face in the uploaded image.")

        generated_anime_path = anime_generator.generate(upload_path, anime_output_path)
        
        anime_face_url = f"/static/patched/{os.path.basename(generated_anime_path)}" if generated_anime_path else None

        return {
            "colors": color_data,
            "anime_face_url": anime_face_url
        }
    except Exception as e:
        # Catch potential exceptions from analysis or generation
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up the temporary uploaded file
        if os.path.exists(upload_path):
            os.remove(upload_path)

@app.post("/api/patch-texture")
async def patch_texture_endpoint(colors: Dict[str, List[int]] = Body(...)):
    """
    Creates a new Live2D texture by patching the base texture with the provided colors.
    """
    session_id = str(uuid.uuid4())
    base_texture_path = "Backend/haru_greeter_pro_jp/runtime/haru_greeter_t05.2048/texture_00.png" # Assume base texture is here
    output_path = f"static/patched/{session_id}_texture_00.png"

    if not os.path.exists(base_texture_path):
        raise HTTPException(
            status_code=500, 
            detail=f"Base texture not found at '{base_texture_path}'. Please create a 'live2d_assets' folder inside 'backend' and copy your 'texture_00.png' into it."
        )

    try:
        texture_patcher.patch(
            base_texture_path=base_texture_path,
            skin_color=colors['skin'],
            eye_color=colors['eye'],
            hair_color=colors['hair'],
            output_path=output_path
        )
        
        return {"texture_url": f"/{output_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to patch texture: {e}")

@app.post("/api/upload-clothing")
async def upload_clothing_endpoint(file: UploadFile = File(...)):
    """
    Endpoint that accepts an uploaded clothing image, removes its background,
    segments it, and maps it onto the Live2D clothing sheet, returning the URL
    to the generated texture atlas.
    """
    session_id = str(uuid.uuid4())
    upload_path = f"temp_uploads/{session_id}_{file.filename}"
    output_path = f"static/patched/{session_id}_texture_01.png"
    
    # Base atlas path for clothing (with transparency)
    base_atlas_path = "haru_greeter_pro_jp/haru_greeter_pro_jp/runtime/haru_greeter_t05.2048/texture_01_custom_alpha.png"
    
    if not os.path.exists(base_atlas_path):
        raise HTTPException(
            status_code=500,
            detail=f"Base clothing atlas not found at: {base_atlas_path}"
        )
        
    try:
        # Save uploaded file temporarily
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Process, segment, and map the clothing
        success = clothing_processor.process_and_map(
            input_image_path=upload_path,
            base_atlas_path=base_atlas_path,
            output_atlas_path=output_path
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to process and map the clothing image.")
            
        # Return the URL of the new texture sheet (relative to XAMPP / HTTP server)
        return {"texture_url": f"/static/patched/{session_id}_texture_01.png"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary uploaded file
        if os.path.exists(upload_path):
            os.remove(upload_path)