import numpy as np
import moviepy.editor as mp
from scipy.io import wavfile
import os

def detect_silence(audio_data, threshold=0.01, min_silence_duration=0.5):
    """오디오 데이터에서 무음 구간을 감지합니다."""
    # 오디오 데이터의 절대값 계산
    abs_audio = np.abs(audio_data)
    
    # 무음 구간 감지
    silence = abs_audio < threshold
    
    # 연속된 무음 구간 찾기
    silence_starts = []
    silence_ends = []
    in_silence = False
    
    for i in range(len(silence)):
        if silence[i] and not in_silence:
            silence_starts.append(i)
            in_silence = True
        elif not silence[i] and in_silence:
            silence_ends.append(i)
            in_silence = False
    
    # 마지막 무음 구간 처리
    if in_silence:
        silence_ends.append(len(silence))
    
    # 무음 구간의 길이 계산
    silence_durations = [(end - start) / len(silence) for start, end in zip(silence_starts, silence_ends)]
    
    # 최소 길이 이상의 무음 구간만 선택
    valid_silences = [(start, end) for start, end, duration in zip(silence_starts, silence_ends, silence_durations)
                     if duration >= min_silence_duration]
    
    return valid_silences

def process_video(video_path, mode='remove'):
    """비디오를 처리하여 무음 구간을 제거하거나 분할합니다."""
    # 비디오 로드
    video = mp.VideoFileClip(video_path)
    
    # 오디오 추출
    audio = video.audio
    if audio is None:
        raise ValueError("비디오에 오디오가 없습니다.")
    
    # 오디오 데이터 추출
    audio_data = audio.to_soundarray()
    if len(audio_data.shape) > 1:
        audio_data = audio_data.mean(axis=1)  # 스테레오를 모노로 변환
    
    # 무음 구간 감지
    silence_segments = detect_silence(audio_data)
    
    if mode == 'remove':
        # 무음 구간 제거
        clips = []
        last_end = 0
        
        for start, end in silence_segments:
            # 무음 구간 전의 클립 추가
            if start > last_end:
                clips.append(video.subclip(last_end, start))
            last_end = end
        
        # 마지막 클립 추가
        if last_end < video.duration:
            clips.append(video.subclip(last_end, video.duration))
        
        # 클립 합치기
        if clips:
            processed_video = mp.concatenate_videoclips(clips)
        else:
            processed_video = video
    
    elif mode == 'split':
        # 비디오 분할
        clips = []
        last_end = 0
        
        for start, end in silence_segments:
            # 무음 구간 전의 클립 추가
            if start > last_end:
                clips.append(video.subclip(last_end, start))
            last_end = end
        
        # 마지막 클립 추가
        if last_end < video.duration:
            clips.append(video.subclip(last_end, video.duration))
        
        # 분할된 비디오 저장
        output_dir = os.path.dirname(video_path)
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        
        for i, clip in enumerate(clips):
            output_path = os.path.join(output_dir, f"{base_name}_part{i+1}.mp4")
            clip.write_videofile(output_path)
        
        return [os.path.join(output_dir, f"{base_name}_part{i+1}.mp4") for i in range(len(clips))]
    
    else:
        raise ValueError("지원하지 않는 모드입니다. 'remove' 또는 'split'을 사용하세요.")
    
    # 처리된 비디오 저장
    output_path = os.path.splitext(video_path)[0] + '_processed.mp4'
    processed_video.write_videofile(output_path)
    
    return output_path 