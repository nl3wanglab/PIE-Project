function addVideo() {
    // This function is now handled by the modal
}

function viewEditVideo(videoPath, guid) {
    window.location.href = `video-viewer.html?video=${encodeURIComponent(videoPath)}&guid=${encodeURIComponent(guid)}`;
}

function arrayBufferToBase64(buffer) {
    let binary = '';
    const bytes = new Uint8Array(buffer);
    const len = bytes.byteLength;
    for (let i = 0; i < len; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return window.btoa(binary);
}

document.getElementById('videoSettingsForm').addEventListener('submit', function(event) {
    event.preventDefault();
    
    const videoFile = document.getElementById('videoFile').files[0];
    const whisperModel = document.getElementById('whisperModel').value;
    const useDiarization = document.getElementById('useDiarization').checked;

    if (!videoFile) {
        showMessage('No video file selected.', 'error');
        return;
    }

    // Close the modal immediately
    $('#settingsModal').modal('hide');

    // Create FormData and append all settings
    const formData = new FormData();
    formData.append('videoFile', videoFile);
    formData.append('whisperModel', whisperModel);
    formData.append('useDiarization', useDiarization);

    console.log(`Uploading video: ${videoFile.name} with diarization: ${useDiarization}`);
    uploadVideo(videoFile, useDiarization);
});

function saveVideoInfo(videoInfo) {
    // Save video information to local storage or send to server
    let videos = JSON.parse(localStorage.getItem('videos')) || [];
    videos.push(videoInfo);
    localStorage.setItem('videos', JSON.stringify(videos));
}

function deleteVideoCard(button) {
    const card = button.closest('.col-md-4');
    card.remove();
    // Update local storage or server with deletion
    let videos = JSON.parse(localStorage.getItem('videos')) || [];
    videos = videos.filter(video => video.name !== card.querySelector('.card-title').textContent);
    localStorage.setItem('videos', JSON.stringify(videos));
}

function loadVideos() {
    const videos = JSON.parse(localStorage.getItem('videos')) || [];
    const videoCards = document.getElementById('video-cards');
    videos.forEach(video => {
        const videoCard = document.createElement('div');
        videoCard.className = 'col-md-4 mb-4';
        videoCard.innerHTML = `
            <div class="card">
                <div class="card-body text-center">
                    <h5 class="card-title">${video.name}</h5>
                    <p>Added on ${video.date}</p>
                    <button class="btn btn-danger mt-2" onclick="deleteVideoCard(this)">Delete</button>
                </div>
            </div>
        `;
        videoCards.insertBefore(videoCard, videoCards.lastElementChild);
    });
}

// Load videos on page load
document.addEventListener('DOMContentLoaded', loadVideos);

function updateCardWithMedia(loadingCard, originalFilename, mediaUrl, isVideo, guid) {
    const cardBody = loadingCard.querySelector('.card-body');
    cardBody.innerHTML = `
        <h5 class="card-title">${originalFilename}</h5>
        <div class="video-thumbnail mb-3" data-guid="${guid}">
            <video preload="metadata" muted>
                <source src="${mediaUrl}" type="video/mp4">
            </video>
            <div class="play-icon">▶</div>
        </div>
        <p>Added on ${new Date().toLocaleString()}</p>
        <button class="btn btn-primary mt-2 mr-2" onclick="viewEditVideo('${mediaUrl}', '${guid}')">View</button>
        <button class="btn btn-danger mt-2" onclick="deleteVideo('${guid}')">Delete</button>
        <div class="transcription-status status-processing">
            Transcription: Processing
        </div>
    `;

    // Set up video thumbnail behavior
    const videoElement = cardBody.querySelector('video');
    const thumbnailContainer = cardBody.querySelector('.video-thumbnail');
    
    videoElement.addEventListener('loadedmetadata', function() {
        const seekTime = Math.min(1, this.duration * 0.25);
        this.currentTime = seekTime;
    });

    thumbnailContainer.addEventListener('mouseenter', function() {
        videoElement.play();
    });

    thumbnailContainer.addEventListener('mouseleave', function() {
        videoElement.pause();
        const seekTime = Math.min(1, videoElement.duration * 0.25);
        videoElement.currentTime = seekTime;
    });

    thumbnailContainer.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
    });
}

