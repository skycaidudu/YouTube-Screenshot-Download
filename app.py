from flask import Flask, render_template, request, jsonify, send_file
from googleapiclient.discovery import build
import yt_dlp
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
from io import BytesIO
import json
import re
import shutil

# 加载环境变量
load_dotenv()

app = Flask(__name__,
    static_url_path='/static',
    static_folder='static',
    template_folder='templates'
)

# 创建临时目录
TEMP_DIR = Path("temp_frames")
TEMP_DIR.mkdir(exist_ok=True)

# YouTube API 设置
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# 修改临时文件存储路径
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 确保目录存在
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

def calculate_frame_clarity(frame):
    """计算帧的清晰度"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()

def detect_scene_change(prev_frame, curr_frame, min_threshold=0.10, max_threshold=0.90):
    """检测场景变化"""
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

def find_clearest_frame(cap, center_frame_no, window_size=30):
    """在指定帧的前后范围内寻找最清晰的帧"""
    start_frame = max(0, center_frame_no - window_size)
    end_frame = center_frame_no + window_size
    max_clarity = -1
    clearest_frame = None
    
    current_pos = cap.get(cv2.CAP_PROP_POS_FRAMES)
    
    try:
        for frame_no in range(start_frame, end_frame):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            ret, frame = cap.read()
            if not ret:
                break
                
            clarity = calculate_frame_clarity(frame)
            if clarity > max_clarity:
                max_clarity = clarity
                clearest_frame = frame.copy()
    finally:
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)
    
    return clearest_frame, max_clarity

@app.route('/api/analyze_frames', methods=['POST'])
def analyze_frames():
    try:
        url = request.json.get('url')
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400
            
        # 创建临时文件夹
        temp_dir = tempfile.mkdtemp(dir=TEMP_DIR)
        temp_video_path = os.path.join(temp_dir, 'temp_video.mp4')
            
        # 使用 yt-dlp 下载视频
        ydl_opts = {
            'format': 'best',
            'outtmpl': temp_video_path,
            'quiet': True,
            'no_warnings': True,
            'format_sort': ['res:1080', 'ext:mp4:m4a'],
            'extractor_args': {'youtube': {'skip': ['dash', 'hls']}}
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            print(f"Download error: {str(e)}")
            return jsonify({'success': False, 'error': f'Failed to download video: {str(e)}'}), 500
            
        if not os.path.exists(temp_video_path):
            return jsonify({'success': False, 'error': 'Video download failed'}), 500
            
        # 分析视频帧
        cap = cv2.VideoCapture(temp_video_path)
        frames = []
        prev_frame = None
        frame_count = 0
        last_selected_frame_time = 0
        min_frame_interval = 0.3
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        while True:
            ret, curr_frame = cap.read()
            if not ret:
                break
                
            current_time = frame_count / fps
            
            if frame_count % 2 == 0:
                if prev_frame is not None:
                    is_new_scene, change_rate = detect_scene_change(prev_frame, curr_frame)
                    
                    if is_new_scene and (current_time - last_selected_frame_time) >= min_frame_interval:
                        clearest_frame, clarity = find_clearest_frame(cap, frame_count)
                        if clearest_frame is not None:
                            height, width = clearest_frame.shape[:2]
                            target_width = 1280
                            target_height = int(height * (target_width / width))
                            resized_frame = cv2.resize(clearest_frame, (target_width, target_height))
                            
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
            
        cap.release()
        
        # 如果场景太多，只保留清晰度最高的几个
        if len(frames) > 6:
            frames.sort(key=lambda x: x['clarity'], reverse=True)
            frames = frames[:6]
            frames.sort(key=lambda x: x['timestamp'])
        
        # 清理临时文件
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Error cleaning up temp files: {str(e)}")
        
        if not frames:
            return jsonify({'success': False, 'error': 'No scenes detected'}), 500
            
        return jsonify({
            'success': True,
            'frames': frames
        })
            
    except Exception as e:
        print(f"Error in analyze_frames: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/download_frames', methods=['POST'])
def download_frames():
    try:
        data = request.json
        frames = data.get('frames', [])
        
        if not frames:
            return jsonify({'success': False, 'error': 'No frames selected'}), 400

        temp_dir = tempfile.mkdtemp(dir=TEMP_DIR)
        zip_path = os.path.join(temp_dir, 'scenes.zip')
        
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for i, frame_data in enumerate(frames):
                try:
                    if isinstance(frame_data, str):
                        if ',' in frame_data:
                            img_data = base64.b64decode(frame_data.split(',')[1])
                        else:
                            img_data = base64.b64decode(frame_data)
                    else:
                        img_data = base64.b64decode(frame_data['data'])
                    
                    frame_path = os.path.join(temp_dir, f'scene_{i+1}.jpg')
                    with open(frame_path, 'wb') as f:
                        f.write(img_data)
                    zf.write(frame_path, f'scene_{i+1}.jpg')
                except Exception as e:
                    print(f"Error processing frame {i}: {str(e)}")
                    continue
        
        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name='scenes.zip'
        )
        
    except Exception as e:
        print(f"Error in download_frames: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Error cleaning up temp files: {str(e)}")

if __name__ == '__main__':
    app.run(debug=False)