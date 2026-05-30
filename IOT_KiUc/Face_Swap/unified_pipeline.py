"""
Unified AI Video Generation Pipeline
Combines SadTalker (talking head animation) + video-retalking (lip sync improvement)
"""

import os
import sys
import cv2
import torch
import numpy as np
import subprocess
from pathlib import Path
from typing import Optional, Tuple
import tempfile
import shutil

# Add SadTalker to path
SADTALKER_PATH = os.path.join(os.path.dirname(__file__), 'SadTalker')
sys.path.insert(0, SADTALKER_PATH)
sys.path.insert(0, os.path.join(SADTALKER_PATH, 'src'))

# Add video-retalking to path
VIDEORETALKING_PATH = os.path.join(os.path.dirname(__file__), 'video-retalking')
sys.path.insert(0, VIDEORETALKING_PATH)


class UnifiedVideoPipeline:
    """
    Complete pipeline for AI video generation combining:
    - SadTalker: Create talking head from image + audio
    - video-retalking: Improve lip sync and overall quality
    """
    
    def __init__(self, device: str = 'cuda', sadtalker_checkpoint: str = 'checkpoints'):
        """
        Initialize the unified pipeline.
        
        Args:
            device: 'cuda' or 'cpu'
            sadtalker_checkpoint: Path to SadTalker checkpoints
        """
        self.device = device if torch.cuda.is_available() else 'cpu'
        self.sadtalker_checkpoint = sadtalker_checkpoint
        self.sadtalker = None
        self.temp_dir = tempfile.mkdtemp(prefix='unified_pipeline_')
        import threading
        self._lock = threading.Lock()
        
        print(f"[Pipeline] Using device: {self.device}")
        print(f"[Pipeline] Temporary directory: {self.temp_dir}")
        
    def cleanup(self):
        """Clean up temporary files"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            
    def _load_sadtalker(self):
        """Lazy load SadTalker model"""
        if self.sadtalker is None:
            try:
                from src.gradio_demo import SadTalker
                config_path = os.path.join(SADTALKER_PATH, 'src/config')
                self.sadtalker = SadTalker(self.sadtalker_checkpoint, config_path, lazy_load=True)
                print("[Pipeline] SadTalker loaded successfully")
            except Exception as e:
                print(f"[Pipeline] Error loading SadTalker: {e}")
                raise
                
    def _load_videoretalking(self):
        """Load video-retalking inference script"""
        try:
            sys.path.insert(0, VIDEORETALKING_PATH)
            return True
        except Exception as e:
            print(f"[Pipeline] Error loading video-retalking: {e}")
            return False
    
    def generate_talking_head(
        self,
        source_image: str,
        audio: str,
        preprocess_type: str = 'crop',
        is_still_mode: bool = False,
        use_enhancer: bool = True,
        pose_style: int = 0,
        size_of_image: int = 256,
        batch_size: int = 2,
        verbose: bool = True
    ) -> str:
        """
        Generate talking head video using SadTalker
        
        Args:
            source_image: Path to source image
            audio: Path to audio file
            preprocess_type: 'crop', 'resize', 'full', 'extcrop', 'extfull'
            is_still_mode: Reduce head motion
            use_enhancer: Use GFPGAN face enhancement
            pose_style: Pose style (0-46)
            size_of_image: Face model resolution (256 or 512)
            batch_size: Batch size for generation
            verbose: Print progress
            
        Returns:
            Path to generated video
        """
        if verbose:
            print(f"[Pipeline] Generating talking head from image: {source_image}")
            
        self._load_sadtalker()
        
        try:
            # Copy source image to temp_dir to prevent SadTalker from deleting/modifying the original file
            import uuid
            uid = str(uuid.uuid4())[:8]
            ext = source_image.split('.')[-1] if '.' in source_image else 'jpg'
            temp_image = os.path.join(self.temp_dir, f'temp_source_{uid}.{ext}')
            shutil.copy(source_image, temp_image)

            output_path = os.path.join(self.temp_dir, f'sadtalker_output_{uid}.mp4')
            
            # Call SadTalker inference
            try:
                with self._lock:
                    result_video = self.sadtalker.test(
                        source_image=temp_image,
                        driven_audio=audio,
                        preprocess=preprocess_type,
                        still_mode=is_still_mode,
                        use_enhancer=use_enhancer,
                        batch_size=batch_size,
                        size=size_of_image,
                        pose_style=pose_style
                    )
            except Exception as e:
                # Write detailed error log for debugging
                try:
                    err_path = os.path.join(self.temp_dir, "result_video_error.txt")
                    with open(err_path, "w", encoding="utf-8") as f:
                        import traceback
                        f.write("SadTalker.test() failed\n")
                        f.write(str(e) + "\n\n")
                        f.write(traceback.format_exc())
                    print(f"[Pipeline] Wrote SadTalker error log: {err_path}")
                except Exception:
                    pass
                raise
            
            if result_video and os.path.exists(result_video):
                # Copy to our temp directory
                shutil.copy(result_video, output_path)
                if verbose:
                    print(f"[Pipeline] OK Talking head generated: {output_path}")
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                return output_path
            else:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                raise Exception("SadTalker generation failed")
                
        except Exception as e:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print(f"[Pipeline] Error generating talking head: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def improve_lip_sync(
        self,
        video_path: str,
        audio_path: str,
        verbose: bool = True
    ) -> str:
        """
        Improve lip sync using video-retalking
        
        Args:
            video_path: Path to input video
            audio_path: Path to audio file
            verbose: Print progress
            
        Returns:
            Path to improved video
        """
        if verbose:
            print(f"[Pipeline] Improving lip sync for: {video_path}")
            
        try:
            # Output path
            output_path = os.path.join(self.temp_dir, f'retalking_output.mp4')
            
            # Prepare video-retalking inference script path
            inference_script = os.path.join(VIDEORETALKING_PATH, 'inference.py')
            
            if not os.path.exists(inference_script):
                print(f"[Pipeline] ⚠ video-retalking not available, skipping lip sync improvement")
                return video_path
            
            # Build command for video-retalking
            cmd = [
                sys.executable,
                inference_script,
                '--face', video_path,
                '--audio', audio_path,
                '--outfile', output_path,
                '--mel_step_size', '16'
            ]
            
            if verbose:
                print(f"[Pipeline] Running: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=VIDEORETALKING_PATH)
            
            if result.returncode == 0 and os.path.exists(output_path):
                if verbose:
                    print(f"[Pipeline] OK Lip sync improved: {output_path}")
                return output_path
            else:
                print(f"[Pipeline] Warning: video-retalking processing had issues")
                if verbose:
                    print(f"[Pipeline] STDOUT: {result.stdout}")
                    print(f"[Pipeline] STDERR: {result.stderr}")
                return video_path  # Return original if retalking fails
                
        except Exception as e:
            print(f"[Pipeline] Error improving lip sync: {e}")
            import traceback
            traceback.print_exc()
            return video_path  # Return original on error
    
    def swap_faces(
        self,
        video_path: str,
        source_face: str,
        verbose: bool = True
    ) -> Optional[str]:
        """
        Optional face swap step using Video-Face-Swap
        
        Args:
            video_path: Path to input video
            source_face: Path to source face image
            verbose: Print progress
            
        Returns:
            Path to face-swapped video or None if unavailable
        """
        if verbose:
            print(f"[Pipeline] Swapping faces in video")
            
        try:
            vfs_backend = os.path.join(os.path.dirname(__file__), 'Video-Face-Swap', 'backend')
            run_swap_script = os.path.join(vfs_backend, 'run_local_swap.py')
            
            if not os.path.exists(run_swap_script):
                print(f"[Pipeline] ⚠ Video-Face-Swap not available, skipping face swap")
                return None
            
            output_path = os.path.join(self.temp_dir, f'face_swapped.mp4')
            
            cmd = [
                sys.executable,
                run_swap_script,
                '--source_face', source_face,
                '--input_video', video_path,
                '--output', output_path
            ]
            
            if verbose:
                print(f"[Pipeline] Running face swap")
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=vfs_backend, timeout=300)
            
            if result.returncode == 0 and os.path.exists(output_path):
                if verbose:
                    print(f"[Pipeline] OK Faces swapped: {output_path}")
                return output_path
            else:
                print(f"[Pipeline] Face swap failed")
                return None
                
        except Exception as e:
            print(f"[Pipeline] Error in face swap: {e}")
            return None
    
    def generate_full_pipeline(
        self,
        source_image: str,
        audio: str,
        output_path: str,
        pipeline_steps: list = ['sadtalker', 'retalking'],
        use_face_swap: bool = False,
        source_face_for_swap: Optional[str] = None,
        **sadtalker_kwargs
    ) -> Tuple[bool, str]:
        """
        Execute the full pipeline combining multiple steps
        
        Args:
            source_image: Path to source image
            audio: Path to audio file
            output_path: Where to save final video
            pipeline_steps: List of steps to execute: ['sadtalker', 'retalking', 'swap']
            use_face_swap: Whether to include face swap
            source_face_for_swap: Source face for swapping (if enabled)
            **sadtalker_kwargs: Additional kwargs for SadTalker
            
        Returns:
            Tuple of (success: bool, output_path: str)
        """
        print(f"\n{'='*60}")
        print("[Pipeline] Starting Unified Video Generation Pipeline")
        print(f"{'='*60}\n")
        
        # Ensure temp_dir exists (it might have been deleted by a previous run's cleanup)
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir, exist_ok=True)

        try:
            current_video = None
            
            # Step 1: Generate talking head with SadTalker
            if 'sadtalker' in pipeline_steps:
                print("[Pipeline] === STEP 1: Generate Talking Head ===")
                current_video = self.generate_talking_head(
                    source_image=source_image,
                    audio=audio,
                    **sadtalker_kwargs
                )
                if not current_video or not os.path.exists(current_video):
                    return False, "SadTalker generation failed"
            
            # Step 2: Improve lip sync with video-retalking
            if 'retalking' in pipeline_steps and current_video:
                print("\n[Pipeline] === STEP 2: Improve Lip Sync ===")
                improved_video = self.improve_lip_sync(current_video, audio)
                if improved_video != current_video:
                    current_video = improved_video
            
            # Step 3: Optional face swap
            if use_face_swap and 'swap' in pipeline_steps and source_face_for_swap:
                print("\n[Pipeline] === STEP 3: Face Swap ===")
                swapped_video = self.swap_faces(current_video, source_face_for_swap)
                if swapped_video:
                    current_video = swapped_video
            
            # Copy final output
            if current_video and os.path.exists(current_video):
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                shutil.copy(current_video, output_path)
                
                print(f"\n[Pipeline] {'='*60}")
                print(f"[Pipeline] OK SUCCESS! Final output: {output_path}")
                print(f"[Pipeline] {'='*60}\n")
                
                return True, output_path
            else:
                return False, "No output video generated"
                
        except Exception as e:
            print(f"\n[Pipeline] ERROR FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)
        finally:
            # Clean up temp files only when pipeline succeeds.
            # When failures happen we keep temp_dir to allow debugging logs.
            if current_video and os.path.exists(output_path):
                self.cleanup()
    
    def __del__(self):
        """Cleanup on deletion"""
        try:
            self.cleanup()
        except:
            pass


if __name__ == '__main__':
    # Example usage
    pipeline = UnifiedVideoPipeline(device='cuda')
    
    # Example paths (replace with actual files)
    source_image = 'examples/image.jpg'
    audio_file = 'examples/audio.wav'
    output_file = 'outputs/final_video.mp4'
    
    success, result = pipeline.generate_full_pipeline(
        source_image=source_image,
        audio=audio_file,
        output_path=output_file,
        pipeline_steps=['sadtalker', 'retalking'],
        preprocess_type='crop',
        is_still_mode=False,
        use_enhancer=True,
        size_of_image=256
    )
    
    if success:
        print(f"Pipeline completed successfully!")
        print(f"Output: {result}")
    else:
        print(f"Pipeline failed: {result}")