// Example function to determine if a file is a video
function isVideoFile(filename) {
    const videoExtensions = ['mp4', 'webm', 'ogg'];
    const extension = filename.split('.').pop().toLowerCase();
    return videoExtensions.includes(extension);
}

// Example function to determine if a file is an image
function isImageFile(filename) {
    const imageExtensions = ['jpg', 'jpeg', 'png', 'gif'];
    const extension = filename.split('.').pop().toLowerCase();
    return imageExtensions.includes(extension);
}

// Modify the existing function to handle both video and image files
function handleFileUpload(event) {
    event.preventDefault();
    const fileInput = document.getElementById('videoFile');
    const useDiarization = document.getElementById('useDiarization').checked;
    const file = fileInput.files[0];

    if (!file) {
        alert('Please select a file first!');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('useDiarization', useDiarization);

    // Show upload status
    const statusElement = document.getElementById('uploadStatus');
    statusElement.innerHTML = `
        <div class="alert alert-info">
            <div class="spinner-border spinner-border-sm" role="status">
                <span class="sr-only">Loading...</span>
            </div>
            Uploading video...
        </div>
    `;

    // Make API call to upload
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            statusElement.innerHTML = `
                <div class="alert alert-success">
                    Upload successful! Processing video...
                    ${useDiarization ? '<br>Speaker diarization enabled - this may take a few minutes.' : ''}
                </div>
            `;
            // Additional handling as needed
        } else {
            statusElement.innerHTML = `
                <div class="alert alert-danger">
                    Upload failed: ${data.error}
                </div>
            `;
        }
    })
    .catch(error => {
        console.error('Error:', error);
        statusElement.innerHTML = `
            <div class="alert alert-danger">
                Upload failed: ${error.message}
            </div>
        `;
    });
}

function deleteVideo(filename) {
    if (confirm(`Are you sure you want to delete ${filename}?`)) {
        window.pywebview.api.delete_video(filename)
            .then(response => {
                if (response.success) {
                    // Remove the video element and its container if it exists
                    const videoContainer = document.getElementById(`video-container-${filename}`);
                    if (videoContainer) {
                        videoContainer.remove();
                    }
                    showMessage('Video deleted successfully', 'success');
                } else {
                    showMessage(`Error deleting video: ${response.error}`, 'error');
                }
            })
            .catch(error => {
                showMessage(`Error deleting video: ${error}`, 'error');
            });
    }
}

// Modify your existing uploadChunk function to add a delete button after successful upload
function handleUploadSuccess(response, filename) {
    const videoContainer = document.createElement('div');
    videoContainer.id = `video-container-${filename}`;
    videoContainer.className = 'video-container';

    const video = document.createElement('video');
    video.controls = true;
    video.style.maxWidth = '100%';
    video.src = `static/${response.path}`;

    const deleteButton = document.createElement('button');
    deleteButton.textContent = 'Delete Video';
    deleteButton.className = 'delete-button';
    deleteButton.onclick = () => deleteVideo(filename);

    videoContainer.appendChild(video);
    videoContainer.appendChild(deleteButton);
    document.getElementById('videoPreview').appendChild(videoContainer);
}

// Add this function to handle message display
function showMessage(message, type = 'info') {
    // Create message container if it doesn't exist
    let messageContainer = document.getElementById('message-container');
    if (!messageContainer) {
        messageContainer = document.createElement('div');
        messageContainer.id = 'message-container';
        messageContainer.style.position = 'fixed';
        messageContainer.style.top = '20px';
        messageContainer.style.right = '20px';
        messageContainer.style.zIndex = '9999';
        document.body.appendChild(messageContainer);
    }

    // Create message element
    const messageElement = document.createElement('div');
    messageElement.className = `alert alert-${type}`;
    messageElement.role = 'alert';
    messageElement.textContent = message;

    // Add to container
    messageContainer.appendChild(messageElement);

    // Auto remove after 5 seconds
    setTimeout(() => {
        messageElement.remove();
    }, 5000);
}

