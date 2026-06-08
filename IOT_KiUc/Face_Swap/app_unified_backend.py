"""
Flask Backend for Unified AI Video Generation Pipeline
Handles API requests for talking head generation and lip sync improvement
"""

from flask import Flask, request, jsonify, send_from_directory, redirect, render_template, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
import jwt
import traceback

def log_error_to_file(msg):
    try:
        with open("backend_error.log", "a", encoding="utf-8") as f:
            from datetime import datetime
            f.write(f"[{datetime.now()}] {msg}\n")
    except: pass

try:
    import google.genai as genai
    gemini_client = genai.Client(api_key="AIzaSyAsitrf5GAwR-6IPLghSWKgdEHvqIQR430")
except ImportError:
    gemini_client = None
    print("Warning: google.genai is not installed. Gemini chat won't work.")

# Configurations
import os
import sys
import uuid
import subprocess
import threading
import traceback
import torch
import shutil
import json
from pathlib import Path
from datetime import datetime
import asyncio

# Import the unified pipeline
from unified_pipeline import UnifiedVideoPipeline

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = 'iot_memory_secret_key_123'

# Auto-create database if not exists
try:
    conn = pymysql.connect(host='localhost', user='root', password='')
    conn.cursor().execute('CREATE DATABASE IF NOT EXISTS iot_memory')
    conn.close()
except Exception as e:
    print(f"Warning: Could not auto-create database iot_memory: {e}")

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/iot_memory'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    google_id = db.Column(db.String(255), unique=True, nullable=True)
    name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

with app.app_context():
    db.create_all()

# Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'unified_uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'unified_outputs')
TEMP_FOLDER = os.path.join(BASE_DIR, 'unified_temp')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024  # 1GB max

# Status tracking
processing_status = {}

# Global pipeline instance
global_pipeline = None


def get_pipeline():
    """Get or create pipeline instance"""
    global global_pipeline
    if global_pipeline is None:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        sadtalker_path = os.path.join(os.path.dirname(__file__), 'SadTalker', 'checkpoints')
        global_pipeline = UnifiedVideoPipeline(device=device, sadtalker_checkpoint=sadtalker_path)
    return global_pipeline


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    return jsonify({
        'status': 'ok',
        'device': device,
        'gpu_available': torch.cuda.is_available(),
        'timestamp': datetime.now().isoformat()
    })


# ===== Live Chunk (TTS + SadTalker) helpers & endpoints =====

def generate_tts_vietnamese_mp3(text: str, output_mp3: str) -> bool:
    """
    Generate Vietnamese TTS to MP3 using edge-tts.exe (binary) from venv_epa.
    This avoids needing Python modules edge_tts/gtts/TTS in the Flask runtime.
    """
    text = (text or "").strip()
    if not text:
        return False

    os.makedirs(os.path.dirname(output_mp3), exist_ok=True)

    cmd = [
        sys.executable, "-m", "edge_tts",
        "--write-media=" + output_mp3,
        "--voice=vi-VN-HoaiMyNeural",
        "--rate=+10%",
        "--text", text
    ]

    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=300)

            if result.returncode == 0 and os.path.exists(output_mp3) and os.path.getsize(output_mp3) > 0:
                return True
                
            print(f"[LiveChunk][TTS] attempt {attempt+1} failed: rc={result.returncode}")
            print(result.stderr[-1000:]) # print the last 1000 chars to see the actual exception
            
            if attempt == max_retries - 1:
                log_error_to_file(f"TTS failed after {max_retries} attempts: {result.stderr[-1000:]}")
                return False
                
            time.sleep(1) # wait before retrying
        except Exception as e:
            print(f"[LiveChunk][TTS] edge-tts error: {e}")
            if attempt == max_retries - 1:
                log_error_to_file(f"TTS exception: {e}\n{traceback.format_exc()}")
                traceback.print_exc()
                return False
            time.sleep(1)
            
    return False

