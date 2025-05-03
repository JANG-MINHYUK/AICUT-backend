import os
import subprocess
from moviepy.editor import VideoFileClip
import shutil

def remove_silence(input_path, output_path):
    command = [
        'ffmpeg',
        '-i', input_path,
        '-af', 'silenceremove=start_periods=1:start_duration=0.5:start_threshold=-30dB',
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '23',
        '-y', output_path
    ]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def split_on_silence(input_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    # 1. Generate silent timestamps using ffmpeg
    silence_log = os.path.join(output_dir, 'silence_timestamps.txt')
    detect_command = [
        'ffmpeg',
        '-i', input_path,
        '-af', 'silencedetect=noise=-30dB:d=0.5',
        '-f', 'null', '-'
    ]
    result = subprocess.run(detect_command, stderr=subprocess.PIPE, text=True)
    lines = result.stderr.splitlines()

    timestamps = []
    for line in lines:
        if 'silence_start' in line:
            start = float(line.split('silence_start: ')[1])
            timestamps.append(('start', start))
        elif 'silence_end' in line:
            end = float(line.split('silence_end: ')[1].split('|')[0])
            timestamps.append(('end', end))

    # 2. Cut video into segments
    clip = VideoFileClip(input_path)
    segments = []
    prev = 0.0
    for tag, ts in timestamps:
        if tag == 'start':
            segments.append((prev, ts))
        elif tag == 'end':
            prev = ts

    if not segments:
        return []

    saved_paths = []
    for idx, (start, end) in enumerate(segments):
        segment_path = os.path.join(output_dir, f'segment_{idx+1}.mp4')
        subclip = clip.subclip(start, end)
        subclip.write_videofile(segment_path, codec='libx264', audio_codec='aac', verbose=False, logger=None)
        saved_paths.append(segment_path)

    return saved_paths

def zip_segments(output_dir, zip_path):
    shutil.make_archive(zip_path.replace('.zip', ''), 'zip', output_dir)