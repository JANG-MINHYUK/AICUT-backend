import torch
import torch.nn.functional as F
import numpy as np
import cv2
from moviepy.editor import VideoFileClip
import os
import gc
import subprocess

model = torch.hub.load('PeterL1n/RobustVideoMatting', 'mobilenetv3')
model = model.cuda() if torch.cuda.is_available() else model
model.eval()

class BackgroundRemover:
    def __init__(self):
        self.model = model

    def process_frame(self, frame):
        try:
            original_h, original_w = frame.shape[:2]
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            resized = cv2.resize(frame_rgb, (128, 128))

            tensor = torch.from_numpy(resized).permute(2, 0, 1).unsqueeze(0).float() / 255.0
            if torch.cuda.is_available():
                tensor = tensor.cuda()

            with torch.no_grad():
                _, pha, *_ = self.model(tensor)
                alpha = F.interpolate(pha, size=(original_h, original_w), mode='bilinear', align_corners=False)
                alpha = alpha.squeeze().cpu().numpy()

            return alpha
        except Exception as e:
            print(f"❌ 프레임 처리 중 오류: {e}")
            return None

    def remove_background(self, video_path):
        video = VideoFileClip(video_path)
        total_duration = int(video.duration)
        chunk_duration = 15  # 초 단위
        output_files = []
        temp_dir = 'temp_chunks'
        os.makedirs(temp_dir, exist_ok=True)

        for start in range(0, total_duration, chunk_duration):
            end = min(start + chunk_duration, total_duration)
            chunk = video.subclip(start, end)
            chunk_path = os.path.join(temp_dir, f"chunk_{start}_{end}.mp4")
            chunk.write_videofile(chunk_path, codec="libx264", audio=False, verbose=False, logger=None)

            processed_chunk = self.process_video_chunk(chunk_path)
            if processed_chunk:
                output_files.append(processed_chunk)

        final_output = os.path.splitext(video_path)[0] + '_final.mp4'
        self.merge_videos(output_files, final_output)

        for file in output_files + [os.path.join(temp_dir, f) for f in os.listdir(temp_dir)]:
            os.remove(file)
        os.rmdir(temp_dir)

        return final_output

    def process_video_chunk(self, video_path):
        clip = VideoFileClip(video_path).resize(height=540)
        fps = clip.fps

        output_path = video_path.replace(".mp4", "_processed.mp4")
        temp_dir = 'temp_frames'
        os.makedirs(temp_dir, exist_ok=True)
        processed_frames = []

        for i, frame in enumerate(clip.iter_frames()):
            alpha = self.process_frame(frame)
            if alpha is None:
                continue

            frame_bgra = cv2.cvtColor(frame, cv2.COLOR_RGB2BGRA)
            frame_bgra[:, :, 3] = (alpha * 255).astype(np.uint8)

            frame_path = os.path.join(temp_dir, f'frame_{i:04d}.jpg')
            cv2.imwrite(frame_path, frame_bgra, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            processed_frames.append(frame_path)

            del alpha
            del frame_bgra
            torch.cuda.empty_cache()
            gc.collect()

        if not processed_frames:
            return None

        frame_sample = cv2.imread(processed_frames[0], cv2.IMREAD_UNCHANGED)
        height, width = frame_sample.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        for frame_path in processed_frames:
            frame = cv2.imread(frame_path, cv2.IMREAD_UNCHANGED)
            if frame.shape[2] == 4:
                alpha_channel = frame[:, :, 3] / 255.0
                background = np.ones_like(frame[:, :, :3], dtype=np.uint8) * 255
                frame_rgb = (frame[:, :, :3] * alpha_channel[..., None] + background * (1 - alpha_channel[..., None])).astype(np.uint8)
            else:
                frame_rgb = frame[:, :, :3]
            out.write(frame_rgb)

        out.release()

        for frame_path in processed_frames:
            os.remove(frame_path)
        os.rmdir(temp_dir)

        return output_path

    def merge_videos(self, video_files, output_path):
        list_file = "files_to_merge.txt"
        with open(list_file, "w") as f:
            for file in video_files:
                f.write(f"file '{file}'\n")

        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_path]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        os.remove(list_file)

remover_instance = BackgroundRemover()

def remove_background(video_path):
    return remover_instance.remove_background(video_path)
