function addVideo() {
    const videoCards = document.getElementById('video-cards');
    const newCard = document.createElement('div');
    newCard.className = 'col-md-4 mb-4';
    newCard.innerHTML = `
        <div class="card">
            <div class="card-body">
                <h5 class="card-title">New Video</h5>
                <p class="card-text">Video details go here.</p>
                <button class="btn btn-primary" onclick="viewEditVideo()">View/Edit</button>
            </div>
        </div>
    `;
    videoCards.insertBefore(newCard, videoCards.lastElementChild);
}

function viewEditVideo() {
    alert('View/Edit functionality to be implemented.');
} 