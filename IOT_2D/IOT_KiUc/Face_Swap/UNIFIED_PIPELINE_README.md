# 🎬 Unified AI Talking Head Video Pipeline

Complete end-to-end system combining **SadTalker** (talking head animation) and **VideoReTalking** (lip-sync improvement) for professional AI video generation.

## Features

✨ **Complete Pipeline**
- 🖼️ Generate talking head from static image + audio (SadTalker)
- 👄 Automatic lip-sync improvement (VideoReTalking)
- 🔄 Optional face-swap post-processing
- 🎨 Face enhancement with GFPGAN

✚ **Advanced Controls**
- Multiple preprocessing options (crop, resize, full, extcrop, extfull)
- Pose style customization (0-46)
- Still mode for reduced head motion
- Batch size optimization
- Face model resolution selection (256 or 512)

🌐 **Web Interface**
- Beautiful, responsive UI
- Real-time progress tracking
- File preview (image & audio)
- One-click video download
- Status dashboard

## Installation

### Prerequisites
- Python 3.8+
- CUDA 11.0+ (recommended for GPU acceleration)
- FFmpeg
- 20GB+ free disk space (for models)

### Step 1: Clone and Download Models

```bash
cd c:\xampp\htdocs\Face_Swap

# The video-retalking repo is already cloned
# If you need to clone again:
# git clone https://github.com/OpenTalker/video-retalking.git

# Download SadTalker models
cd SadTalker
wget https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/checkpoints.zip
unzip checkpoints.zip
cd ..

# Download video-retalking models
cd video-retalking
wget https://github.com/OpenTalker/video-retalking/releases/download/v0.0.1/checkpoints.zip
unzip checkpoints.zip
cd ..
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv_unified
venv_unified\Scripts\activate

# Linux/Mac
python3 -m venv venv_unified
source venv_unified/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install --upgrade pip setuptools wheel

# Install all requirements
pip install -r requirements_unified.txt

# If you have GPU (NVIDIA):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install any additional dependencies
pip install PyYAML pyyaml
```

### Step 4: Verify Installation

```bash
python -c "import torch; print('CUDA Available:', torch.cuda.is_available())"
python unified_pipeline.py
```

## Usage

### Method 1: Web Interface (Recommended)

```bash
# Make sure your virtual environment is activated
python app_unified_backend.py
```

Then open your browser: http://localhost:5000

### Method 2: Python Script

```python
from unified_pipeline import UnifiedVideoPipeline

# Initialize pipeline
pipeline = UnifiedVideoPipeline(device='cuda')  # or 'cpu'

# Generate video
success, output_path = pipeline.generate_full_pipeline(
    source_image='path/to/image.jpg',
    audio='path/to/audio.wav',
    output_path='outputs/result.mp4',
    pipeline_steps=['sadtalker', 'retalking'],
    preprocess_type='crop',
    is_still_mode=False,
    use_enhancer=True,
    size_of_image=256,
    pose_style=0
)

if success:
    print(f"Video saved to: {output_path}")
else:
    print(f"Error: {output_path}")

pipeline.cleanup()
```

### Method 3: API Endpoints

```bash
# Check health
curl http://localhost:5000/api/health

# Get configuration
curl http://localhost:5000/api/config

# Upload files
curl -F "image=@image.jpg" -F "audio=@audio.wav" \
  http://localhost:5000/api/upload

# Generate video
curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "your-task-id",
    "image_path": "path/to/image",
    "audio_path": "path/to/audio",
    "use_retalking": true,
    "preprocess_type": "crop"
  }'

# Check status
curl http://localhost:5000/api/status/your-task-id

# Download result
curl http://localhost:5000/api/download/final_video_xyz.mp4 -o result.mp4
```

## Parameters Explained

### SadTalker Settings

| Parameter | Options | Description |
|-----------|---------|-------------|
| `preprocess_type` | crop, resize, full, extcrop, extfull | How to process input image |
| `size_of_image` | 256, 512 | Face model resolution (higher = better quality, slower) |
| `is_still_mode` | True/False | Reduce head motion for formal settings |
| `use_enhancer` | True/False | Apply GFPGAN face enhancement |
| `pose_style` | 0-46 | Style of head pose (experiment to find preferred style) |
| `batch_size` | 1-10 | Batch size (higher = faster but uses more memory) |

### Pipeline Steps

- **sadtalker**: Generate talking head animation from image + audio
- **retalking**: Improve lip synchronization on the generated video
- **swap**: (Optional) Perform face swap using Video-Face-Swap backend

## Output Structure

