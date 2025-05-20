from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import time
from werkzeug.utils import secure_filename
import logging

from utils.whisper_transcriber import transcribe_audio
from utils.background_remover import BackgroundRemover

# 폴더 설정
UPLOAD_FOLDER = 'uploads'
AUDIO_FOLDER = os.path.join(UPLOAD_FOLDER, 'audio')
PROCESSED_FOLDER = os.path.join(UPLOAD_FOLDER, 'processed')
SUBTITLES_FOLDER = os.path.join(UPLOAD_FOLDER, 'subtitles')

BASE_URL = os.getenv("BASE_URL", "https://aicut-backend-clean-production.up.railway.app")
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"], supports_credentials=True)  # ✅ CORS 설정 (React용)

# 경로 설정
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['AUDIO_FOLDER'] = AUDIO_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['SUBTITLES_FOLDER'] = SUBTITLES_FOLDER

# 폴더 생성
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(SUBTITLES_FOLDER, exist_ok=True)

# 로깅
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def home():
    return "✅ AICUT Backend is running!", 200

@app.route("/process", methods=["POST", "OPTIONS"])
def process_video():
    if request.method == "OPTIONS":
        return '', 200

    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    video = request.files['video']
    mode = request.form.get('mode', 'remove')
    filename = secure_filename(video.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    video.save(save_path)

    processed_path = save_path
    if mode == 'remove':
        remover = BackgroundRemover()
        processed_path = remover.remove_background(save_path)

    processed_filename = os.path.basename(processed_path)

    return jsonify({
        'original_url': f'{BASE_URL}/uploads/{filename}',
        'processed_url': f'{BASE_URL}/processed/{processed_filename}'
    })

@app.route("/uploads/<filename>")
def serve_uploaded(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/processed/<filename>")
def serve_processed(filename):
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename)

@app.route("/subtitles/<filename>")
def serve_subtitles(filename):
    return send_from_directory(app.config['SUBTITLES_FOLDER'], filename)