// Add this function to check transcription status
async function checkTranscriptionStatus(filename, guid) {
    try {
        const response = await window.pywebview.api.get_transcription_status(guid);
        if (response.success) {
            const card = document.querySelector(`[data-video="${filename}"]`);
            if (card) {
                const statusElement = card.querySelector('.transcription-status');
                if (!statusElement) {
                    return;
                }
                
                const status = response.status;
                let statusText = '';
                
                if (status === 'COMPLETED') {
                    statusText = 'Transcription Complete ✓';
                    console.log('Transcription completed for:', guid);
                    console.log('Transcript:', response.full_transcript);
                    if (card.dataset.statusInterval) {
                        clearInterval(parseInt(card.dataset.statusInterval));
                    }
                } else if (status === 'FAILED') {
                    statusText = `Transcription Failed: ${response.error || 'Unknown error'}`;
                    console.error('Transcription failed:', response.error);
                    if (card.dataset.statusInterval) {
                        clearInterval(parseInt(card.dataset.statusInterval));
                    }
                } else if (status === 'PROCESSING') {
                    statusText = 'Transcribing... (This may take a few minutes)';
                } else {
                    statusText = `Transcription: ${status}`;
                }
                
                statusElement.textContent = statusText;
                statusElement.className = `transcription-status status-${status.toLowerCase()}`;
            }
        }
    } catch (error) {
        console.error('Error checking transcription status:', error);
    }
}

// Add this function to handle GUID storage
function saveVideoGUID(originalFilename, guid) {
    let videoMappings = JSON.parse(localStorage.getItem('videoMappings')) || {};
    videoMappings[originalFilename] = guid;
    localStorage.setItem('videoMappings', JSON.stringify(videoMappings));
}

// Modify the uploadVideo function to handle GUIDs
async function uploadVideo(file, useDiarization = false) {
    const chunkSize = 1024 * 1024; // 1MB chunks
    let offset = 0;
    let isFirstChunk = true;
    const totalChunks = Math.ceil(file.size / chunkSize);
    let currentChunk = 0;

    // Create a loading card
    const videoCards = document.getElementById('video-cards');
    const loadingCard = document.createElement('div');
    loadingCard.className = 'col-md-4 mb-4';
    loadingCard.innerHTML = `
        <div class="card" data-video="${file.name}">
            <div class="card-body text-center">
                <h5 class="card-title">${file.name}</h5>
                <div class="progress mb-3" style="height: 20px;">
                    <div class="progress-bar progress-bar-striped progress-bar-animated" 
                         role="progressbar" style="width: 0%; transition: width 0.1s ease">
                    </div>
                </div>
                <p class="mt-3">Uploading: 0/${formatFileSize(file.size)} (0%)</p>
                <div class="transcription-status status-pending">
                    Waiting for upload to complete...
                </div>
            </div>
        </div>
    `;
    videoCards.insertBefore(loadingCard, videoCards.lastElementChild);

    try {
        console.log(`Starting upload of ${file.name} (${formatFileSize(file.size)})`);
        
        let guid = null;
        
        while (offset < file.size) {
            currentChunk++;
            const chunk = file.slice(offset, offset + chunkSize);
            const reader = new FileReader();
            
            // Convert chunk to base64
            const base64Chunk = await new Promise((resolve, reject) => {
                reader.onload = () => resolve(reader.result);
                reader.onerror = reject;
                reader.readAsDataURL(chunk);
            });

            // Upload chunk
            const response = await window.pywebview.api.upload_video_chunk(
                base64Chunk, 
                guid ? `${guid}${file.name.substr(file.name.lastIndexOf('.'))}` : file.name,
                isFirstChunk,
                file.size,
                useDiarization
            );

            if (!response.success) {
                throw new Error(response.error || 'Upload failed');
            }

            // Store GUID from first chunk
            if (isFirstChunk && response.guid) {
                guid = response.guid;
                saveVideoGUID(file.name, guid);
            }

            // Calculate progress
            const uploadedSize = Math.min(offset + chunkSize, file.size);
            const progress = (uploadedSize / file.size) * 100;
            
            // Update UI with requestAnimationFrame for smoother updates
            requestAnimationFrame(() => {
                const progressBar = loadingCard.querySelector('.progress-bar');
                const progressText = loadingCard.querySelector('p.mt-3');
                progressBar.style.width = `${progress}%`;
                progressBar.setAttribute('aria-valuenow', progress);
                progressText.textContent = `Uploading: ${formatFileSize(uploadedSize)}/${formatFileSize(file.size)} (${Math.round(progress)}%)`;
            });
            
            // Log progress
            console.log(`Uploaded chunk ${currentChunk}/${totalChunks} (${Math.round(progress)}%)`);

            offset += chunkSize;
            isFirstChunk = false;
            
            // Add a small delay to prevent overwhelming the UI
            await new Promise(resolve => setTimeout(resolve, 10));
        }

        console.log('Upload complete, starting transcription...');
        
        // Start checking transcription status
        const checkStatus = () => {
            checkTranscriptionStatus(file.name, guid);
        };
        const statusInterval = setInterval(checkStatus, 2000);
        const card = loadingCard.querySelector('.card');
        if (card) {
            card.dataset.statusInterval = statusInterval;
        }

        // Update the card with the completed upload
        updateCardWithMedia(
            loadingCard, 
            file.name,
            `uploaded_videos/${guid}${file.name.substr(file.name.lastIndexOf('.'))}`,
            true,
            guid
        );
        
    } catch (error) {
        console.error('Upload error:', error);
        showMessage(`Upload failed: ${error.message}`, 'error');
        loadingCard.remove();
    }
}

