document.addEventListener('DOMContentLoaded', async function() {
    // Get URL parameters including guid
    const urlParams = new URLSearchParams(window.location.search);
    const videoPath = urlParams.get('video');
    const guid = urlParams.get('guid');
    
    // Store guid in window object so it's accessible everywhere
    window.currentGuid = guid;
    
    // Set up video player
    const videoPlayer = document.getElementById('videoPlayer');
    if (videoPath) {
        videoPlayer.src = videoPath;
    }

    // Initialize all components after pywebview is ready
    async function initializeComponents() {
        if (window.pywebview && window.pywebview.api) {
            if (guid) {
                // Initialize HR data handling
                await initializeHRDataHandling(guid);
                
                // Initialize transcript
                switchTranscriptView('full');
                
                // Initialize other components...
            } else {
                console.error('No GUID provided in URL parameters');
                showMessage('Error: No video ID found', 'error');
            }
        } else {
            // If pywebview isn't ready yet, try again in 100ms
            setTimeout(initializeComponents, 100);
        }
    }

    // Start initialization
    initializeComponents();

    // Handle transcript view switching
    const analyticsTab = document.querySelector('a[href="#analytics"]'); // Select the Analytics tab

    analyticsTab.addEventListener('click', function() {
        // Charts will be created only if data exists in window.heartRateData
        if (window.heartRateData) {
            createHeartRateCharts(window.heartRateData);
        }
    });

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

    // Add event listener for the Create New Chart button
    const createChartButton = document.getElementById('createChartButton');
    createChartButton.addEventListener('click', function() {
        // Assuming you have the parsed data stored in a variable
        if (window.heartRateData) { // Check if heart rate data is available
            try {
                createHeartRateChart(window.heartRateData); // Pass the real data to create the chart
            } catch (error) {
                console.error("Error creating chart:", error);
            }
        } else {
            console.error("No heart rate data available to create chart.");
        }
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

// Remove the event listener that automatically processes the file on selection
// Let the form submission handle the file upload instead
document.getElementById('hrDataFile').removeEventListener('change', function(e) {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        const csvData = e.target.result;
        const parsedData = parseHeartRateData(csvData); // Parse the CSV data
        console.log(parsedData);
        if (parsedData) { // Check if parsed data is valid
            uploadHRData(parsedData, window.currentGuid);
        } else {
            showMessage('Error parsing heart rate data. Please ensure the file is in the correct format.', 'error');
        }
    };
    reader.readAsText(file);
});

function parseHeartRateData(csvText) {
    try {
        const rows = csvText.split('\n');
        const data = rows
            .map(row => {
                const values = row.split(',').map(s => s.trim());
                if (values.length < 3) return null;

                const timeStr = values[0];
                const parentBpm = parseFloat(values[1]);
                const childBpm = parseFloat(values[2]);

                // Parse time (expecting format like "MM:SS" or "HH:MM:SS")
                const timeComponents = timeStr.split(':').map(Number);
                let seconds = 0;
                if (timeComponents.length === 2) {
                    seconds = timeComponents[0] * 60 + timeComponents[1];
                } else if (timeComponents.length === 3) {
                    seconds = timeComponents[0] * 3600 + timeComponents[1] * 60 + timeComponents[2];
                }

                if (isNaN(seconds) || isNaN(parentBpm) || isNaN(childBpm)) return null;

                return {
                    timestamp: seconds,
                    parent: parentBpm,
                    child: childBpm
                };
            })
            .filter(item => item !== null);

        return data;
    } catch (error) {
        console.error('Error parsing heart rate data:', error);
        alert('Error parsing file. Please ensure it\'s in the correct format (Time,Parent BPM,Child BPM)');
        return null;
    }
}

function updateHeartRateTable(data) {
    const tableBody = document.getElementById('heartRateTableBody');
    if (!tableBody) return;
    
    tableBody.innerHTML = data
        .map((row, index) => `
            <tr>
                <td>${index + 1}</td>
                <td>${row.child || 'N/A'}</td>
                <td>${row.parent || 'N/A'}</td>
            </tr>
        `)
        .join('');
}

// Global chart variable
let heartRateChart = null;

function createHeartRateCharts(data) {
    console.log("Creating heart rate chart with data:", data);
    
    // Verify data structure
    if (!data || !Array.isArray(data) || data.length === 0) {
        console.error("Invalid or empty heart rate data");
        return;
    }
    
    // Clear any existing chart
    if (heartRateChart) {
        heartRateChart.destroy();
    }
    
    // Get the canvas element - we'll use the parent one for the combined chart
    const canvas = document.getElementById('parentHeartRateChart');
    
    if (!canvas) {
        console.error("Canvas element not found");
        return;
    }
    
    const ctx = canvas.getContext('2d');
    
    // First, add timestamps if they don't exist
    if (!data[0].hasOwnProperty('timestamp')) {
        data = data.map((row, index) => ({
            ...row,
            timestamp: index // Use index as timestamp if not present
        }));
    }
    
    const labels = data.map(row => row.timestamp);
    const parentHR = data.map(row => row.parent);
    const childHR = data.map(row => row.child);
    
    // Calculate min and max for dynamic y-axis scaling
    const allValues = [...parentHR, ...childHR].filter(val => val !== undefined && val !== null);
    const min = Math.min(...allValues);
    const max = Math.max(...allValues);
    
    // Set scale to be min-10 to max+10, with a minimum range of 40
    const yMin = Math.max(40, min - 10);
    const yMax = Math.max(yMin + 40, max + 10);
    
    console.log("Heart Rate Range:", { min, max, yMin, yMax });
    
    // Create combined heart rate chart
    heartRateChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Parent Heart Rate',
                    data: parentHR,
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.1)',
                    fill: true,
                    tension: 0.3
                },
                {
                    label: 'Child Heart Rate',
                    data: childHR,
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    fill: true,
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Time (seconds)'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Heart Rate (BPM)'
                    },
                    min: yMin,
                    max: yMax
                }
            },
            onClick: function(event, elements, chart) {
                // Get the x-axis value (time) where the user clicked
                const canvasPosition = Chart.helpers.getRelativePosition(event, chart);
                const timeValue = chart.scales.x.getValueForPixel(canvasPosition.x);
                
                // Find the closest timestamp in our data
                const closestTimeIndex = labels.reduce((prev, curr, index) => {
                    return (Math.abs(curr - timeValue) < Math.abs(labels[prev] - timeValue)) 
                        ? index 
                        : prev;
                }, 0);
                
                const timeInSeconds = labels[closestTimeIndex];
                
                // Seek the video to this time
                const videoPlayer = document.getElementById('videoPlayer');
                if (videoPlayer) {
                    videoPlayer.currentTime = timeInSeconds;
                    videoPlayer.play();
                }
            }
        }
    });
    
    // Hide the second chart container since we're only using one
    const childChartContainer = document.getElementById('childHeartRateChart').parentNode;
    if (childChartContainer) {
        childChartContainer.style.display = 'none';
    }
    
    console.log("Heart rate chart created successfully");
}

