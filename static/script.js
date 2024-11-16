function addVideo() {
    // This function is now handled by the modal
}

function viewEditVideo() {
    alert('View/Edit functionality to be implemented.');
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
    
    // Close the modal immediately
    $('#settingsModal').modal('hide');

    // Get form data
    const videoFile = document.getElementById('videoFile').files[0];
    if (!videoFile) {
        console.error('No video file selected.');
        return;
    }

    console.log(`Uploading video: ${videoFile.name}`);

    // Create a loading card
    const videoCards = document.getElementById('video-cards');
    const loadingCard = document.createElement('div');
    loadingCard.className = 'col-md-4 mb-4';
    loadingCard.innerHTML = `
        <div class="card">
            <div class="card-body text-center">
                <h5 class="card-title">Loading...</h5>
                <div class="progress">
                    <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 100%"></div>
                </div>
                <p class="mt-3">Processing video...</p>
            </div>
        </div>
    `;
    videoCards.insertBefore(loadingCard, videoCards.lastElementChild);

    // Check if PyWebView API is available
    if (window.pywebview && window.pywebview.api) {
        const chunkSize = 1024 * 1024; // 1MB
        let offset = 0;

        function readNextChunk() {
            const fileReader = new FileReader();
            const slice = videoFile.slice(offset, offset + chunkSize);

            fileReader.onload = function() {
                const arrayBuffer = fileReader.result;
                const base64String = arrayBufferToBase64(arrayBuffer);
                const fileData = `data:video/mp4;base64,${base64String}`;

                window.pywebview.api.upload_video_chunk(fileData, videoFile.name, offset === 0).then(response => {
                    if (response.success) {
                        if (offset + chunkSize < videoFile.size) {
                            offset += chunkSize;
                            readNextChunk();
                        } else {
                            console.log(`Video saved at: ${response.path}`);
                            updateCardWithMedia(loadingCard, videoFile.name, response.path, true);
                        }
                    } else {
                        console.error('Failed to save video.');
                        loadingCard.querySelector('.card-title').textContent = 'Error';
                        loadingCard.querySelector('.progress').remove();
                        loadingCard.querySelector('p').textContent = 'Failed to process video.';
                    }
                }).catch(error => {
                    console.error('Error:', error);
                    loadingCard.querySelector('.card-title').textContent = 'Error';
                    loadingCard.querySelector('.progress').remove();
                    loadingCard.querySelector('p').textContent = 'Failed to process video.';
                });
            };

            fileReader.onerror = function() {
                console.error('Error reading video file.');
            };

            fileReader.readAsArrayBuffer(slice);
        }

        readNextChunk();
    } else {
        console.error('PyWebView API is not available.');
    }
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

function updateCardWithMedia(loadingCard, filename, mediaUrl, isVideo) {
    loadingCard.querySelector('.card-title').textContent = filename;
    loadingCard.querySelector('.progress').remove();
    
    if (isVideo) {
        // Create a video thumbnail container
        const thumbnailHtml = `
            <div class="video-thumbnail mb-3">
                <video preload="metadata" muted>
                    <source src="${mediaUrl}" type="video/mp4">
                </video>
                <div class="play-icon">▶</div>
            </div>
            <p>Added on ${new Date().toLocaleString()}</p>
            <button class="btn btn-danger mt-2" onclick="deleteVideoCard(this)">Delete</button>
        `;
        
        loadingCard.querySelector('.card-body').innerHTML = `
            <h5 class="card-title">${filename}</h5>
            ${thumbnailHtml}
        `;

        // Set up the video thumbnail
        const videoElement = loadingCard.querySelector('video');
        const thumbnailContainer = loadingCard.querySelector('.video-thumbnail');
        
        videoElement.addEventListener('loadedmetadata', function() {
            const seekTime = Math.min(1, this.duration * 0.25);
            this.currentTime = seekTime;
        });

        // Add hover handlers for video playback
        thumbnailContainer.addEventListener('mouseenter', function() {
            videoElement.play();
        });

        thumbnailContainer.addEventListener('mouseleave', function() {
            videoElement.pause();
            // Reset to thumbnail frame
            const seekTime = Math.min(1, videoElement.duration * 0.25);
            videoElement.currentTime = seekTime;
        });

        // Prevent video from playing when clicking if it's not being hovered
        thumbnailContainer.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
        });
    }
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
function handleFileUpload(fileData, filename) {
    if (isVideoFile(filename)) {
        // Process video file
        const videoUrl = URL.createObjectURL(fileData); // Assuming fileData is a Blob
        updateCardWithMedia(loadingCard, filename, videoUrl, true);
    } else if (isImageFile(filename)) {
        // Process image file
        const imageUrl = URL.createObjectURL(fileData); // Assuming fileData is a Blob
        updateCardWithMedia(loadingCard, filename, imageUrl, false);
    } else {
        alert('Unsupported file type. Please select a video or image file.');
        console.error('Unsupported file type.');
        loadingCard.querySelector('.card-title').textContent = 'Error';
        loadingCard.querySelector('.progress').remove();
        loadingCard.querySelector('p').textContent = 'Unsupported file type.';
    }
}