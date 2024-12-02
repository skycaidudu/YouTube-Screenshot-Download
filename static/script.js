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
        
        // 首先进行场景分析
        const scenesResponse = await fetch('/api/analyze_frames', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: urlInput.value.trim()
            })
        });

        if (!scenesResponse.ok) {
            throw new Error(`Scene analysis failed: ${scenesResponse.status}`);
        }

        const scenesData = await scenesResponse.json();
        if (scenesData.success) {
            // 创建场景容器
            const scenesContainer = document.createElement('div');
            scenesContainer.className = 'scenes-container';
            
            // 添加标题
            const scenesTitle = document.createElement('h2');
            scenesTitle.textContent = 'Scene Analysis Results';
            scenesTitle.className = 'scenes-title';
            container.appendChild(scenesTitle);
            
            // 添加场景图片
            scenesData.frames.forEach((frame, index) => {
                const sceneDiv = document.createElement('div');
                sceneDiv.className = 'scene-item';
                
                const img = document.createElement('img');
                img.src = `data:image/jpeg;base64,${frame.data}`;
                img.className = 'scene-thumbnail';
                
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.dataset.frameIndex = index;
                
                sceneDiv.appendChild(img);
                sceneDiv.appendChild(checkbox);
                scenesContainer.appendChild(sceneDiv);
            });
            
            container.appendChild(scenesContainer);
            
            // 添加下载按钮容器
            const buttonContainer = document.createElement('div');
            buttonContainer.className = 'button-container';
            
            // 添加"下载选中场景"按钮
            const downloadSelectedBtn = document.createElement('button');
            downloadSelectedBtn.className = 'download-button';
            downloadSelectedBtn.textContent = 'Download Selected Scenes';
            downloadSelectedBtn.onclick = () => downloadSelectedScenes(scenesData.frames);
            
            // 添加"下载所有场景"按钮
            const downloadAllBtn = document.createElement('button');
            downloadAllBtn.className = 'download-button';
            downloadAllBtn.textContent = 'Download All Scenes';
            downloadAllBtn.onclick = () => {
                // 选中所有复选框
                document.querySelectorAll('.scene-item input[type="checkbox"]')
                    .forEach(checkbox => checkbox.checked = true);
                // 下载所有场景
                downloadSelectedScenes(scenesData.frames);
            };
            
            buttonContainer.appendChild(downloadSelectedBtn);
            buttonContainer.appendChild(downloadAllBtn);
            container.appendChild(buttonContainer);
        }

        // 然后获取视频信息
        const infoResponse = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: urlInput.value.trim()
            })
        });

        if (!infoResponse.ok) {
            throw new Error(`Video info analysis failed: ${infoResponse.status}`);
        }

        const infoData = await infoResponse.json();
        if (infoData.success) {
            // 创建视频信息标题
            const infoTitle = document.createElement('h2');
            infoTitle.textContent = 'Video Information';
            infoTitle.className = 'info-title';
            container.appendChild(infoTitle);

            // 创建视频信息表格
            const infoTable = document.createElement('table');
            infoTable.className = 'video-info-table';
            
            // 添加视频信息
            const fields = [
                ['Title', infoData.data.title],
                ['Author', infoData.data.author],
                ['Upload Date', infoData.data.publish_date],
                ['Duration', infoData.data.duration],
                ['Views', infoData.data.views],
                ['File Size', infoData.data.filesize]
            ];
            
            fields.forEach(([label, value]) => {
                const row = infoTable.insertRow();
                const labelCell = row.insertCell();
                const valueCell = row.insertCell();
                labelCell.textContent = label;
                valueCell.textContent = value || 'N/A';
            });
            
            container.appendChild(infoTable);

            // 添加下载视频按钮
            const downloadBtn = document.createElement('button');
            downloadBtn.className = 'download-button';
            downloadBtn.textContent = 'Download Video';
            downloadBtn.onclick = () => downloadVideo(urlInput.value);
            container.appendChild(downloadBtn);
        }
    } catch (error) {
        console.error('Error details:', error);
        alert('Error processing video: ' + error.message);
    } finally {
        loading.style.display = 'none';
    }
}

async function downloadVideo(url) {
    try {
        const response = await fetch('/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: url.trim() })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        if (data.success) {
            alert(`Video downloaded successfully as: ${data.file_name}`);
        } else {
            throw new Error(data.error || 'Download failed');
        }
    } catch (error) {
        console.error('Download error:', error);
        alert('Download failed: ' + error.message);
    }
}

async function analyzeScenes(url) {
    const container = document.getElementById('screenshots-container');
    const loading = document.getElementById('loading');
    
    try {
        loading.style.display = 'block';
        
        const response = await fetch('/api/analyze_frames', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        if (data.success) {
            // 创建场景容器
            const scenesContainer = document.createElement('div');
            scenesContainer.className = 'scenes-container';
            
            // 添加场景图片
            data.frames.forEach((frame, index) => {
                const sceneDiv = document.createElement('div');
                sceneDiv.className = 'scene-item';
                
                const img = document.createElement('img');
                img.src = `data:image/jpeg;base64,${frame.data}`;
                img.className = 'scene-thumbnail';
                
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.dataset.frameIndex = index;
                
                sceneDiv.appendChild(img);
                sceneDiv.appendChild(checkbox);
                scenesContainer.appendChild(sceneDiv);
            });
            
            // 添加下载选中场景的按钮
            const downloadBtn = document.createElement('button');
            downloadBtn.className = 'download-button';
            downloadBtn.textContent = 'Download Selected Scenes';
            downloadBtn.onclick = () => downloadSelectedScenes(data.frames);
            
            container.appendChild(scenesContainer);
            container.appendChild(downloadBtn);
        }
    } catch (error) {
        console.error('Scene analysis error:', error);
        alert('Failed to analyze scenes: ' + error.message);
    } finally {
        loading.style.display = 'none';
    }
}

async function downloadSelectedScenes(frames) {
    try {
        const selectedFrames = Array.from(document.querySelectorAll('.scene-item input[type="checkbox"]:checked'))
            .map(checkbox => frames[checkbox.dataset.frameIndex].data);
            
        if (selectedFrames.length === 0) {
            alert('Please select at least one scene');
            return;
        }
        
        const response = await fetch('/api/download_frames', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ frames: selectedFrames })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // 触发下载
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'scenes.zip';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
    } catch (error) {
        console.error('Download error:', error);
        alert('Failed to download scenes: ' + error.message);
    }
} 