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
        diarizedBtn.classList.add('active');
        fullBtn.classList.remove('active');
        loadDiarizedTranscript();
    });

    fullBtn.addEventListener('click', function() {
        fullBtn.classList.add('active');
        diarizedBtn.classList.remove('active');
        loadFullTranscript();
    });

    function loadDiarizedTranscript() {
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.get_diarized_transcript(videoPath).then(response => {
                if (response.success) {
                    displayDiarizedTranscript(response.segments);
                } else {
                    transcriptContent.innerHTML = `<div class="alert alert-danger">Error loading transcript: ${response.error}</div>`;
                }
            });
        }
    }

    function loadFullTranscript() {
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.get_pure_transcript(videoPath).then(response => {
                if (response.success) {
                    transcriptContent.innerHTML = `<div class="transcript-segment">${response.text}</div>`;
                } else {
                    transcriptContent.innerHTML = `<div class="alert alert-danger">Error loading transcript: ${response.error}</div>`;
                }
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

    // Load diarized transcript by default
    loadDiarizedTranscript();
}); 