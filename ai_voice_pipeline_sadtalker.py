import whisper
import google.genai as genai
from gtts import gTTS
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
import os
import sys
import subprocess
import shutil
from shutil import which

# Ensure local ffmpeg (in project root) is discoverable by subprocesses
script_root = os.path.abspath(os.path.dirname(__file__))
os.environ["PATH"] = os.pathsep.join([script_root, os.environ.get("PATH", "")])
os.chdir(script_root)

# ===== cấu hình Gemini =====
client = genai.Client(api_key="AIzaSyAsitrf5GAwR-6IPLghSWKgdEHvqIQR430")

# ===== load Whisper =====
speech_model = whisper.load_model("base")

# ===== HÀM GHI ÂM MICRO =====
def record_audio(filename="voice_input.wav", duration=5, fs=16000):
    print("🎤 Nói đi...")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()
    write(filename, fs, recording)
    print("✔ Đã ghi xong")

# ===== HÀM TẠO ÂM THANH IM LẶNG =====
def create_silent_audio(filename="silent.wav", duration=5, fs=16000):
    """Creates a silent WAV file for blink mode."""
    print(f"🎤 Tạo file âm thanh im lặng: {filename}")
    samples = np.zeros(int(duration * fs), dtype=np.int16)
    write(filename, fs, samples)
    print("✔ Đã tạo xong file im lặng")
    return filename

# ===== Speech to Text =====
def speech_to_text(audio):
    result = speech_model.transcribe(audio, language="vi")
    return result["text"]

# ===== Gemini trả lời =====
def ask_ai(text):
    try:
        prompt = (
            "Bạn là một người bạn thân, trả lời như đang đối thoại bình thường với"
            " người dùng. Hãy nói ngắn gọn, tự nhiên và tránh liệt kê hoặc phân loại." 
            f"User: {text}\nAI:"
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        if "RESOURCE_EXHAUSTED" in str(e) or "quota" in str(e).lower():
            return "✗ API quota đã hết. Vui lòng kiểm tra: https://ai.dev/rate-limit"
        else:
            return f"✗ Lỗi API: {str(e)}"

# ===== Text to Speech =====
def text_to_speech(text):
    tts = gTTS(text=text, lang="vi")
    tts.save("ai_voice.mp3")
    print("✔ Đã tạo file âm thanh")

# ===== TẠO VIDEO TỰ ĐỘNG VỚI SADTALKER =====
def run_sadtalker(face_path="face.jpg", audio_path="ai_voice.mp3", outfile="ai_video_final.mp4"):
    """Run SadTalker inference to create a talking head video from a static image and audio."""
    print("🎬 Bắt đầu tạo video bằng SadTalker...")
    sadtalker_dir = os.path.join(os.getcwd(), "SadTalker")
    if not os.path.isdir(sadtalker_dir):
        print("⚠️ Không tìm thấy thư mục SadTalker.")
        return None

    # SadTalker inference command
    # inference.py --source_image <image> --driven_audio <audio> --result_dir <output_dir> --checkpoint_dir <checkpoints>
    result_dir = os.path.join(os.getcwd(), "sadtalker_output")
    os.makedirs(result_dir, exist_ok=True)
    
    # Use SadTalker's Python environment
    sadtalker_python = os.path.join(script_root, "sadtalker_env", "Scripts", "python.exe")
    
    cmd = [
        sadtalker_python, "inference.py",
        "--source_image", os.path.join("..", face_path),
        "--driven_audio", os.path.join("..", audio_path),
        "--result_dir", os.path.join("..", "sadtalker_output"),
        "--checkpoint_dir", "checkpoints",
        "--size", "256",
        # SadTalker doesn't support a device flag; it uses CPU by default
        "--preprocess", "crop"
    ]

    try:
        res = subprocess.run(cmd, cwd=sadtalker_dir, capture_output=True, text=True, timeout=600)
        print(res.stdout)
        if res.returncode != 0:
            print("❌ SadTalker lỗi:")
            print(res.stderr)
            return None
        
        # Find the generated video in sadtalker_output (it creates a timestamped folder)
        # Try to find the latest generated mp4 file
        output_videos = []
        for root, dirs, files in os.walk(result_dir):
            for file in files:
                if file.endswith(".mp4"):
                    output_videos.append(os.path.join(root, file))
        
        if output_videos:
            # Get the most recently modified video
            latest_video = max(output_videos, key=os.path.getmtime)
            print(f"✅ Đã tạo video: {latest_video}")
            return latest_video
        else:
            print("⚠️ Không tìm thấy video output từ SadTalker")
            return None
    except Exception as e:
        print("❌ Lỗi khi chạy SadTalker:", str(e))
        return None

# ===== RUN PIPELINE =====
if __name__ == '__main__':
    # Check ffmpeg availability early and guide the user if missing
    def ffmpeg_available():
        return which('ffmpeg') is not None or which('ffmpeg.exe') is not None

    if not ffmpeg_available():
        print("⚠️ Không tìm thấy 'ffmpeg' trên PATH.")
        print("Hãy cài ffmpeg và thêm vào PATH, hoặc đặt ffmpeg.exe vào thư mục dự án.")
        print("Windows: tải từ https://ffmpeg.org/download.html và giải nén; thêm đường dẫn tới ffmpeg.exe vào PATH.")
        # don't proceed if ffmpeg missing
        sys.exit(1)
    # cleanup old files from previous runs first
    try:
        for old_file in ["ai_video.mp4", "ai_video_temp.mp4", "ai_voice.mp3",
                         "voice_input.wav", "voice.mp3", "voice1.mp3", "ai_video_final.mp4", "silent.wav"]:
            if os.path.isfile(old_file):
                os.remove(old_file)
    except Exception:
        pass
    
    # --- Lựa chọn chế độ chạy ---
    mode = "auto"
    if len(sys.argv) > 1:
        mode = sys.argv[1]

    # --- Định nghĩa đường dẫn file input ---
    INPUT_FOLDER = "inputs"
    input_face_path = os.path.join(INPUT_FOLDER, "face.jpg")
    input_audio_path = os.path.join(INPUT_FOLDER, "voice_input.wav")

    video = None

    if mode == "blink":
        print("👉 Chế độ chớp mắt (Blink mode)")
        silent_audio = create_silent_audio("silent.wav", duration=5)
        video = run_sadtalker(face_path=input_face_path, audio_path=silent_audio)

    elif mode == "talk":
        print("👉 Chế độ nhép môi (Talk mode)")
        # Sử dụng trực tiếp audio người dùng tải lên
        video = run_sadtalker(face_path=input_face_path, audio_path=input_audio_path)

    else:  # Chế độ "auto" mặc định
        print("👉 Chế độ tự động (Auto mode)")
        # record_audio() # Bỏ qua ghi âm, dùng file đã upload
        print("Đang nhận dạng...")
        user_text = speech_to_text(input_audio_path)
        print("Bạn nói:", user_text)
        ai_reply = ask_ai(user_text)
        print("AI:", ai_reply)
        text_to_speech(ai_reply) # Tạo file ai_voice.mp3
        video = run_sadtalker(face_path=input_face_path, audio_path="ai_voice.mp3")

    if video:
        final = "ai_video_final.mp4"
        try:
            shutil.copy(video, final)
            print(f"✔ Video cuối cùng: {final}")
        except Exception as e:
            print(f"⚠️ Không thể copy video: {e}")

    if os.path.exists("ai_video_final.mp4"):
        print("✔ Đã tạo video hoàn chỉnh: ai_video_final.mp4")
    else:
        print("❌ Không tạo được video.")
