document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const videoPath = urlParams.get('video');
    const guid = urlParams.get('guid');
    
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
        transcriptContent.innerHTML = '<div class="alert alert-info">Loading diarized transcript...</div>';
        if (window.pywebview && window.pywebview.api) {
            const urlParams = new URLSearchParams(window.location.search);
            const guid = urlParams.get('guid');
            
            window.pywebview.api.get_transcript(guid).then(response => {
                if (response.success && response.data && response.data.diarized_segments) {
                    displayDiarizedTranscript(response.data.diarized_segments);
                } else {
                    transcriptContent.innerHTML = `
                        <div class="alert alert-danger">
                            Error loading diarized transcript: ${response.error || 'No diarization data available'}
                        </div>`;
                }
            }).catch(error => {
                console.error('Error loading diarized transcript:', error);
                transcriptContent.innerHTML = `
                    <div class="alert alert-danger">
                        Error loading diarized transcript: ${error}
                    </div>`;
            });
        }
    }

    function loadFullTranscript() {
        transcriptContent.innerHTML = '<div class="alert alert-info">Loading transcript...</div>';
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.get_transcript(guid).then(response => {
                if (response.success && response.data) {
                    console.log("Transcript loaded:", response.data);
                    displayFullTranscript(response.data);
                } else {
                    console.error("Failed to load transcript:", response.error);
                    transcriptContent.innerHTML = `
                        <div class="alert alert-danger">
                            Error loading transcript: ${response.error || 'Transcript not found'}
                        </div>`;
                }
            });
        }
    }

    function displayDiarizedTranscript(segments) {
        transcriptContent.innerHTML = segments.map(segment => `
            <div class="transcript-segment" data-start="${segment.start}" data-end="${segment.end}">
                <div class="speaker-label">Speaker ${segment.speaker}</div>
                <div class="timestamp">${formatTime(segment.start)} - ${formatTime(segment.end)}</div>
                <div class="text">${segment.text}</div>
            </div>
        `).join('');

        // Add click handlers to jump to video timestamp
        document.querySelectorAll('.transcript-segment').forEach(segment => {
            segment.addEventListener('click', function() {
                const startTime = parseFloat(this.dataset.start);
                videoPlayer.currentTime = startTime;
                videoPlayer.play();
                
                // Highlight current segment
                document.querySelectorAll('.transcript-segment').forEach(s => 
                    s.classList.remove('current-segment'));
                this.classList.add('current-segment');
            });
        });
    }

    function formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
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

    function displayFullTranscript(transcriptData) {
        const container = document.createElement('div');
        container.className = 'transcript-container';

        // Create segments with timestamps
        transcriptData.segments.forEach(segment => {
            const segmentDiv = document.createElement('div');
            segmentDiv.className = 'transcript-segment';
            
            const startTime = segment.timestamp[0];
            const endTime = segment.timestamp[1];
            
            // Add data attributes for time tracking
            segmentDiv.dataset.start = startTime;
            segmentDiv.dataset.end = endTime;
            
            segmentDiv.innerHTML = `
                <div class="segment-timestamp" data-start="${startTime}">
                    ${formatTimestamp(startTime)} - ${formatTimestamp(endTime)}
                </div>
                <div class="segment-text">${segment.text}</div>
            `;

            // Add click handler to jump to timestamp
            segmentDiv.addEventListener('click', () => {
                const videoPlayer = document.getElementById('videoPlayer');
                videoPlayer.currentTime = startTime;
                videoPlayer.play();
            });

            container.appendChild(segmentDiv);
        });

        const transcriptContent = document.getElementById('transcriptContent');
        transcriptContent.innerHTML = '';
        transcriptContent.appendChild(container);

        // Initialize and update charts
        initializeCharts();
        updateCharts(transcriptData);
    }

    function formatTimestamp(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }

    // Add this event listener for the Return button
    document.getElementById('returnButton').addEventListener('click', function() {
        window.history.back(); // Go back to the previous page
    });

    // Modify the timeupdate event listener for continuous scrolling
    videoPlayer.addEventListener('timeupdate', function() {
        const currentTime = this.currentTime;
        const segments = document.querySelectorAll('.transcript-segment');
        const transcriptContent = document.getElementById('transcriptContent');
        let activeSegmentFound = false;
        
        segments.forEach(segment => {
            const start = parseFloat(segment.dataset.start);
            const end = parseFloat(segment.dataset.end);
            
            // Check if current time is within this segment
            if (currentTime >= start && currentTime <= end) {
                activeSegmentFound = true;
                
                // Always update scroll position based on progress within segment
                const segmentDuration = end - start;
                const progress = (currentTime - start) / segmentDuration;
                
                // Get segment dimensions
                const segmentRect = segment.getBoundingClientRect();
                const containerRect = transcriptContent.getBoundingClientRect();
                
                // Calculate the target scroll position
                const segmentTop = segment.offsetTop;
                const containerHeight = transcriptContent.clientHeight;
                
                // Calculate progressive scroll position
                // Start with segment at 33% from top when it begins
                // End with segment at 66% from top when it ends
                const startOffset = containerHeight * 0.33;
                const endOffset = containerHeight * 0.66;
                const scrollOffset = startOffset + (endOffset - startOffset) * progress;
                
                const targetScrollTop = segmentTop - scrollOffset;
                
                // Smooth scroll to position
                transcriptContent.scrollTo({
                    top: targetScrollTop,
                    behavior: 'auto'
                });
                
                // Handle highlighting
                if (!segment.classList.contains('current-segment')) {
                    segments.forEach(s => s.classList.remove('current-segment'));
                    segment.classList.add('current-segment');
                }
            } else if (!activeSegmentFound) {
                segment.classList.remove('current-segment');
            }
        });
    });

    // Additional code to load the video can go here
});

