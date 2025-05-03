from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import time
from werkzeug.utils import secure_filename

from utils.whisper_transcriber import transcribe_audio
from utils.background_remover import BackgroundRemover

# 폴더 경로 설정
UPLOAD_FOLDER = 'uploads'
AUDIO_FOLDER = os.path.join(UPLOAD_FOLDER, 'audio')
PROCESSED_FOLDER = os.path.join(UPLOAD_FOLDER, 'processed')
SUBTITLES_FOLDER = os.path.join(UPLOAD_FOLDER, 'subtitles')

# 배포 환경에 맞는 BASE_URL 설정
BASE_URL = os.getenv("BASE_URL", "https://aicut-backend-clean-production.up.railway.app")

# 업로드 허용 확장자
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}

app = Flask(__name__)

# CORS 설정
CORS(app, resources={r"/*": {"origins": "*"}})

# 앱 config에 경로 지정
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['AUDIO_FOLDER'] = AUDIO_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['SUBTITLES_FOLDER'] = SUBTITLES_FOLDER

# 필요한 폴더 생성
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(SUBTITLES_FOLDER, exist_ok=True)

# 허용된 파일 확장자 확인 함수
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def home():
    return "✅ AICUT Backend is running!", 200

@app.route('/api/status', methods=['GET'])
def api_status():
    return jsonify({"status": "Server is running", "timestamp": time.time()})

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
        extension = os.path.splitext(original_filename)[1]
        unique_filename = f"{base_name}_{timestamp}{extension}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(save_path)

        try:
            # 자막 생성
            subtitles_path = transcribe_audio(save_path)

            # 배경 제거 옵션 확인
            remove_bg = request.form.get('remove_background') == 'true'
            processed_video = save_path
            if remove_bg:
                remover = BackgroundRemover()
                processed_video = remover.remove_background(save_path)

            return jsonify({
                'message': '파일 처리 완료',
                'videoUrl': f'{BASE_URL}/processed/{os.path.basename(processed_video)}',
                'subtitlesUrl': f'{BASE_URL}/subtitles/{os.path.basename(subtitles_path)}',
                'fileName': os.path.splitext(os.path.basename(processed_video))[0]
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

    video_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(video.filename))
    video.save(video_path)

    # 여기에 실제 컷 편집 등 처리 로직 추가 가능
    processed_video_path = video_path

    return jsonify({
        'original_url': f'{BASE_URL}/uploads/{os.path.basename(video_path)}',
        'processed_url': f'{BASE_URL}/processed/{os.path.basename(processed_video_path)}'
    })

# 파일 서빙 라우트
@app.route('/uploads/<filename>')
def serve_uploaded(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/processed/<filename>')
def serve_processed(filename):
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename)

@app.route('/subtitles/<filename>')
def serve_subtitles(filename):
    return send_from_directory(app.config['SUBTITLES_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
