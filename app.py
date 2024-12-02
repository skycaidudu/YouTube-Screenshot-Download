from flask import Flask, render_template, request, jsonify, send_file, make_response
from googleapiclient.discovery import build
import datetime
import os
import cv2
import numpy as np
from pathlib import Path
import base64
import tempfile
import requests
from dotenv import load_dotenv
import re

# 加载环境变量
load_dotenv()

app = Flask(__name__,
    static_url_path='/static',
    static_folder='static',
    template_folder='templates'
)

# 确保 API 密钥存在
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
if not YOUTUBE_API_KEY:
    raise ValueError("YouTube API Key not found in environment variables")

# 初始化 YouTube API
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

def extract_video_id(url):
    """从各种 YouTube URL 格式中提取视频 ID"""
    patterns = [
        r'(?:v=|/v/|^)([^&\n?#]+)',  # 标准格式
        r'(?:shorts/)([^&\n?#]+)',    # Shorts 格式
        r'(?:youtu\.be/)([^&\n?#]+)', # 短链接格式
        r'(?:embed/)([^&\n?#]+)'      # 嵌入格式
    ]
    
    for pattern in patterns:
        if match := re.search(pattern, url):
            return match.group(1)
    return None

@app.after_request
def add_security_headers(response):
    """添加安全头"""
    response.headers['Content-Security-Policy'] = "default-src 'self'; \
        script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.youtube.com https://www.googleapis.com; \
        frame-src 'self' https://www.youtube.com; \
        img-src 'self' data: https://*.ytimg.com https://*.youtube.com; \
        style-src 'self' 'unsafe-inline'; \
        connect-src 'self' https://www.googleapis.com"
    return response

@app.route('/')
def index():
    response = make_response(render_template('index.html'))
    return response

@app.route('/api/analyze_frames', methods=['POST'])
def analyze_frames():
    try:
        print("Received analyze_frames request")  # 调试日志
        data = request.get_json()
        if not data or 'url' not in data:
            print("No URL in request data")  # 调试日志
            return jsonify({'success': False, 'error': 'URL is required'}), 400

        url = data['url']
        print(f"Processing URL: {url}")  # 调试日志
        
        video_id = extract_video_id(url)
        if not video_id:
            print(f"Could not extract video ID from URL: {url}")  # 调试日志
            return jsonify({'success': False, 'error': 'Invalid YouTube URL'}), 400

        print(f"Extracted video ID: {video_id}")  # 调试日志

        try:
            # 使用 YouTube API 获取视频信息
            video_response = youtube.videos().list(
                part='snippet',
                id=video_id
            ).execute()

            if not video_response.get('items'):
                print("No video found with ID:", video_id)  # 调试日志
                return jsonify({'success': False, 'error': 'Video not found'}), 404

            # 获取视频缩略图
            thumbnails = video_response['items'][0]['snippet']['thumbnails']
            maxres = thumbnails.get('maxres') or thumbnails.get('high') or thumbnails.get('medium')
            
            if not maxres:
                print("No thumbnails available for video:", video_id)  # 调试日志
                return jsonify({'success': False, 'error': 'No thumbnails available'}), 404

            # 下载缩略图
            print(f"Downloading thumbnail from: {maxres['url']}")  # 调试日志
            response = requests.get(maxres['url'])
            img_array = np.frombuffer(response.content, np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            # 调整图像大小
            height, width = frame.shape[:2]
            target_width = 1280
            target_height = int(height * (target_width / width))
            resized_frame = cv2.resize(frame, (target_width, target_height))

            # 转换为base64
            _, buffer = cv2.imencode('.jpg', resized_frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            frame_base64 = base64.b64encode(buffer).decode('utf-8')

            frames = [{
                'data': frame_base64,
                'timestamp': 0,
                'index': 0
            }]

            print("Successfully processed video")  # 调试日志
            return jsonify({
                'success': True,
                'frames': frames
            })

        except Exception as e:
            print(f"YouTube API error: {str(e)}")  # 调试日志
            return jsonify({'success': False, 'error': str(e)}), 500

    except Exception as e:
        print(f"Error in analyze_frames: {str(e)}")  # 调试日志
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)), debug=debug_mode)