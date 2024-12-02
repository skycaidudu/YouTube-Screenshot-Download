async function getScreenshots() {
    const urlInput = document.getElementById('youtube-url');
    const loading = document.getElementById('loading');
    const container = document.getElementById('screenshots-container');
    
    if (!urlInput.value) {
        alert('Please enter a YouTube URL');
        return;
    }

    try {
        loading.style.display = 'block';
        container.innerHTML = '';
        
        // 直接发送URL到后端
        const response = await fetch('/api/analyze_frames', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: urlInput.value
            })
        });

        if (!response.ok) {
            throw new Error(`Scene analysis failed: ${response.status}`);
        }

        const data = await response.json();
        if (data.success) {
            displayScenes(data.frames, container);
        } else {
            throw new Error(data.error || 'Failed to analyze video');
        }

    } catch (error) {
        console.error('Error details:', error);
        alert('Error processing video: ' + error.message);
    } finally {
        loading.style.display = 'none';
    }
}

function displayScenes(frames, container) {
    const scenesContainer = document.createElement('div');
    scenesContainer.className = 'scenes-container';
    
    frames.forEach((frame, index) => {
        const sceneDiv = document.createElement('div');
        sceneDiv.className = 'scene-item';
        
        const img = document.createElement('img');
        img.src = `data:image/jpeg;base64,${frame.data}`;
        img.className = 'scene-thumbnail';
        
        const timestamp = document.createElement('div');
        timestamp.className = 'timestamp';
        timestamp.textContent = `${Math.floor(frame.timestamp)}s`;
        
        sceneDiv.appendChild(img);
        sceneDiv.appendChild(timestamp);
        scenesContainer.appendChild(sceneDiv);
    });
    
    container.appendChild(scenesContainer);
}

// 辅助函数：从URL中提取视频ID
function extractVideoId(url) {
    const match = url.match(/[?&]v=([^&]+)/);
    return match ? match[1] : url.split('/').pop();
} 