function initializeCharts() {
    // Add this common configuration object for click interactions
    const clickInteractionConfig = {
        onClick: (event, elements) => {
            if (elements && elements.length > 0) {
                const index = elements[0].index;
                const timestamps = event.chart.data.labels;
                const timeString = timestamps[index];
                const seconds = timeStringToSeconds(timeString);
                
                // Set video to that timestamp
                const videoPlayer = document.getElementById('videoPlayer');
                videoPlayer.currentTime = seconds;
                videoPlayer.play();
                
                // Highlight corresponding transcript segment
                highlightTranscriptSegment(seconds);
            }
        }
    };

    // Initialize speaking time chart
    const speakingTimeCtx = document.getElementById('speakingTimeChart').getContext('2d');
    window.speakingTimeChart = new Chart(speakingTimeCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Speaking Time (seconds)',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Speaking Time Distribution'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Duration (seconds)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Timeline'
                    }
                }
            },
            ...clickInteractionConfig,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            onHover: (event, elements) => {
                event.native.target.style.cursor = elements.length ? 'pointer' : 'default';
            }
        }
    });

    // Initialize word frequency chart
    const wordFrequencyCtx = document.getElementById('wordFrequencyChart').getContext('2d');
    window.wordFrequencyChart = new Chart(wordFrequencyCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Word Frequency',
                data: [],
                borderColor: 'rgb(153, 102, 255)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Word Frequency Over Time'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Word Count'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Timeline'
                    }
                }
            },
            ...clickInteractionConfig,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            onHover: (event, elements) => {
                event.native.target.style.cursor = elements.length ? 'pointer' : 'default';
            }
        }
    });

    // Initialize heart rate chart
    const heartRateCtx = document.getElementById('heartRateChart').getContext('2d');
    window.heartRateChart = new Chart(heartRateCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Heart Rate (BPM)',
                data: [],
                borderColor: 'rgb(255, 99, 132)',
                tension: 0.1,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Heart Rate Over Time'
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: 'BPM'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Timeline'
                    }
                }
            },
            ...clickInteractionConfig,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            onHover: (event, elements) => {
                event.native.target.style.cursor = elements.length ? 'pointer' : 'default';
            }
        }
    });

    // Initialize emotions chart
    const emotionsCtx = document.getElementById('emotionsChart').getContext('2d');
    window.emotionsChart = new Chart(emotionsCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Happy',
                    data: [],
                    borderColor: 'rgb(255, 206, 86)',
                    tension: 0.1,
                    fill: false
                },
                {
                    label: 'Sad',
                    data: [],
                    borderColor: 'rgb(54, 162, 235)',
                    tension: 0.1,
                    fill: false
                },
                {
                    label: 'Angry',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    tension: 0.1,
                    fill: false
                },
                {
                    label: 'Neutral',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Emotion Detection Over Time'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 1,
                    title: {
                        display: true,
                        text: 'Confidence Score'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Timeline'
                    }
                }
            },
            ...clickInteractionConfig,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            onHover: (event, elements) => {
                event.native.target.style.cursor = elements.length ? 'pointer' : 'default';
            }
        }
    });

    // Initialize emotions pie chart
    const emotionsPieCtx = document.getElementById('emotionsPieChart').getContext('2d');
    window.emotionsPieChart = new Chart(emotionsPieCtx, {
        type: 'pie',
        data: {
            labels: ['Happy', 'Sad', 'Angry', 'Neutral'],
            datasets: [{
                data: [0, 0, 0, 0],
                backgroundColor: [
                    'rgb(255, 206, 86)',   // Happy - yellow
                    'rgb(54, 162, 235)',    // Sad - blue
                    'rgb(255, 99, 132)',    // Angry - red
                    'rgb(75, 192, 192)'     // Neutral - green
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Overall Emotion Distribution'
                },
                legend: {
                    position: 'right'
                }
            }
        }
    });
}