// Add this helper function for formatting file sizes
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Function to create video card (modify your existing function)
function createVideoCard(filename, videoPath) {
    const card = document.createElement('div');
    card.className = 'video-card';
    card.setAttribute('data-video', filename);
    
    // ... existing card creation code ...
    
    // Add transcription status element
    const statusDiv = document.createElement('div');
    statusDiv.className = 'transcription-status status-pending';
    statusDiv.textContent = 'Transcription: Pending';
    card.appendChild(statusDiv);
    
    return card;
}

function viewTranscript(videoName) {
    window.pywebview.api.get_pure_transcript(videoName).then(response => {
        if (response.success) {
            // Create or get modal
            let modal = document.getElementById('transcriptModal');
            if (!modal) {
                modal = document.createElement('div');
                modal.id = 'transcriptModal';
                modal.className = 'modal';
                document.body.appendChild(modal);
            }

            // Update modal content
            modal.innerHTML = `
                <div class="modal-content">
                    <span class="close">&times;</span>
                    <h2>Transcript for ${videoName}</h2>
                    <p class="timestamp">Transcribed: ${response.timestamp}</p>
                    <div class="transcript-text">${response.text}</div>
                </div>
            `;

            // Show modal
            modal.style.display = "block";

            // Close button functionality
            const closeBtn = modal.querySelector('.close');
            closeBtn.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                modal.style.display = "none";
            }

            // Click outside to close
            modal.onclick = function(event) {
                if (event.target === modal) {
                    modal.style.display = "none";
                }
            }

            // Prevent clicks inside modal content from closing the modal
            modal.querySelector('.modal-content').onclick = function(e) {
                e.stopPropagation();
            }
        } else {
            alert('Error loading transcript: ' + response.error);
        }
    });
}

// Add this function to handle the settings modal
function showSettingsModal() {
    const modal = document.getElementById('settingsModal');
    if (modal) {
        modal.style.display = 'block';
        
        // Close button functionality
        const closeBtn = modal.querySelector('.close');
        if (closeBtn) {
            closeBtn.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                modal.style.display = "none";
            }
        }

        // Click outside to close
        window.onclick = function(event) {
            if (event.target === modal) {
                modal.style.display = "none";
            }
        }

        // Prevent clicks inside modal content from closing the modal
        const modalContent = modal.querySelector('.modal-content');
        if (modalContent) {
            modalContent.onclick = function(e) {
                e.stopPropagation();
            }
        }
    }
}

document.getElementById('returnButton').addEventListener('click', function() {
    window.history.back(); // Go back to the previous page
});