```
unified_outputs/
├── final_video_[task-id].mp4    # Final output video
└── ...

unified_uploads/
├── [task-id]/
│   ├── source_image.jpg
│   └── audio.wav
└── ...

unified_temp/
└── [temporary processing files]
```

## Troubleshooting

### CUDA Out of Memory
```bash
# Reduce batch size in UI or:
batch_size = 1

# Or use CPU:
pipeline = UnifiedVideoPipeline(device='cpu')
```

### Model Download Issues
```bash
# Manually download from:
# SadTalker: https://github.com/OpenTalker/SadTalker/releases
# video-retalking: https://github.com/OpenTalker/video-retalking/releases
# Extract to respective checkpoints/ folders
```

### FFmpeg Not Found
```bash
# Windows (with chocolatey):
choco install ffmpeg

# Linux:
sudo apt-get install ffmpeg

# Mac:
brew install ffmpeg
```

### Video-Face-Swap Not Available
- Install optional dependencies: `pip install -r Video-Face-Swap/requirements.txt`
- Face swap will be skipped if unavailable

## Performance Optimization

### For Faster Processing
- Use `size_of_image=256` instead of 512
- Enable `is_still_mode` (less animation)
- Increase `batch_size` (if GPU memory allows)
- Use shorter audio clips

### For Better Quality
- Use `size_of_image=512`
- Use `use_enhancer=True`
- Enable `retalking` step
- Try different `preprocess_type` options

## API Response Examples

### Upload Response
```json
{
  "task_id": "abc123def456",
  "image_path": "/unified_uploads/abc123def456/source_image.jpg",
  "audio_path": "/unified_uploads/abc123def456/audio.wav",
  "status": "success"
}
```

### Generation Response
```json
{
  "task_id": "abc123def456",
  "status": "processing_started",
  "message": "Video generation started in background"
}
```

### Status Response
```json
{
  "status": "processing",
  "progress": 45,
  "step": "generating_talking_head",
  "message": "Generating talking head..."
}
```

### Completion Response
```json
{
  "status": "completed",
  "progress": 100,
  "step": "completed",
  "message": "Video generated successfully",
  "output_file": "final_video_abc123.mp4",
  "output_path": "/unified_outputs/final_video_abc123.mp4",
  "timestamp": "2024-05-08T12:34:56"
}
```

## Architecture

```
┌─────────────────────────────────────┐
│   Web UI (HTML/JavaScript)          │
│   - File upload                     │
│   - Parameter configuration         │
│   - Progress tracking               │
│   - Download management             │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   Flask Backend (app_unified_backend.py)
│   - File handling                   │
│   - API endpoints                   │
│   - Status tracking                 │
│   - Async job management            │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   Unified Pipeline (unified_pipeline.py)
│   ┌────────────────────────────────┐│
│   │ SadTalker Inference            ││
│   │ - Face detection               ││
│   │ - 3D face reconstruction       ││
│   │ - Animation generation         ││
│   └────────────────────────────────┘│
│   ┌────────────────────────────────┐│
│   │ VideoReTalking Post-Processing ││
│   │ - Lip sync refinement          ││
│   │ - Audio-visual alignment       ││
│   └────────────────────────────────┘│
│   ┌────────────────────────────────┐│
│   │ Optional Face Swap             ││
│   │ - Face detection & extraction  ││
│   │ - Blending & compositing       ││
│   └────────────────────────────────┘│
└─────────────────────────────────────┘
```

## Important Notes

⚠️ **Existing Apps Unchanged**
- `app_emote_portrait.py` - Not modified
- `app_face_swap.py` - Not modified
- All existing functionality preserved

📁 **File Organization**
- New unified pipeline files: `unified_pipeline.py`, `app_unified_backend.py`, `full_pipeline_ui.html`
- Separate upload/output folders to avoid conflicts
- Existing apps continue to work independently

🔧 **Model Requirements**
- Ensure all models are downloaded before first use
- Models cached in respective `checkpoints/` directories
- Plan for 15-20GB disk space for all models

## Performance Benchmarks

**GPU (NVIDIA RTX 3080):**
- Image → Talking Head: ~30-60 seconds (depending on video length)
- Lip Sync Improvement: ~20-40 seconds
- Total (both steps): ~50-100 seconds

**CPU:**
- 3-5x slower than GPU
- Not recommended for production use

## Contributing & Support

For issues with:
- **SadTalker**: https://github.com/OpenTalker/SadTalker
- **VideoReTalking**: https://github.com/OpenTalker/video-retalking
- **This Integration**: Check the error logs in the status dashboard

## License

- SadTalker: MIT License
- VideoReTalking: MIT License
- This integration: MIT License

---

**Created**: May 2024
**Last Updated**: May 2024
**Status**: Production Ready