function updateCharts(transcriptData) {
    if (!transcriptData || !transcriptData.segments) return;

    // Store the original timestamps for click handling
    window.timestampData = transcriptData.segments.map(segment => ({
        start: segment.timestamp[0],
        end: segment.timestamp[1]
    }));

    // Process data for speaking time chart
    const timeData = transcriptData.segments.map(segment => {
        const duration = segment.timestamp[1] - segment.timestamp[0];
        return {
            time: formatTimestamp(segment.timestamp[0]),
            duration: duration
        };
    });

    // Process data for word frequency chart
    const wordData = transcriptData.segments.map(segment => {
        return {
            time: formatTimestamp(segment.timestamp[0]),
            wordCount: segment.text.split(/\s+/).length
        };
    });

    // Update speaking time chart
    window.speakingTimeChart.data.labels = timeData.map(d => d.time);
    window.speakingTimeChart.data.datasets[0].data = timeData.map(d => d.duration);
    window.speakingTimeChart.update();

    // Update word frequency chart
    window.wordFrequencyChart.data.labels = wordData.map(d => d.time);
    window.wordFrequencyChart.data.datasets[0].data = wordData.map(d => d.wordCount);
    window.wordFrequencyChart.update();

    // Update heart rate chart (assuming heart rate data is available in transcriptData)
    if (transcriptData.heartRate) {
        window.heartRateChart.data.labels = transcriptData.heartRate.map(d => formatTimestamp(d.timestamp));
        window.heartRateChart.data.datasets[0].data = transcriptData.heartRate.map(d => d.bpm);
        window.heartRateChart.update();
    }

    // Update emotions chart (assuming emotion data is available in transcriptData)
    if (transcriptData.emotions) {
        const emotions = ['Happy', 'Sad', 'Angry', 'Neutral'];
        const timestamps = transcriptData.emotions.map(d => formatTimestamp(d.timestamp));
        
        window.emotionsChart.data.labels = timestamps;
        
        emotions.forEach((emotion, index) => {
            window.emotionsChart.data.datasets[index].data = 
                transcriptData.emotions.map(d => d[emotion.toLowerCase()]);
        });
        
        window.emotionsChart.update();
    }

    // Update emotions pie chart
    if (transcriptData.emotions) {
        const emotions = ['Happy', 'Sad', 'Angry', 'Neutral'];
        
        // Calculate average emotion values
        const emotionSums = emotions.reduce((sums, emotion) => {
            const values = transcriptData.emotions.map(d => d[emotion.toLowerCase()]);
            sums[emotion] = values.reduce((a, b) => a + b, 0) / values.length;
            return sums;
        }, {});

        // Update pie chart
        window.emotionsPieChart.data.datasets[0].data = emotions.map(emotion => 
            (emotionSums[emotion] * 100).toFixed(1)
        );
        window.emotionsPieChart.update();

        // Add percentages to labels
        window.emotionsPieChart.data.labels = emotions.map(emotion => 
            `${emotion} (${(emotionSums[emotion] * 100).toFixed(1)}%)`
        );
    }
}