// Initialize HR data handling
async function initializeHRDataHandling(guid) {
    const hrDataUploadForm = document.getElementById('hrDataUploadForm');
    const hrDataStatus = document.getElementById('hrDataStatus');
    const deleteHRDataBtn = document.getElementById('deleteHRData');
    
    if (!guid) {
        hrDataStatus.innerHTML = `
            <div class="alert alert-danger">
                Error: No video ID found. Please return to the main page and try again.
            </div>
        `;
        return;
    }
    
    // Try to load existing HR data when page loads with correct GUID
    try {
        const response = await window.pywebview.api.get_hr_data(guid);
        if (response.success) {
            updateHRDisplay(response.data);
            // Only create charts when data is loaded
            createHeartRateCharts(response.data);
            if (deleteHRDataBtn) {
                deleteHRDataBtn.disabled = false;
            }
        } else {
            console.log('No HR data available');
            showHRUploadForm();
        }
    } catch (error) {
        console.error('Error loading HR data:', error);
        showHRUploadForm();
    }
    
    // Modified file upload handler - only create charts after successful upload
    hrDataUploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const fileInput = document.getElementById('hrDataFile');
        const file = fileInput.files[0];
        
        if (!file) {
            showMessage('Please select a CSV file', 'error');
            return;
        }
        
        if (!file.name.toLowerCase().endsWith('.csv')) {
            showMessage('Please upload a CSV file', 'error');
            return;
        }
        
        try {
            const reader = new FileReader();
            reader.onload = async function(e) {
                const csvData = e.target.result;
                const lines = csvData.split('\n');
                
                if (lines.length < 2) {
                    showMessage('CSV file must contain data rows', 'error');
                    return;
                }

                // Get column configuration
                const firstColType = document.getElementById('firstColumnType').value;
                const secondColType = document.getElementById('secondColumnType').value;

                // Create header line based on column configuration
                const headerLine = `${firstColType},${secondColType}\n`;
                
                // Process the data lines (skip header if it exists)
                const dataLines = lines.filter(line => line.trim().length > 0);
                const processedData = dataLines.slice(1).join('\n');
                
                // Combine header and processed data
                const finalCsvData = headerLine + processedData;

                // Send to backend
                const response = await window.pywebview.api.upload_hr_data(finalCsvData, guid);
                if (response.success) {
                    showMessage('HR data uploaded successfully', 'success');
                    
                    // Process the data for display
                    const displayData = dataLines.slice(1).map(line => {
                        const [col1, col2] = line.split(',').map(val => parseFloat(val.trim()));
                        return {
                            [firstColType]: col1,
                            [secondColType]: col2
                        };
                    });

                    updateHRDisplay(displayData);
                    // Only create charts after successful upload
                    createHeartRateCharts(displayData);
                } else {
                    showMessage(`Upload failed: ${response.error}`, 'error');
                }
            };
            reader.readAsText(file);
        } catch (error) {
            showMessage(`Upload error: ${error.message}`, 'error');
        }
    });
    
    // Rest of your existing code...
}

