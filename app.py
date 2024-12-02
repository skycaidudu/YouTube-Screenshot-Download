from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import datetime
import os
import json
import cv2
import numpy as np
from pathlib import Path
import time
import shutil
import base64
import tempfile
import zipfile

app = Flask(__name__,
    static_url_path='/static',
    static_folder='static',
    template_folder='templates'
)

# 创建临时目录
TEMP_DIR = Path("temp_frames")
TEMP_DIR.mkdir(exist_ok=True)

def format_filesize(bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024
    return f"{bytes:.2f} TB"

def calculate_frame_clarity(frame):
    """计算帧的清晰度"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()

def detect_scene_change(prev_frame, curr_frame, min_threshold=0.10, max_threshold=0.90):
    """
    检测场景变化
    :param prev_frame: 前一帧
    :param curr_frame: 当前帧
    :param min_threshold: 最小变化阈值
    :param max_threshold: 最大变化阈值
    :return: (是否是新场景, 变化程度)
    """
    # 转换为灰度图
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
    
    # 计算帧差
    diff = cv2.absdiff(prev_gray, curr_gray)
    
    # 使用更复杂的变化检测方法
    # 1. 计算整体变化率
    change_rate = np.mean(diff) / 255.0
    
    # 2. 计算局部变化
    # 将图像分成网格，检查每个网格的变化
    blocks = 4  # 将图像分成4x4的网格
    h, w = prev_gray.shape
    block_h, block_w = h // blocks, w // blocks
    
    block_changes = []
    for i in range(blocks):
        for j in range(blocks):
            y1, y2 = i * block_h, (i + 1) * block_h
            x1, x2 = j * block_w, (j + 1) * block_w
            block_diff = diff[y1:y2, x1:x2]
            block_changes.append(np.mean(block_diff) / 255.0)
    
    # 如果有任何区块变化显著，就认为是新场景
    max_block_change = max(block_changes)
    
    # 综合判断是否是新场景
    is_new_scene = (min_threshold <= change_rate <= max_threshold) or (max_block_change > max_threshold * 0.8)
    
    return is_new_scene, max(change_rate, max_block_change)

def find_clearest_frame(cap, center_frame_no, window_size=30):
    """
    在指定帧的前后范围内寻找最清晰的帧
    :param cap: VideoCapture对象
    :param center_frame_no: 中心帧号
    :param window_size: 搜索窗口大小
    :return: 最清晰的帧和其清晰度
    """
    start_frame = max(0, center_frame_no - window_size)
    end_frame = center_frame_no + window_size
    max_clarity = -1
    clearest_frame = None
    
    # 保存当前帧位置
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
        # 恢复到原始位置
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)
    
    return clearest_frame, max_clarity

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_video():
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 400
        
    try:
        url = request.json.get('url')
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            video_info = {
                'title': info.get('title', 'Unknown'),
                'thumbnail': info.get('thumbnail', ''),
                'description': info.get('description', 'No description')[:200],
                'duration': str(datetime.timedelta(seconds=int(info.get('duration', 0)))),
                'author': info.get('uploader', 'Unknown'),
                'publish_date': datetime.datetime.strptime(info['upload_date'], '%Y%m%d').strftime('%Y-%m-%d'),
                'views': format(info.get('view_count', 0), ','),
                'filesize': format_filesize(info.get('filesize', 0)) if info.get('filesize') else "Unknown"
            }
            
            return jsonify({
                'success': True,
                'data': video_info
            })

    except Exception as e:
        print(f"Error in analyze_video: {str(e)}")  # 添加服务器端日志
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download', methods=['POST'])
def download_video():
    try:
        url = request.json.get('url')
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400
        
        # 设置下载路径为用户的Downloads文件夹
        download_path = os.path.expanduser("~/Downloads")
        ydl_opts = {
            'format': 'best',  # 下载最佳质量
            'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_name = f"{info['title']}.{info['ext']}"
        
        return jsonify({
            'success': True,
            'message': 'Video downloaded successfully',
            'file_name': file_name
        })
        
    except Exception as e:
        print(f"Download error: {str(e)}")  # 添加错误日志
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
            'no_warnings': True
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
        min_frame_interval = 0.3  # 减少最小帧间隔
        
        # 获取视频的FPS和总帧数
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # 特殊处理第一帧（封面图）
        ret, first_frame = cap.read()
        if ret:
            # 寻找开头最清晰的帧
            clearest_first_frame, clarity = find_clearest_frame(cap, 0, window_size=15)
            if clearest_first_frame is not None:
                first_frame = clearest_first_frame
            
            # 保持原始宽高比进行缩放
            height, width = first_frame.shape[:2]
            target_width = 1280  # 提高目标宽度
            target_height = int(height * (target_width / width))
            resized_frame = cv2.resize(first_frame, (target_width, target_height))
            
            # 使用更高的JPEG质量
            _, buffer = cv2.imencode('.jpg', resized_frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            frames.append({
                'data': frame_base64,
                'index': 0,
                'change_rate': 1.0,
                'clarity': float(clarity),
                'timestamp': 0.0
            })
            
            prev_frame = first_frame.copy()
            last_selected_frame_time = 0
            frame_count = 1
        
        # 处理其余帧
        while True:
            ret, curr_frame = cap.read()
            if not ret:
                break
                
            current_time = frame_count / fps
            
            if frame_count % 2 == 0:
                if prev_frame is not None:
                    is_new_scene, change_rate = detect_scene_change(prev_frame, curr_frame)
                    
                    if is_new_scene and (current_time - last_selected_frame_time) >= min_frame_interval:
                        # 在场景变化点附近寻找最清晰的帧
                        clearest_frame, clarity = find_clearest_frame(cap, frame_count)
                        if clearest_frame is not None:
                            # 保持原始宽高比进行缩放
                            height, width = clearest_frame.shape[:2]
                            target_width = 1280  # 提高目标宽度
                            target_height = int(height * (target_width / width))
                            resized_frame = cv2.resize(clearest_frame, (target_width, target_height))
                            
                            # 使用更高的JPEG质量
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
            
            # 添加进度打印
            if frame_count % 30 == 0:
                print(f"Processing: {(frame_count/total_frames)*100:.2f}%")
            
        cap.release()
        
        # 如果场景太多，只保留清晰度最高的几个
        if len(frames) > 6:
            frames.sort(key=lambda x: x['clarity'], reverse=True)
            frames = frames[:6]
            # 按时间顺序重新排序
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

        # 创建临时目录
        temp_dir = tempfile.mkdtemp(dir=TEMP_DIR)
        zip_path = os.path.join(temp_dir, 'scenes.zip')
        
        # 保存选中的帧到ZIP文件
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for i, frame_data in enumerate(frames):
                try:
                    # 正确处理base64数据
                    if isinstance(frame_data, str):
                        # 如果是字符串，假设是完整的base64数据
                        if ',' in frame_data:
                            # 如果包含逗号，取逗号后面的部分
                            img_data = base64.b64decode(frame_data.split(',')[1])
                        else:
                            # 否则直接解码
                            img_data = base64.b64decode(frame_data)
                    else:
                        # 如果是字典（从analyze_frames传来的数据格式）
                        img_data = base64.b64decode(frame_data['data'])
                    
                    frame_path = os.path.join(temp_dir, f'scene_{i+1}.jpg')
                    with open(frame_path, 'wb') as f:
                        f.write(img_data)
                    zf.write(frame_path, f'scene_{i+1}.jpg')
                except Exception as e:
                    print(f"Error processing frame {i}: {str(e)}")
                    continue
        
        # 发送文件
        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name='scenes.zip'
        )
        
    except Exception as e:
        print(f"Error in download_frames: {str(e)}")  # 添加错误日志
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        # 清理临时文件
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Error cleaning up temp files: {str(e)}")

# ... 其他路由和函数保持不变 ...

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)