// Add helper function to calculate emotion percentages
function calculateEmotionPercentages(emotionsData) {
    const totalSamples = emotionsData.length;
    const emotionSums = emotionsData.reduce((sums, sample) => {
        Object.keys(sample).forEach(emotion => {
            if (emotion !== 'timestamp') {
                sums[emotion] = (sums[emotion] || 0) + sample[emotion];
            }
        });
        return sums;
    }, {});

    // Convert sums to percentages
    Object.keys(emotionSums).forEach(emotion => {
        emotionSums[emotion] = (emotionSums[emotion] / totalSamples) * 100;
    });

    return emotionSums;
}

// Add these new helper functions
function timeStringToSeconds(timeString) {
    const [minutes, seconds] = timeString.split(':').map(Number);
    return minutes * 60 + seconds;
}

function highlightTranscriptSegment(targetTime) {
    const segments = document.querySelectorAll('.transcript-segment');
    segments.forEach(segment => {
        const start = parseFloat(segment.dataset.start);
        const end = parseFloat(segment.dataset.end);
        
        if (targetTime >= start && targetTime <= end) {
            // Remove highlight from all segments
            segments.forEach(s => s.classList.remove('current-segment'));
            
            // Add highlight to current segment
            segment.classList.add('current-segment');
            
            // Scroll segment into view
            segment.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    });
}

// Add this CSS class if not already present
function addStyleToDocument() {
    const style = document.createElement('style');
    style.textContent = `
        .chart-container {
            cursor: pointer;
        }
        .chart-container:hover {
            background-color: rgba(0,0,0,0.02);
        }
    `;
    document.head.appendChild(style);
}

// Call this when the document loads
document.addEventListener('DOMContentLoaded', function() {
    addStyleToDocument();
    // ... rest of your initialization code ...
});

// Add this after your existing code
document.getElementById('heartRateFile').addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        const text = e.target.result;
        const data = parseHeartRateData(text);
        if (data) {
            updateHeartRateChart(data);
            displayHeartRateTable(data);
        }
    };
    reader.readAsText(file);
});

function parseHeartRateData(csvText) {
    try {
        const rows = csvText.split('\n');
        const data = rows
            .map(row => {
                const [timeStr, bpmStr] = row.split(',').map(s => s.trim());
                if (!timeStr || !bpmStr) return null;
                
                // Parse time (expecting format like "MM:SS" or "HH:MM:SS")
                const timeComponents = timeStr.split(':').map(Number);
                let seconds = 0;
                if (timeComponents.length === 2) {
                    seconds = timeComponents[0] * 60 + timeComponents[1];
                } else if (timeComponents.length === 3) {
                    seconds = timeComponents[0] * 3600 + timeComponents[1] * 60 + timeComponents[2];
                }

                const bpm = parseFloat(bpmStr);
                if (isNaN(seconds) || isNaN(bpm)) return null;

                return { timestamp: seconds, bpm: bpm };
            })
            .filter(item => item !== null);

        return data;
    } catch (error) {
        console.error('Error parsing heart rate data:', error);
        alert('Error parsing file. Please ensure it\'s in the correct format (Time,BPM)');
        return null;
    }
}

function updateHeartRateChart(data) {
    // Sort data by timestamp
    data.sort((a, b) => a.timestamp - b.timestamp);

    // Update the heart rate chart
    window.heartRateChart.data.labels = data.map(d => formatTimestamp(d.timestamp));
    window.heartRateChart.data.datasets[0].data = data.map(d => d.bpm);
    window.heartRateChart.update();

    // Store the data for later use
    window.heartRateData = data;
}

function displayHeartRateTable(data) {
    const tableBody = document.getElementById('heartRateTableBody');
    tableBody.innerHTML = data
        .map(row => `
            <tr>
                <td>${formatTimestamp(row.timestamp)}</td>
                <td>${row.bpm}</td>
            </tr>
        `)
        .join('');
}

// Update the existing updateCharts function to use the loaded heart rate data
const originalUpdateCharts = updateCharts;
updateCharts = function(transcriptData) {
    originalUpdateCharts(transcriptData);
    
    // If we have heart rate data loaded from file, use that instead
    if (window.heartRateData) {
        window.heartRateChart.data.labels = window.heartRateData.map(d => formatTimestamp(d.timestamp));
        window.heartRateChart.data.datasets[0].data = window.heartRateData.map(d => d.bpm);
        window.heartRateChart.update();
    }
}; 