function updateHRDisplay(data) {
    const tableBody = document.getElementById('heartRateTableBody');
    const deleteHRDataBtn = document.getElementById('deleteHRData');
    
    if (!tableBody) return;
    
    // Enable delete button when data is present
    if (deleteHRDataBtn) {
        deleteHRDataBtn.disabled = false;
    }
    
    // Correctly display the data in the table
    tableBody.innerHTML = data.map((row, index) => `
        <tr>
            <td>${index + 1}</td>
            <td>${row.child !== undefined ? row.child : 'N/A'}</td>
            <td>${row.parent !== undefined ? row.parent : 'N/A'}</td>
        </tr>
    `).join('');
}

function updateHRChart(data) {
    if (window.heartRateChart) {
        window.heartRateChart.data.datasets = [{
            label: 'Parent HR',
            data: data.map(row => row.parent),
            borderColor: 'rgb(255, 99, 132)',
            fill: false,
            tension: 0.1
        }, {
            label: 'Child HR',
            data: data.map(row => row.child),
            borderColor: 'rgb(75, 192, 192)',
            fill: false,
            tension: 0.1
        }];
        window.heartRateChart.update();
    }
}

function showHRUploadForm() {
    const hrDataStatus = document.getElementById('hrDataStatus');
    const deleteHRDataBtn = document.getElementById('deleteHRData');
    
    if (hrDataStatus) {
        hrDataStatus.innerHTML = `
            <div class="alert alert-info">
                No HR data available. Please upload a CSV file with child and parent heart rate data.
            </div>
        `;
    }
    
    // Disable delete button when no data is present
    if (deleteHRDataBtn) {
        deleteHRDataBtn.disabled = true;
    }
}

// Add a showMessage function if you don't have one
function showMessage(message, type = 'info') {
    const hrDataStatus = document.getElementById('hrDataStatus');
    if (hrDataStatus) {
        hrDataStatus.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
    }
}

// Add function to clear HR display
function clearHRDisplay() {
    // Clear table
    const tableBody = document.getElementById('heartRateTableBody');
    if (tableBody) {
        tableBody.innerHTML = '';
    }
    
    // Clear chart
    if (window.heartRateChart) {
        window.heartRateChart.data.datasets = [{
            label: 'Parent HR',
            data: [],
            borderColor: 'rgb(255, 99, 132)',
            tension: 0.1
        }, {
            label: 'Child HR',
            data: [],
            borderColor: 'rgb(75, 192, 192)',
            tension: 0.1
        }];
        window.heartRateChart.update();
    }
}

// Global error handler
window.onerror = function(message, source, lineno, colno, error) {
    const errorMessage = `Error: ${message} at ${source}:${lineno}:${colno}`;
    console.error(errorMessage); // Log to console

    // Send error to Python backend
    if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.log_js_error(errorMessage).catch(err => {
            console.error("Failed to log error to backend:", err);
        });
    }
};

// Add interactivity to the heart rate chart
const heartRateChartCanvas = document.getElementById('heartRateChart');
heartRateChartCanvas.onclick = function(event) {
    if (window.heartRateChart) { // Check if the chart instance exists
        const activePoints = window.heartRateChart.getElementsAtEventForMode(event, 'nearest', { intersect: true }, false);
        if (activePoints.length) {
            const index = activePoints[0].index;
            const timeInSeconds = window.heartRateChart.data.labels[index]; // Use the label for time
            const videoPlayer = document.getElementById('videoPlayer');
            videoPlayer.currentTime = timeInSeconds; // Seek to the corresponding time in the video
            videoPlayer.play(); // Optionally play the video
        }
    } else {
        console.error("Heart rate chart instance is not available.");
    }
};

function chartClickHandler(event) {
    const chart = this.id === 'parentHeartRateChart' ? parentHeartRateChart : childHeartRateChart;
    if (chart) {
        const activePoints = chart.getElementsAtEventForMode(event, 'nearest', { intersect: true }, false);
        if (activePoints.length) {
            const index = activePoints[0].index;
            const timeInSeconds = chart.data.labels[index]; // Use the timestamp as the time
            const videoPlayer = document.getElementById('videoPlayer');
            if (videoPlayer) {
                videoPlayer.currentTime = timeInSeconds;
                videoPlayer.play();
            }
        }
    }
} 