function viewTranscript(videoName) {
    // Call the Python API through pywebview
    window.pywebview.api.view_transcript(videoName)
        .then(response => {
            if (!response.success) {
                alert(response.error || 'Failed to load transcript');
                return;
            }
            
            const data = response.data;
            
            // Remove any existing modal
            const existingModal = document.querySelector('.modal');
            if (existingModal) {
                existingModal.remove();
            }
            
            const transcriptHtml = `
                <div class="transcript-container">
                    <h3>Transcript for ${data.video_name}</h3>
                    <p><strong>Created:</strong> ${data.timestamp}</p>
                    <p><strong>Status:</strong> ${data.status}</p>
                    <div class="transcript-text">
                        ${data.full_transcript}
                    </div>
                </div>
            `;
            
            // Create and show modal
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <span class="close-button">&times;</span>
                    ${transcriptHtml}
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // Add event listeners
            const closeButton = modal.querySelector('.close-button');
            closeButton.onclick = () => {
                modal.remove();
            };
            
            // Close modal when clicking outside
            modal.onclick = (event) => {
                if (event.target === modal) {
                    modal.remove();
                }
            };
            
            // Show modal
            modal.style.display = 'block';
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error loading transcript');
        });
} 