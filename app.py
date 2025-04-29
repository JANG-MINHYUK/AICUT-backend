from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import time
from werkzeug.utils import secure_filename

from utils.whisper_transcriber import transcribe_audio
from utils.background_remover import BackgroundRemover

UPLOAD_FOLDER = 'uploads'
AUDIO_FOLDER = os.path.join(UPLOAD_FOLDER, 'audio')
PROCESSED_FOLDER = os.path.join(UPLOAD_FOLDER, 'processed')
SUBTITLES_FOLDER = os.path.join(UPLOAD_FOLDER, 'subtitles')

app = Flask(__name__)

# 설정은 app 객체 생성 후에 진행해야 합니다
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['AUDIO_FOLDER'] = AUDIO_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['SUBTITLES_FOLDER'] = SUBTITLES_FOLDER

CORS(app, resources={r"/*": {"origins": "*"}})  # Allow requests from all origins

# 필요한 폴더 생성
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(SUBTITLES_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '파일이 요청에 없습니다.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400

    if file and allowed_file(file.filename):
        timestamp = int(time.time())
        original_filename = secure_filename(file.filename)
        base_name = os.path.splitext(original_filename)[0]
        unique_filename = f"{base_name}_{timestamp}"
        
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_filename}{os.path.splitext(original_filename)[1]}")
        file.save(save_path)

        try:
            processed_video = save_path  # 원본 그대로 사용

            # Whisper로 자막 생성
            subtitles_path = transcribe_audio(processed_video)

            # remove_background 옵션 확인
            remove_bg = request.form.get('remove_background') == 'true'
            if remove_bg:
                remover = BackgroundRemover()
                processed_video = remover.remove_background(processed_video)

            processed_filename = os.path.basename(processed_video)
            subtitles_filename = os.path.basename(subtitles_path)

            return jsonify({
                'message': '파일 처리 완료',
                'videoUrl': f'http://localhost:5000/processed/{processed_filename}',
                'subtitlesUrl': f'http://localhost:5000/subtitles/{subtitles_filename}',
                'fileName': os.path.splitext(processed_filename)[0]
            })

        except Exception as e:
            print(f"Error processing video: {e}")
            return jsonify({'error': '서버 처리 중 오류 발생'}), 500

    return jsonify({'error': '허용되지 않는 파일 형식입니다.'}), 400

@app.route('/process', methods=['POST'])
def process_video():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    video = request.files['video']
    mode = request.form.get('mode', 'remove')

    # Save the uploaded video
    video_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(video.filename))
    video.save(video_path)

    # Process the video based on the mode
    processed_video_path = video_path  # Placeholder for actual processing logic

    return jsonify({
        'original_url': f'http://localhost:5000/uploads/{os.path.basename(video_path)}',
        'processed_url': f'http://localhost:5000/processed/{os.path.basename(processed_video_path)}'
    })

@app.route('/api/status', methods=['GET'])
def api_status():
    return jsonify({"status": "Server is running", "timestamp": time.time()})

if __name__ == '__main__':
    app.run(debug=True)
