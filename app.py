from flask import Flask, render_template, request, jsonify, send_file
from googleapiclient.discovery import build
import datetime
import os
import cv2
import numpy as np
from pathlib import Path
import base64
import tempfile
import zipfile
from dotenv import load_dotenv
import requests
import json

# 确保正确设置模板和静态文件路径
app = Flask(__name__,
    static_url_path='/static',
    static_folder='static',
    template_folder='templates'
)

# 加载环境变量
load_dotenv()

# 创建临时目录
TEMP_DIR = Path("temp_frames")
TEMP_DIR.mkdir(exist_ok=True)

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"Error rendering template: {str(e)}")
        return str(e), 500

# YouTube API 设置
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# 保留原有的辅助函数
def calculate_frame_clarity(frame):
    """计算帧的清晰度"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()

def detect_scene_change(prev_frame, curr_frame, min_threshold=0.10, max_threshold=0.90):
    """检测场景变化"""
    # 保持原有的场景检测逻辑
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
    
    diff = cv2.absdiff(prev_gray, curr_gray)
    change_rate = np.mean(diff) / 255.0
    
    blocks = 4
    h, w = prev_gray.shape
    block_h, block_w = h // blocks, w // blocks
    
    block_changes = []
    for i in range(blocks):
        for j in range(blocks):
            y1, y2 = i * block_h, (i + 1) * block_h
            x1, x2 = j * block_w, (j + 1) * block_w
            block_diff = diff[y1:y2, x1:x2]
            block_changes.append(np.mean(block_diff) / 255.0)
    
    max_block_change = max(block_changes)
    is_new_scene = (min_threshold <= change_rate <= max_threshold) or (max_block_change > max_threshold * 0.8)
    
    return is_new_scene, max(change_rate, max_block_change)

@app.route('/api/analyze_frames', methods=['POST'])
def analyze_frames():
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'success': False, 'error': 'URL is required'}), 400

        url = data['url']
        video_id = extract_video_id(url)
        
        if not video_id:
            return jsonify({'success': False, 'error': 'Invalid YouTube URL'}), 400

        # 使用YouTube API获取视频信息
        try:
            video_response = youtube.videos().list(
                part='snippet',
                id=video_id
            ).execute()

            if not video_response.get('items'):
                return jsonify({'success': False, 'error': 'Video not found'}), 404

            # 获取视频缩略图
            thumbnails = video_response['items'][0]['snippet']['thumbnails']
            maxres = thumbnails.get('maxres') or thumbnails.get('high') or thumbnails.get('medium')
            
            if not maxres:
                return jsonify({'success': False, 'error': 'No thumbnails available'}), 404

            # 下载缩略图并进行处理
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

            return jsonify({
                'success': True,
                'frames': frames
            })

        except Exception as e:
            print(f"YouTube API error: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    except Exception as e:
        print(f"Error in analyze_frames: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
        print(f"Error in analyze_frames: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 保留原有的下载帧功能
@app.route('/api/download_frames', methods=['POST'])
def download_frames():
    # 保持原有的下载帧逻辑不变
    ...

if __name__ == '__main__':
    # 确保目录结构正确
    print("Static folder:", app.static_folder)
    print("Template folder:", app.template_folder)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))