def generate_silent_audio_mp3(output_mp3: str, duration: int = 3) -> bool:
    """
    Generate a silent MP3 file using ffmpeg.
    """
    try:
        ffmpeg_exe = os.path.join(os.path.dirname(__file__), "ffmpeg.exe")
        if not os.path.exists(ffmpeg_exe):
            # Fallback to system ffmpeg if not in root
            ffmpeg_exe = "ffmpeg"
        
        dirname = os.path.dirname(output_mp3)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        
        cmd = [
            ffmpeg_exe,
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=mono",
            "-t", str(duration),
            "-q:a", "9",
            "-acodec", "libmp3lame",
            output_mp3,
            "-y"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"[LiveChunk][SilentAudio] ffmpeg failed: rc={result.returncode}")
            print(result.stderr[:1000])
            return False
            
        return os.path.exists(output_mp3) and os.path.getsize(output_mp3) > 0
    except Exception as e:
        print(f"[LiveChunk][SilentAudio] ffmpeg error: {e}")
        traceback.print_exc()
        return False



@app.route('/api/live/upload_image', methods=['POST'])
def live_upload_image():
    """
    Upload avatar image once for a live session.
    Frontend expects: { task_id, image_path }
    """
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'Missing image'}), 400

        image_file = request.files['image']
        if not image_file.filename:
            return jsonify({'error': 'No selected file'}), 400

        task_id = str(uuid.uuid4())[:12]
        task_folder = os.path.join(UPLOAD_FOLDER, f'live_{task_id}')
        os.makedirs(task_folder, exist_ok=True)

        image_path = os.path.join(task_folder, 'avatar.jpg')

        from PIL import Image
        img = Image.open(image_file)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(image_path, 'JPEG')

        processing_status[task_id] = {
            'status': 'ready',
            'progress': 0,
            'step': 'live_ready',
            'message': 'Avatar uploaded'
        }

        return jsonify({'task_id': task_id, 'image_path': image_path}), 200

    except Exception as e:
        print(f"[LiveChunk][upload_image] Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/live/generate_idle', methods=['POST'])
def live_generate_idle():
    """
    Generate an idle video chunk (subtle movement without talking).
    Frontend expects: { task_id, image_path }
    """
    try:
        data = request.get_json(force=True)
        
        task_id = data.get('task_id')
        image_path = data.get('image_path')
        
        if not task_id or not image_path:
            return jsonify({'error': 'Missing task_id/image_path'}), 400
            
        if not os.path.exists(image_path):
            return jsonify({'error': 'image_path not found'}), 400
            
        task_folder = os.path.join(OUTPUT_FOLDER, f'live_{task_id}')
        os.makedirs(task_folder, exist_ok=True)
        
        chunk_tag = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        out_mp3 = os.path.join(task_folder, f'idle_{chunk_tag}.mp3')
        out_mp4 = os.path.join(task_folder, f'idle_{chunk_tag}.mp4')
        
        processing_status[task_id] = {
            'status': 'processing',
            'progress': 10,
            'step': 'live_idle',
            'message': 'Generating idle audio'
        }
        
        # Generate 3 seconds of silent audio
        ok = generate_silent_audio_mp3(output_mp3=out_mp3, duration=3)
        if not ok:
            return jsonify({'error': 'Silent audio generation failed'}), 500
            
        processing_status[task_id]['progress'] = 35
        processing_status[task_id]['step'] = 'live_idle_sadtalker'
        processing_status[task_id]['message'] = 'Rendering idle chunk: SadTalker'
        
        import logging
        print("\n" + "="*50, flush=True)
        logging.error(f"[{datetime.now().strftime('%H:%M:%S')}] BAT DAU TAO VIDEO NHAP (IDLE)")
        logging.error(f"[{datetime.now().strftime('%H:%M:%S')}] 1/2 Dang nap model AI vao VRAM (mat 1-2 phut o lan dau)...")
        
        pipeline = get_pipeline()
        
        logging.error(f"[{datetime.now().strftime('%H:%M:%S')}] 2/2 Dang chay 3DMM Extraction va Face Render (se co thanh % chay)...")
        
        success, result = pipeline.generate_full_pipeline(
            source_image=image_path,
            audio=out_mp3,
            output_path=out_mp4,
            pipeline_steps=['sadtalker'],
            use_face_swap=False,
            preprocess_type='crop',
            is_still_mode=False,
            use_enhancer=True,
            pose_style=0,
            size_of_image=256,
            batch_size=2
        )
        
        if not success or not os.path.exists(out_mp4):
            return jsonify({'error': 'SadTalker idle chunk failed', 'detail': str(result)}), 500
            
        processing_status[task_id] = {
            'status': 'completed',
            'progress': 100,
            'step': 'live_idle_done',
            'message': 'Idle chunk rendered'
        }
        
        filename = os.path.basename(out_mp4)
        idle_video_url = f"/unified_outputs/live_{task_id}/{filename}"
        
        return jsonify({'idle_video_url': idle_video_url}), 200
        
    except Exception as e:
        print(f"[LiveChunk][generate_idle] Error: {e}")
        log_error_to_file(f"generate_idle exception: {e}\n{traceback.format_exc()}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def ask_ai(text):
    if not gemini_client:
        return "Lỗi: Chưa cài đặt thư viện google-genai ở Backend."
    try:
        prompt = (
            "Bạn là một người bạn thân, trả lời như đang đối thoại bình thường với"
            " người dùng. Hãy nói ngắn gọn, tự nhiên và tránh liệt kê hoặc phân loại." 
            f"User: {text}\nAI:"
        )
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        if "RESOURCE_EXHAUSTED" in str(e) or "quota" in str(e).lower():
            return "API quota đã hết. Vui lòng kiểm tra lại giới hạn API."
        else:
            return f"Lỗi API Gemini: {str(e)}"

@app.route('/api/live/chat', methods=['POST'])
def live_chat_api():
    try:
        data = request.get_json(force=True)
        text = data.get('text', '')
        if not text.strip():
            return jsonify({'error': 'No text provided'}), 400
        
        reply = ask_ai(text)
        return jsonify({'reply': reply}), 200
    except Exception as e:
        print(f"[LiveChunk][chat_api] Error: {e}")
        log_error_to_file(f"chat_api exception: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/live/render_chunk', methods=['POST'])
def live_render_chunk():
    """
    Render one chunk: TTS(chunk_text) -> SadTalker(image+audio) -> output mp4 chunk.
    Frontend expects: { chunk_video_url }
    """
    try:
        data = request.get_json(force=True)

        task_id = data.get('task_id')
        image_path = data.get('image_path')
        text = data.get('text')

        if not task_id or not image_path or not isinstance(text, str):
            return jsonify({'error': 'Missing task_id/image_path/text'}), 400

        if not os.path.exists(image_path):
            return jsonify({'error': 'image_path not found'}), 400

        task_folder = os.path.join(OUTPUT_FOLDER, f'live_{task_id}')
        os.makedirs(task_folder, exist_ok=True)

        chunk_tag = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        out_mp3 = os.path.join(task_folder, f'chunk_{chunk_tag}.mp3')
        out_mp4 = os.path.join(task_folder, f'chunk_{chunk_tag}.mp4')

        processing_status[task_id] = {
            'status': 'processing',
            'progress': 10,
            'step': 'live_tts',
            'message': 'Rendering chunk: TTS (MP3)'
        }

        ok = generate_tts_vietnamese_mp3(text=text.strip(), output_mp3=out_mp3)
        if not ok:
            processing_status[task_id] = {
                'status': 'failed',
                'progress': 0,
                'step': 'live_tts_error',
                'message': 'TTS failed'
            }
            return jsonify({'error': 'TTS failed'}), 500

        processing_status[task_id]['progress'] = 35
        processing_status[task_id]['step'] = 'live_sadtalker'
        processing_status[task_id]['message'] = 'Rendering chunk: SadTalker'

        import logging
        print("\n" + "="*50, flush=True)
        logging.error(f"[{datetime.now().strftime('%H:%M:%S')}] BAT DAU TAO VIDEO CHINH (NOI CHUYEN)")
        logging.error(f"[{datetime.now().strftime('%H:%M:%S')}] 1/2 Dang nap model AI vao VRAM (neu chua nap)...")

        pipeline = get_pipeline()

        logging.error(f"[{datetime.now().strftime('%H:%M:%S')}] 2/2 Dang chay 3DMM Extraction va Face Render (se co thanh % chay)...")

        success, result = pipeline.generate_full_pipeline(
            source_image=image_path,
            audio=out_mp3,
            output_path=out_mp4,
            pipeline_steps=['sadtalker'],
            use_face_swap=False,
            preprocess_type='crop',
            is_still_mode=False,
            use_enhancer=True,
            pose_style=0,
            size_of_image=256,
            batch_size=2
        )

        if not success or not os.path.exists(out_mp4):
            # Write error log for debugging
            try:
                err_path = os.path.join(task_folder, "last_error.txt")
                with open(err_path, "w", encoding="utf-8") as f:
                    f.write("SadTalker chunk failed\n")
                    f.write(f"success={success}\n")
                    f.write("result:\n")
                    f.write(str(result))
                    f.write("\n")
                    f.write(f"out_mp4={out_mp4}\n")
                print(f"[LiveChunk] wrote error log: {err_path}")
            except Exception as log_e:
                print(f"[LiveChunk] failed to write last_error.txt: {log_e}")

            processing_status[task_id] = {
                'status': 'failed',
                'progress': 0,
                'step': 'live_sadtalker_error',
                'message': str(result)
            }
            return jsonify({'error': 'SadTalker chunk failed', 'detail': str(result)}), 500

        processing_status[task_id] = {
            'status': 'completed',
            'progress': 100,
            'step': 'live_done',
            'message': 'Chunk rendered'
        }

        # Frontend will load mp4 via direct URL served by send_from_directory route.
        # We expose it under /unified_outputs/<filename>
        filename = os.path.basename(out_mp4)
        # Ensure unique filename but keep folder in URL:
        # URL will be /unified_outputs/live_<task_id>/<filename>
        chunk_video_url = f"/unified_outputs/live_{task_id}/{filename}"

        return jsonify({'chunk_video_url': chunk_video_url}), 200

    except Exception as e:
        print(f"[LiveChunk][render_chunk] Error: {e}")
        log_error_to_file(f"render_chunk exception: {e}\n{traceback.format_exc()}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/live_chunk', methods=['GET'])
@login_required
def live_chunk_page():
    return send_from_directory('.', 'live_chunk_ui.html')


@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Upload source image and audio"""
    try:
        task_id = str(uuid.uuid4())
        processing_status[task_id] = {
            'status': 'uploading',
            'progress': 0,
            'step': 'initializing',
            'message': 'Uploading files...'
        }
        
        # Check required files
        if 'image' not in request.files or 'audio' not in request.files:
            return jsonify({'error': 'Missing image or audio file'}), 400
        
        image_file = request.files['image']
        audio_file = request.files['audio']
        
        if image_file.filename == '' or audio_file.filename == '':
            return jsonify({'error': 'No selected files'}), 400
        
        # Save files
        task_folder = os.path.join(UPLOAD_FOLDER, task_id)
        os.makedirs(task_folder, exist_ok=True)
        
        image_path = os.path.join(task_folder, 'source_image.' + image_file.filename.split('.')[-1])
        audio_path = os.path.join(task_folder, 'audio.' + audio_file.filename.split('.')[-1])
        
        image_file.save(image_path)
        audio_file.save(audio_path)
        
        processing_status[task_id]['status'] = 'ready'
        processing_status[task_id]['progress'] = 100
        processing_status[task_id]['message'] = 'Files uploaded successfully'
        
        return jsonify({
            'task_id': task_id,
            'image_path': image_path,
            'audio_path': audio_path,
            'status': 'success'
        }), 200
        
    except Exception as e:
        print(f"Upload error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate', methods=['POST'])
def generate_video():
    """Generate AI talking head video with unified pipeline"""
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        
        if not task_id or task_id not in processing_status:
            return jsonify({'error': 'Invalid task_id'}), 400
        
        # Extract parameters
        image_path = data.get('image_path')
        audio_path = data.get('audio_path')
        use_retalking = data.get('use_retalking', True)
        use_face_swap = data.get('use_face_swap', False)
        source_face_swap = data.get('source_face_swap')
        
        # SadTalker settings
        preprocess_type = data.get('preprocess_type', 'crop')
        is_still_mode = data.get('is_still_mode', False)
        use_enhancer = data.get('use_enhancer', True)
        pose_style = data.get('pose_style', 0)
        size_of_image = data.get('size_of_image', 256)
        batch_size = data.get('batch_size', 2)
        
        if not os.path.exists(image_path) or not os.path.exists(audio_path):
            return jsonify({'error': 'Files not found'}), 400
        
        # Start processing in background
        def process_video():
            try:
                processing_status[task_id] = {
                    'status': 'processing',
                    'progress': 0,
                    'step': 'generating_talking_head',
                    'message': 'Generating talking head...'
                }
                
                pipeline = get_pipeline()
                
                # Prepare pipeline steps
                pipeline_steps = ['sadtalker']
                if use_retalking:
                    pipeline_steps.append('retalking')
                if use_face_swap:
                    pipeline_steps.append('swap')
                
                # Output path
                output_filename = f'final_video_{task_id}.mp4'
                output_path = os.path.join(OUTPUT_FOLDER, output_filename)
                
                # Run pipeline
                success, result = pipeline.generate_full_pipeline(
                    source_image=image_path,
                    audio=audio_path,
                    output_path=output_path,
                    pipeline_steps=pipeline_steps,
                    use_face_swap=use_face_swap,
                    source_face_for_swap=source_face_swap,
                    preprocess_type=preprocess_type,
                    is_still_mode=is_still_mode,
                    use_enhancer=use_enhancer,
                    pose_style=pose_style,
                    size_of_image=size_of_image,
                    batch_size=batch_size
                )
                
                if success and os.path.exists(output_path):
                    processing_status[task_id] = {
                        'status': 'completed',
                        'progress': 100,
                        'step': 'completed',
                        'message': 'Video generated successfully',
                        'output_file': output_filename,
                        'output_path': output_path,
                        'timestamp': datetime.now().isoformat()
                    }
                    print(f"OK Video generation completed: {output_path}")
                else:
                    processing_status[task_id] = {
                        'status': 'failed',
                        'progress': 0,
                        'step': 'error',
                        'message': result
                    }
                    print(f"ERROR Video generation failed: {result}")
                    
            except Exception as e:
                print(f"Processing error: {e}")
                traceback.print_exc()
                processing_status[task_id] = {
                    'status': 'failed',
                    'progress': 0,
                    'step': 'error',
                    'message': str(e)
                }
        
        # Start background thread
        thread = threading.Thread(target=process_video)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'task_id': task_id,
            'status': 'processing_started',
            'message': 'Video generation started in background'
        }), 202
        
    except Exception as e:
        print(f"Generate error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/status/<task_id>', methods=['GET'])
def get_status(task_id):
    """Get processing status"""
    if task_id not in processing_status:
        return jsonify({'error': 'Task not found'}), 404
    
    return jsonify(processing_status[task_id]), 200


@app.route('/api/download/<filename>', methods=['GET'])
def download_video(filename):
    """Download generated video"""
    try:
        file_path = os.path.join(OUTPUT_FOLDER, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)
        
    except Exception as e:
        print(f"Download error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/cleanup/<task_id>', methods=['POST'])
def cleanup_task(task_id):
    """Clean up task files"""
    try:
        task_folder = os.path.join(UPLOAD_FOLDER, task_id)
        if os.path.exists(task_folder):
            shutil.rmtree(task_folder)
        
        if task_id in processing_status:
            del processing_status[task_id]
        
        return jsonify({'status': 'cleaned up'}), 200
        
    except Exception as e:
        print(f"Cleanup error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get pipeline configuration and available options"""
    return jsonify({
        'device': 'cuda' if torch.cuda.is_available() else 'cpu',
        'max_file_size': app.config['MAX_CONTENT_LENGTH'],
        'preprocess_types': ['crop', 'resize', 'full', 'extcrop', 'extfull'],
        'image_sizes': [256, 512],
        'max_batch_size': 10,
        'supports_face_swap': os.path.exists(os.path.join(os.path.dirname(__file__), 'Video-Face-Swap', 'backend')),
        'supports_retalking': os.path.exists(os.path.join(os.path.dirname(__file__), 'video-retalking', 'inference.py'))
    }), 200


@app.route('/', methods=['GET'])
def index():
    """Serve the web interface"""
    return redirect('/live_chunk')


@app.route('/<path:path>', methods=['GET'])
def serve_static(path):
    """Serve static files"""
    return send_from_directory('.', path)


# ===== Auth Routes =====

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/live_chunk')
    
    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        email = data.get('email')
        password = data.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and user.password_hash and check_password_hash(user.password_hash, password):
            login_user(user)
            return jsonify({'success': True, 'redirect': '/live_chunk'})
        return jsonify({'success': False, 'message': 'Invalid email or password!'}), 401
        
    return send_from_directory('.', 'auth.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.json if request.is_json else request.form
    email = data.get('email')
    password = data.get('password')
    name = data.get('name', 'User')
    
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'This email is already registered!'}), 400
        
    new_user = User(
        email=email,
        name=name,
        password_hash=generate_password_hash(password)
    )
    db.session.add(new_user)
    db.session.commit()
    
    # Do not auto-login, redirect to login page with success flag
    return jsonify({'success': True, 'redirect': '/login?registered=1'})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

@app.route('/api/auth/google', methods=['POST'])
def google_auth():
    token = request.json.get('credential')
    try:
        # Decode JWT token from Google Identity Services
        idinfo = jwt.decode(token, options={"verify_signature": False})
        
        email = idinfo['email']
        google_id = idinfo['sub']
        name = idinfo.get('name', '')
        
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email, google_id=google_id, name=name)
            db.session.add(user)
            db.session.commit()
            
        login_user(user)
        return jsonify({'success': True, 'redirect': '/live_chunk'})
        
    except Exception as e:
        print(f"Google Auth Error: {e}")
        return jsonify({'success': False, 'message': 'Google login failed!'}), 400

@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user_info():
    return jsonify({
        'email': current_user.email,
        'name': current_user.name or current_user.email.split('@')[0]
    })


if __name__ == '__main__':
    print("="*60)
    print("Unified AI Video Generation Pipeline - Flask Backend")
    print("="*60)
    print(f"Device: {'CUDA' if torch.cuda.is_available() else 'CPU'}")
    print(f"GPU Available: {torch.cuda.is_available()}")
    
    # Initialize pipeline to preload models
    print("Initializing pipeline...")
    pipeline = get_pipeline()
    print("OK Pipeline initialized")
    
    print("\nStarting Flask server...")
    print("Server running on http://localhost:5000/live_chunk")
    print("="*60 + "\n")
    # Run in single process mode to prevent VS Code terminal from swallowing stdout
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)
