document.addEventListener('DOMContentLoaded', function() {
    // Get video path from URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const videoPath = urlParams.get('video');
    
    // Set up video player
    const videoPlayer = document.getElementById('videoPlayer');
    if (videoPath) {
        videoPlayer.src = videoPath;
    }

    // Handle transcript view switching
    const diarizedBtn = document.getElementById('diarizedBtn');
    const fullBtn = document.getElementById('fullBtn');
    const transcriptContent = document.getElementById('transcriptContent');

    diarizedBtn.addEventListener('click', function() {
        switchTranscriptView('diarized');
    });

    fullBtn.addEventListener('click', function() {
        switchTranscriptView('full');
    });

    function switchTranscriptView(type) {
        if (type === 'diarized') {
            diarizedBtn.classList.add('active');
            fullBtn.classList.remove('active');
            loadDiarizedTranscript();
        } else {
            fullBtn.classList.add('active');
            diarizedBtn.classList.remove('active');
            loadFullTranscript();
        }
    }

    function loadDiarizedTranscript() {
        transcriptContent.innerHTML = '<div class="alert alert-info">Loading transcript...</div>';
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.get_diarized_transcript(videoPath).then(response => {
                if (response.success) {
                    displayDiarizedTranscript(response.segments);
                } else {
                    transcriptContent.innerHTML = `<div class="alert alert-danger">Error loading transcript: ${response.error}</div>`;
                }
            }).catch(error => {
                transcriptContent.innerHTML = `<div class="alert alert-danger">Error loading transcript: ${error}</div>`;
            });
        }
    }

    function loadFullTranscript() {
        transcriptContent.innerHTML = '<div class="alert alert-info">Loading transcript...</div>';
        if (window.pywebview && window.pywebview.api) {
            // Get video name from the path
            const videoName = videoPath.split('/').pop();  // Gets the filename from the path
            console.log("Loading transcript for video:", videoName);
            
            window.pywebview.api.get_transcript(videoName).then(response => {
                if (response.success && response.data) {
                    console.log("Transcript loaded:", response.data);
                    transcriptContent.innerHTML = `
                        <div class="transcript-container">
                            <h3>Transcript</h3>
                            <p class="timestamp">Created: ${response.data.timestamp}</p>
                            <div class="transcript-text">${response.data.full_transcript}</div>
                        </div>`;
                } else {
                    console.error("Failed to load transcript:", response.error);
                    transcriptContent.innerHTML = `
                        <div class="alert alert-danger">
                            Error loading transcript: ${response.error || 'Transcript not found'}
                        </div>`;
                }
            }).catch(error => {
                console.error("Error loading transcript:", error);
                transcriptContent.innerHTML = `
                    <div class="alert alert-danger">
                        Error loading transcript: ${error}
                    </div>`;
            });
        }
    }

    function displayDiarizedTranscript(segments) {
        transcriptContent.innerHTML = segments.map(segment => `
            <div class="transcript-segment" data-start="${segment.start}">
                <div class="speaker-label">Speaker ${segment.speaker}</div>
                <div class="timestamp">${segment.start} - ${segment.end}</div>
                <div class="text">${segment.text}</div>
            </div>
        `).join('');

        // Add click handlers to jump to video timestamp
        document.querySelectorAll('.transcript-segment').forEach(segment => {
            segment.addEventListener('click', function() {
                const startTime = timeToSeconds(this.dataset.start);
                videoPlayer.currentTime = startTime;
                videoPlayer.play();
            });
        });
    }

    function timeToSeconds(timeString) {
        // Convert "Xm Ys" format to seconds
        const match = timeString.match(/(\d+)m\s*([\d.]+)s/);
        if (match) {
            return parseInt(match[1]) * 60 + parseFloat(match[2]);
        }
        return 0;
    }

    // Wait for pywebview to be ready
    function initializeTranscript() {
        if (window.pywebview && window.pywebview.api) {
            switchTranscriptView('full');
        } else {
            transcriptContent.innerHTML = '<div class="alert alert-info">Initializing...</div>';
            setTimeout(initializeTranscript, 100);
        }
    }

    // Start initialization
    initializeTranscript();
}); 