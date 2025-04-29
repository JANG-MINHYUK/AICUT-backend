import torch
import torch.nn.functional as F
import numpy as np
import cv2
from moviepy.editor import VideoFileClip
import os

# 글로벌 모델 1번만 로드
model = torch.hub.load('PeterL1n/RobustVideoMatting', 'mobilenetv3')
model = model.cuda() if torch.cuda.is_available() else model
model.eval()

class BackgroundRemover:
    def __init__(self):
        self.model = model

    def process_frame(self, frame):
        print("📸 프레임 처리 시작")
        try:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (512, 512))
            frame = torch.from_numpy(frame).permute(2, 0, 1).unsqueeze(0).float() / 255.0

            if torch.cuda.is_available():
                frame = frame.cuda()

            with torch.no_grad():
                result = self.model(frame)
                alpha = result[0]

            alpha = F.interpolate(alpha, size=(frame.shape[2], frame.shape[3]), mode='bilinear', align_corners=False)
            alpha = alpha.squeeze().cpu().numpy()
            print(f"✅ alpha 생성 완료, 반환 전 shape: {alpha.shape}")
            return alpha

        except Exception as e:
            print(f"❌ 프레임 처리 중 오류 발생: {e}")
            return None

    def remove_background(self, video_path):
        print("🎞️ 비디오 배경 제거 시작")
        video = VideoFileClip(video_path)
        fps = video.fps

        output_path = os.path.splitext(video_path)[0] + '_nobg.mp4'
        temp_dir = 'temp_frames'
        os.makedirs(temp_dir, exist_ok=True)

        processed_frames = []
        mask_frames = []

        for i, frame in enumerate(video.iter_frames()):
            print(f"🎞️ 프레임 {i} 수신됨, shape: {frame.shape}")
            try:
                alpha = self.process_frame(frame)
                if alpha is None or not isinstance(alpha, np.ndarray):
                    print(f"⚠️ 프레임 {i} 처리 실패, alpha 유효성 검사 실패")
                    continue

                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGRA)
                frame[:, :, 3] = (alpha * 255).astype(np.uint8)

                frame_path = os.path.join(temp_dir, f'frame_{i:04d}.png')
                cv2.imwrite(frame_path, frame)
                processed_frames.append(frame_path)
                mask_frames.append(alpha)

                print(f"✅ 프레임 {i} 처리 완료")

            except Exception as e:
                print(f"❗ 프레임 {i} 처리 중 오류 발생: {e}")
                continue

        if not processed_frames:
            raise RuntimeError("⚠️ 처리된 프레임이 없습니다.")

        try:
            mask = np.stack([m for m in mask_frames if m is not None])
        except Exception as e:
            raise ValueError(f"❌ 마스크 스택 오류: {e}")

        frame = cv2.imread(processed_frames[0], cv2.IMREAD_UNCHANGED)
        height, width = frame.shape[:2]

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        for frame_path in processed_frames:
            frame = cv2.imread(frame_path, cv2.IMREAD_UNCHANGED)
            out.write(frame)

        out.release()

        for frame_path in processed_frames:
            os.remove(frame_path)
        os.rmdir(temp_dir)

        return output_path

# 외부 사용용
remover_instance = BackgroundRemover()

def remove_background(video_path):
    return remover_instance.remove_background(video_path)
