document.addEventListener('DOMContentLoaded', function() {
    // Get video ID from URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const videoPath = urlParams.get('video');
    
    if (videoPath) {
        // Set video source
        const videoElement = document.getElementById('mainVideo');
        videoElement.src = videoPath;
        
        // Load transcripts
        loadTranscripts(videoPath);
    }
});

async function loadTranscripts(videoPath) {
    if (window.pywebview && window.pywebview.api) {
        try {
            // Get the video filename from the path
            const filename = videoPath.split('/').pop();
            const baseFilename = filename.split('.')[0];
            
            // Load pure transcript
            const pureTranscript = await window.pywebview.api.get_pure_transcript(baseFilename);
            if (pureTranscript.success) {
                document.getElementById('pureTranscript').textContent = pureTranscript.text;
            } else {
                document.getElementById('pureTranscript').textContent = 
                    `Unable to load transcript: ${pureTranscript.error || 'Unknown error'}`;
            }
            
            // Load diarized transcript
            const diarizedTranscript = await window.pywebview.api.get_diarized_transcript(baseFilename);
            if (diarizedTranscript.success) {
                displayDiarizedTranscript(diarizedTranscript.segments);
            } else {
                document.getElementById('diarizedTranscript').textContent = 
                    `Unable to load diarized transcript: ${diarizedTranscript.error || 'Unknown error'}`;
            }
        } catch (error) {
            console.error('Error loading transcripts:', error);
            document.getElementById('pureTranscript').textContent = 
                `Error loading transcript: ${error.message}`;
            document.getElementById('diarizedTranscript').textContent = 
                `Error loading transcript: ${error.message}`;
        }
    } else {
        document.getElementById('pureTranscript').textContent = 
            'PyWebView API not available';
        document.getElementById('diarizedTranscript').textContent = 
            'PyWebView API not available';
    }
}

function displayDiarizedTranscript(segments) {
    const container = document.getElementById('diarizedTranscript');
    container.innerHTML = segments.map(segment => `
        <div class="speaker-segment">
            <div class="timestamp">${segment.start} - ${segment.end}</div>
            <div><strong>Speaker ${segment.speaker}</strong></div>
            <div>${segment.text}</div>
        </div>
    `).join('');
} 