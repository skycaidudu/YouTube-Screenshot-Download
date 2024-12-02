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
        # 获取前端发送的帧数据
        data = request.json
        frames_data = data.get('frames', [])
        
        if not frames_data:
            return jsonify({'success': False, 'error': 'No frames data received'}), 400
            
        frames = []
        prev_frame = None
        frame_count = 0
        last_selected_frame_time = 0
        min_frame_interval = 0.3
        
        for frame_data in frames_data:
            # 解码base64图像数据
            try:
                img_data = base64.b64decode(frame_data['data'].split(',')[1])
                nparr = np.frombuffer(img_data, np.uint8)
                curr_frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if curr_frame is None:
                    continue
                    
                current_time = frame_data.get('timestamp', 0)
                
                if prev_frame is not None:
                    is_new_scene, change_rate = detect_scene_change(prev_frame, curr_frame)
                    
                    if is_new_scene and (current_time - last_selected_frame_time) >= min_frame_interval:
                        clarity = calculate_frame_clarity(curr_frame)
                        
                        # 保持原始宽高比进行缩放
                        height, width = curr_frame.shape[:2]
                        target_width = 1280
                        target_height = int(height * (target_width / width))
                        resized_frame = cv2.resize(curr_frame, (target_width, target_height))
                        
                        # 编码为JPEG
                        _, buffer = cv2.imencode('.jpg', resized_frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                        frame_base64 = base64.b64encode(buffer).decode('utf-8')
                        
                        frames.append({
                            'data': frame_base64,
                            'index': frame_count,
                            'change_rate': float(change_rate),
                            'clarity': float(clarity),
                            'timestamp': current_time
                        })
                        
                        last_selected_frame_time = current_time
                
                prev_frame = curr_frame.copy()
                frame_count += 1
                
            except Exception as e:
                print(f"Error processing frame: {str(e)}")
                continue
        
        # 如果场景太多，只保留清晰度最高的几个
        if len(frames) > 6:
            frames.sort(key=lambda x: x['clarity'], reverse=True)
            frames = frames[:6]
            frames.sort(key=lambda x: x['timestamp'])
        
        if not frames:
            return jsonify({'success': False, 'error': 'No scenes detected'}), 500
            
        return jsonify({
            'success': True,
            'frames': frames
        })
            
    except Exception as e:
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