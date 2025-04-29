import whisper
import os
import time
from moviepy.editor import VideoFileClip

# 폴더 경로 설정
AUDIO_FOLDER = 'uploads/audio'
SUBTITLES_FOLDER = 'uploads/subtitles'

# 폴더가 없으면 생성
os.makedirs(AUDIO_FOLDER, exist_ok=True)
os.makedirs(SUBTITLES_FOLDER, exist_ok=True)

def extract_audio(video_path):
    """비디오 파일에서 오디오를 추출하고 저장합니다."""
    try:
        video = VideoFileClip(video_path)
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        audio_path = os.path.join(AUDIO_FOLDER, f"{base_name}.wav")
        audio_path = audio_path.replace('\\', '/')  # ✅ 경로 통일
        print(f"🎵 오디오 저장 경로: {audio_path}")

        video.audio.write_audiofile(audio_path)

        # ⭐ 추가: 저장 완료 대기
        timeout = 5
        while not os.path.exists(audio_path) and timeout > 0:
            time.sleep(0.5)
            timeout -= 0.5

        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"❌ 오디오 파일이 생성되지 않았습니다: {audio_path}")

        print(f"✅ 오디오 저장 완료: {audio_path}")
        return os.path.abspath(audio_path)  # ✅ 절대경로 반환

    except Exception as e:
        print(f"❌ 오디오 추출 실패: {e}")
        raise

def transcribe_audio(video_path):
    """오디오 파일을 Whisper로 자막 생성 후 .srt 파일로 저장합니다."""
    try:
        # 오디오 추출
        audio_path = extract_audio(video_path)

        # 경로 구분자 통일
        audio_path = audio_path.replace('\\', '/')

        # 오디오 파일 존재 여부 확인
        if not os.path.exists(audio_path):
            print(f"❌ 파일이 존재하지 않습니다: {audio_path}")
            raise FileNotFoundError(f"오디오 파일을 찾을 수 없습니다: {audio_path}")

        print(f"✅ Whisper 변환 시작, 파일 경로: {audio_path}")

        # Whisper 모델 로드
        model = whisper.load_model("base")
        try:
            result = model.transcribe(audio_path)
        except Exception as e:
            print(f"❌ Whisper 변환 실패: {e}")
            raise e

        # 결과 SRT 파일로 저장
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        srt_path = os.path.join(SUBTITLES_FOLDER, f"{base_name}.srt")

        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(result['segments'], 1):
                start_time = format_time(segment['start'])
                end_time = format_time(segment['end'])
                text = segment['text'].strip()

                f.write(f"{i}\n{start_time} --> {end_time}\n{text}\n\n")

        print(f"✅ SRT 파일 저장 완료: {srt_path}")

        # 오디오 파일 삭제
        try:
            os.remove(audio_path)
            print(f"🧹 오디오 파일 삭제 완료: {audio_path}")
        except Exception as e:
            print(f"⚠️ 오디오 삭제 실패: {e}")

        return srt_path

    except Exception as e:
        print(f"❌ 자막 생성 중 오류 발생: {e}")
        raise

def format_time(seconds):
    """초를 SRT 시간 형식으로 변환합니다."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"
