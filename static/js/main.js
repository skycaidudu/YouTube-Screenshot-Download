let globalFrames = [];

async function analyzeVideo() {
    const urlInput = document.getElementById('youtube-url');
    const url = urlInput.value.trim();
    
    if (!url) {
        alert('请输入YouTube URL');
        return;
    }

    try {
        const response = await fetch('/api/analyze_frames', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: url })
        });

        const data = await response.json();
        
        if (data.success) {
            displayFrames(data.frames);
        } else {
            alert('分析失败: ' + data.error);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('发生错误，请查看控制台');
    }
}

function displayFrames(frames) {
    globalFrames = frames;
    const container = document.getElementById('frames-container');
    container.innerHTML = '';
    
    frames.forEach((frame, index) => {
        const frameDiv = document.createElement('div');
        frameDiv.className = 'frame-item';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'frame-checkbox';
        checkbox.dataset.frameIndex = index;
        checkbox.checked = true;
        
        const img = document.createElement('img');
        img.src = `data:image/jpeg;base64,${frame.data}`;
        
        const timestamp = document.createElement('div');
        timestamp.className = 'frame-timestamp';
        timestamp.textContent = `${Math.floor(frame.timestamp)}s`;
        
        frameDiv.appendChild(checkbox);
        frameDiv.appendChild(img);
        frameDiv.appendChild(timestamp);
        container.appendChild(frameDiv);
    });
    
    document.getElementById('download-buttons').style.display = 'flex';
}

async function downloadSelected() {
    const selectedFrames = [];
    const checkboxes = document.querySelectorAll('.frame-checkbox:checked');
    
    checkboxes.forEach(checkbox => {
        const index = parseInt(checkbox.dataset.frameIndex);
        selectedFrames.push(globalFrames[index]);
    });
    
    if (selectedFrames.length === 0) {
        alert('请至少选择一个场景');
        return;
    }
    
    try {
        const response = await fetch('/api/download_frames', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ frames: selectedFrames })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'selected_scenes.zip';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } else {
            alert('下载失败');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('下载出错，请查看控制台');
    }
}

async function downloadFrames() {
    if (!globalFrames || globalFrames.length === 0) {
        alert('No frames available to download');
        return;
    }
    
    try {
        const response = await fetch('/api/download_frames', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ frames: globalFrames })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'all_scenes.zip';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } else {
            alert('下载失败');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('下载出错，请查看控制台');
    }
} 