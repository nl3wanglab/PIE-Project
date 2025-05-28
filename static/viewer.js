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
                await switchTranscriptView('full');
                
                // Initialize diarization if selected
                const diarizedBtn = document.getElementById('diarizedBtn');
                if (diarizedBtn && diarizedBtn.classList.contains('active')) {
                    await initializeDiarization();
                }
                
                // Initialize scoring after transcript/diarization
                await initializeScoring();
                
                // Initialize notes
                await initializeNotes();
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

    // Event listener for the new Load/Process Analytics Button
    const loadAnalyticsBtn = document.getElementById('loadProcessAnalyticsButton');
    if (loadAnalyticsBtn) {
        loadAnalyticsBtn.addEventListener('click', async () => {
            if (!window.currentGuid) {
                showMessage('No video ID found. Please ensure a video is loaded.', 'error');
                return;
            }
            try {
                showMessage('Processing full analytics... This may take a moment.', 'info');
                loadAnalyticsBtn.disabled = true;
                loadAnalyticsBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
                
                const response = await window.pywebview.api.calculate_scores(window.currentGuid);
                
                if (response && response.success && response.data) {
                    // Update UI with all new scores and metrics
                    if (response.data.scores) {
                        updateMainScoresUI(response.data.scores); // Assumes/Creates a function to update main score sliders
                    }
                    if (response.data.detailed_metrics) {
                        updateDetailedMetrics(response.data.detailed_metrics);
                    }
                    showMessage('Analytics processed and updated successfully.', 'success');
                } else {
                    showMessage(`Error processing analytics: ${response.error || 'Unknown error'}`, 'error');
                }
            } catch (e) {
                console.error("Error calling calculate_scores:", e);
                showMessage(`Failed to process analytics: ${e.toString()}`, 'error');
            } finally {
                loadAnalyticsBtn.disabled = false;
                loadAnalyticsBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Load/Process Full Analytics';
            }
        });
    }

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
        const diarizedBtn = document.getElementById('diarizedBtn');
        const fullBtn = document.getElementById('fullBtn');
        const speakerControls = document.querySelector('.speaker-controls');
        const saveChangesBtn = document.getElementById('saveChangesBtn');
        
        if (type === 'diarized') {
            diarizedBtn.classList.add('active');
            fullBtn.classList.remove('active');
            speakerControls.style.display = 'flex';
            loadDiarizedTranscript();
            // Reset edit state when switching to diarized view
            saveChangesBtn.innerHTML = '<i class="bi bi-pencil"></i> Edit';
            saveChangesBtn.disabled = false;
        } else {
            fullBtn.classList.add('active');
            diarizedBtn.classList.remove('active');
            speakerControls.style.display = 'none';
            loadFullTranscript();
        }
    }

    async function loadDiarizedTranscript() {
        const transcriptContent = document.getElementById('transcriptContent');
        transcriptContent.innerHTML = '<div class="alert alert-info">Loading diarized transcript...</div>';
        
        try {
            // First try to get the main transcript with diarized segments
            const response = await window.pywebview.api.get_transcript(window.currentGuid);
            if (response.success && response.data && response.data.diarized_segments) {
                // Load any manual speaker assignments
                const diarizationResponse = await window.pywebview.api.get_diarized_transcript(window.currentGuid);
                if (diarizationResponse.success && diarizationResponse.data && diarizationResponse.data.segments) {
                    // Merge manual assignments with original segments
                    const manualAssignments = diarizationResponse.data.segments;
                    const segments = response.data.diarized_segments.map(segment => {
                        // Find matching manual assignment
                        const manual = manualAssignments.find(m => 
                            Math.abs(m.start - segment.start) < 0.1 && 
                            Math.abs(m.end - segment.end) < 0.1
                        );
                        if (manual) {
                            return { ...segment, speaker: manual.speaker };
                        }
                        return segment;
                    });
                    displayDiarizedTranscript(segments);
                } else {
                    displayDiarizedTranscript(response.data.diarized_segments);
                }
            } else {
                transcriptContent.innerHTML = `
                    <div class="alert alert-danger">
                        Error loading diarized transcript: ${response.error || 'No diarization data available'}
                    </div>`;
            }
        } catch (error) {
            console.error('Error loading diarized transcript:', error);
            transcriptContent.innerHTML = `
                <div class="alert alert-danger">
                    Error loading diarized transcript: ${error}
                </div>`;
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
        const transcriptContent = document.getElementById('transcriptContent');
        if (!segments || !segments.length) {
            transcriptContent.innerHTML = `
                <div class="alert alert-info">
                    No diarized segments available.
                </div>
            `;
            return;
        }
        
        transcriptContent.innerHTML = segments.map(segment => `
            <div class="transcript-segment speaker-${segment.speaker}" 
                 data-start="${segment.start}" 
                 data-end="${segment.end}">
                <div class="speaker-label">Speaker ${segment.speaker}</div>
                <div class="timestamp">${formatTime(segment.start)} - ${formatTime(segment.end)}</div>
                <div class="text">${segment.text}</div>
            </div>
        `).join('');

        // Add click handlers to segments - only seek, don't play
        document.querySelectorAll('.transcript-segment').forEach(segment => {
            segment.addEventListener('click', function() {
                const startTime = parseFloat(this.dataset.start);
                const videoPlayer = document.getElementById('videoPlayer');
                if (videoPlayer) {
                    videoPlayer.currentTime = startTime;
                }
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
        if (!transcriptData || !transcriptData.segments) {
            console.error("Invalid transcript data");
            return;
        }
        
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

            // Add click handler to jump to timestamp without playing
            segmentDiv.addEventListener('click', () => {
                const videoPlayer = document.getElementById('videoPlayer');
                if (videoPlayer) {
                    videoPlayer.currentTime = startTime;
                }
            });

            container.appendChild(segmentDiv);
        });

        const transcriptContent = document.getElementById('transcriptContent');
        if (transcriptContent) {
            transcriptContent.innerHTML = '';
            transcriptContent.appendChild(container);
        }
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
                
                // Only update scroll position if this is a new active segment
                if (!segment.classList.contains('current-segment')) {
                    // Remove highlight from all segments
                    segments.forEach(s => s.classList.remove('current-segment'));
                    segment.classList.add('current-segment');
                    
                    // Calculate the target scroll position
                    const segmentTop = segment.offsetTop;
                    const containerHeight = transcriptContent.clientHeight;
                    const targetScrollTop = segmentTop - (containerHeight / 2);
                    
                    // Smooth scroll to position
                    transcriptContent.scrollTo({
                        top: targetScrollTop,
                        behavior: 'smooth'
                    });
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
    
    // Create a vertical line annotation plugin
    const verticalLinePlugin = {
        id: 'verticalLine',
        beforeDraw: (chart) => {
            if (chart.tooltip?._active?.length && chart.config._config.type === 'line') {
                // Only show on hover
                return;
            }
            
            // Get current video time for positioning the line
            const videoPlayer = document.getElementById('videoPlayer');
            if (!videoPlayer) return;
            
            const currentTime = videoPlayer.currentTime;
            
            // Find the closest x value to the current time
            const xAxis = chart.scales.x;
            const yAxis = chart.scales.y;
            
            // Skip if outside the chart range
            if (currentTime < xAxis.min || currentTime > xAxis.max) return;
            
            const xPixel = xAxis.getPixelForValue(currentTime);
            
            // Get canvas context and draw vertical line
            const ctx = chart.ctx;
            
            // Draw vertical line
            ctx.save();
            ctx.beginPath();
            ctx.moveTo(xPixel, yAxis.top);
            ctx.lineTo(xPixel, yAxis.bottom);
            ctx.lineWidth = 2;
            ctx.strokeStyle = '#FF0000';
            ctx.stroke();
            
            // Draw circle at the intersection with each dataset
            ctx.lineWidth = 2;
            
            chart.data.datasets.forEach((dataset, i) => {
                // Find the nearest data point
                const meta = chart.getDatasetMeta(i);
                if (meta.hidden) return;
                
                // Get closest point index
                const pointIndex = labels.reduce((prev, curr, idx) => {
                    return Math.abs(curr - currentTime) < Math.abs(labels[prev] - currentTime) ? idx : prev;
                }, 0);
                
                // Draw marker at this point's y-position
                if (pointIndex >= 0 && dataset.data[pointIndex] !== undefined) {
                    const yValue = dataset.data[pointIndex];
                    const yPixel = yAxis.getPixelForValue(yValue);
                    
                    ctx.beginPath();
                    ctx.arc(xPixel, yPixel, 5, 0, 2 * Math.PI);
                    ctx.fillStyle = dataset.borderColor;
                    ctx.fill();
                    ctx.strokeStyle = 'white';
                    ctx.stroke();
                }
            });
            
            ctx.restore();
        }
    };
    
    // Create combined heart rate chart with the plugin
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
                
                // Seek the video to this time but don't play
                const videoPlayer = document.getElementById('videoPlayer');
                if (videoPlayer) {
                    videoPlayer.currentTime = timeInSeconds;
                }
            }
        },
        plugins: [verticalLinePlugin]
    });
    
    // Hide the second chart container since we're only using one
    const childChartContainer = document.getElementById('childHeartRateChart').parentNode;
    if (childChartContainer) {
        childChartContainer.style.display = 'none';
    }
    
    console.log("Heart rate chart created successfully");
    
    // Set up video timeupdate event to update the chart
    const videoPlayer = document.getElementById('videoPlayer');
    if (videoPlayer) {
        videoPlayer.addEventListener('timeupdate', function() {
            // Request animation frame to update the chart
            if (heartRateChart) {
                heartRateChart.update();
            }
        });
    }
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

// Enhanced transcript scrolling functionality
document.addEventListener('DOMContentLoaded', function() {
    const videoPlayer = document.getElementById('videoPlayer');
    
    if (videoPlayer) {
        // Remove any existing timeupdate listeners to prevent duplicates
        videoPlayer.removeEventListener('timeupdate', updateOnTimeChange);
        
        // Add the event listener for time updates
        videoPlayer.addEventListener('timeupdate', updateOnTimeChange);
        
        // Initialize transcript view
        const fullBtn = document.getElementById('fullBtn');
        if (fullBtn && fullBtn.classList.contains('active')) {
            loadFullTranscript();
        } else {
            const diarizedBtn = document.getElementById('diarizedBtn');
            if (diarizedBtn && diarizedBtn.classList.contains('active')) {
                loadDiarizedTranscript();
            }
        }
    }
    
    // Ensure transcript container has proper styling
    const transcriptContent = document.getElementById('transcriptContent');
    if (transcriptContent) {
        transcriptContent.style.overflowY = 'auto';
        transcriptContent.style.maxHeight = '500px'; // Set appropriate height
        transcriptContent.style.scrollBehavior = 'smooth';
    }
});

// Throttle function to limit how often a function can run
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Keep track of scrolling status to prevent overlapping scroll operations
let isScrolling = false;
let lastActiveSegmentId = null;

// Function that updates both chart and transcript on video time change
function updateOnTimeChange() {
    const currentTime = this.currentTime;
    
    // Update transcript highlighting and scrolling (throttled)
    updateTranscriptHighlightingThrottled(currentTime);
    
    // Update chart if it exists
    if (heartRateChart) {
        heartRateChart.update();
    }
}

// Create a throttled version of the updateTranscriptHighlighting function
const updateTranscriptHighlightingThrottled = throttle(updateTranscriptHighlighting, 200);

// Improved transcript highlighting and scrolling function
function updateTranscriptHighlighting(currentTime) {
    const segments = document.querySelectorAll('.transcript-segment');
    const transcriptContent = document.getElementById('transcriptContent');
    
    if (!segments.length || !transcriptContent) {
        return;
    }
    
    let activeSegment = null;
    
    // Find the active segment
    segments.forEach(segment => {
        const start = parseFloat(segment.dataset.start || 0);
        const end = parseFloat(segment.dataset.end || 0);
        
        // Remove current highlight from all segments
        segment.classList.remove('current-segment');
        
        // Add highlight to current segment
        if (currentTime >= start && currentTime <= end) {
            segment.classList.add('current-segment');
            activeSegment = segment;
        }
    });
    
    // Only scroll when we move to a new segment and we're not already scrolling
    if (activeSegment && !isScrolling) {
        const currentSegmentId = activeSegment.dataset.start + '-' + activeSegment.dataset.end;
        
        // Only scroll when we have a new active segment
        if (currentSegmentId !== lastActiveSegmentId) {
            // Record this segment as the last one we scrolled to
            lastActiveSegmentId = currentSegmentId;
            
            // Calculate optimal scroll position
            const containerRect = transcriptContent.getBoundingClientRect();
            const segmentRect = activeSegment.getBoundingClientRect();
            
            // Get the top of the segment relative to the container
            const segmentTop = segmentRect.top - containerRect.top;
            
            // Calculate ideal position to center the segment
            const containerHeight = containerRect.height;
            const segmentHeight = segmentRect.height;
            
            // Target position centers the segment in the visible area
            const targetPosition = transcriptContent.scrollTop + segmentTop - (containerHeight/2) + (segmentHeight/2);
            
            // Set scrolling flag to prevent overlapping scroll operations
            isScrolling = true;
            
            // Use smooth scrolling with promises to track completion
            transcriptContent.scrollTo({
                top: targetPosition,
                behavior: 'smooth'
            });
            
            // Reset the scrolling flag after animation completes (approximately 300ms for most browsers)
            setTimeout(() => {
                isScrolling = false;
            }, 500);
        }
    }
}

// Only update style tags once when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check if we've already added this style
    if (!document.getElementById('transcript-smooth-scroll-style')) {
        const style = document.createElement('style');
        style.id = 'transcript-smooth-scroll-style';
        style.textContent = `
            #transcriptContent {
                scroll-behavior: smooth;
                padding-right: 10px;
                overflow-y: auto;
                max-height: 500px;
                scrollbar-width: thin;
                scrollbar-color: rgba(0,0,0,0.2) transparent;
            }
            
            #transcriptContent::-webkit-scrollbar {
                width: 8px;
            }
            
            #transcriptContent::-webkit-scrollbar-track {
                background: transparent;
            }
            
            #transcriptContent::-webkit-scrollbar-thumb {
                background-color: rgba(0,0,0,0.2);
                border-radius: 4px;
            }
            
            .transcript-segment {
                padding: 12px;
                margin-bottom: 10px;
                border-left: 3px solid #ccc;
                background: #f8f9fa;
                transition: all 0.25s ease;
                border-radius: 4px;
                cursor: pointer;
                transform: translateX(0);
            }
            
            .transcript-segment.current-segment {
                background-color: #e2f0ff;
                border-left: 3px solid #0056b3;
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                transform: translateX(5px);
            }
        `;
        document.head.appendChild(style);
    }
    
    // Set up event listeners for video player
    const videoPlayer = document.getElementById('videoPlayer');
    if (videoPlayer) {
        // Remove any existing event listeners to prevent duplicates
        videoPlayer.removeEventListener('timeupdate', updateOnTimeChange);
        
        // Add event listener for time updates
        videoPlayer.addEventListener('timeupdate', updateOnTimeChange);
    }
});

// Initialize scoring functionality
async function initializeScoring() {
    const unlockButton = document.getElementById('unlockScoring');
    const sliders = document.querySelectorAll('.scoring-slider');
    let currentSavedScores = {}; // To store the original scores for slider interaction
    
    try {
        // Load saved scores and metrics from backend
        const response = await window.pywebview.api.get_scores(window.currentGuid);
        if (response.success && response.data) {
            currentSavedScores = response.data.scores || {};
            const detailedMetrics = response.data.detailed_metrics || {};
            
            // Update core scoring metrics sliders and values
            updateMainScoresUI(currentSavedScores);
            
            // Update detailed metrics section (including sentiment if available)
            updateDetailedMetrics(detailedMetrics);
        } else {
            console.error('Error loading scores:', response.error);
            // Initialize sliders to 0 or default if no scores found
            updateMainScoresUI({}); 
        }
    } catch (error) {
        console.error('Error initializing scoring:', error);
        updateMainScoresUI({}); // Initialize sliders on error
    }
    
    // Handle unlock button
    unlockButton.addEventListener('click', () => {
        const isUnlocked = unlockButton.classList.contains('unlocked');
        
        if (isUnlocked) {
            // Lock the sliders
            unlockButton.classList.remove('unlocked');
            unlockButton.innerHTML = '<i class="bi bi-lock-fill"></i> Unlock Scoring';
            sliders.forEach(slider => slider.disabled = true);
        } else {
            // Unlock the sliders
            unlockButton.classList.add('unlocked');
            unlockButton.innerHTML = '<i class="bi bi-unlock-fill"></i> Lock Scoring';
            sliders.forEach(slider => slider.disabled = false);
        }
    });
    
    // Handle slider changes
    sliders.forEach(slider => {
        slider.addEventListener('input', async () => {
            const value = slider.value;
            const metric = slider.id.replace('Score', '');
            const metricValue = slider.closest('.metric-item').querySelector('.metric-value');
            
            // Update the metric value display
            metricValue.textContent = `${value}%`;
            
            // Collect all current scores from sliders
            const scoresToSave = {
                scores: {},
                // Assuming detailed_metrics are not editable by sliders, so we don't resave them from here
                // Or, if they are, they need to be fetched and included.
                // For now, only saving what sliders control.
            };
            
            document.querySelectorAll('.scoring-slider').forEach(s => {
                const m = s.id.replace('Score', '');
                const originalData = currentSavedScores[m] || { original: parseInt(s.value), label: m, description: '' }; 
                scoresToSave.scores[m] = {
                    current: parseInt(s.value),
                    original: originalData.original, // Keep the original value that was loaded
                    label: originalData.label,
                    description: originalData.description
                };
            });
             // Fetch existing detailed_metrics to save them back alongside slider changes
            try {
                const existingScoresResponse = await window.pywebview.api.get_scores(window.currentGuid);
                if (existingScoresResponse.success && existingScoresResponse.data && existingScoresResponse.data.detailed_metrics) {
                    scoresToSave.detailed_metrics = existingScoresResponse.data.detailed_metrics;
                }
            } catch (fetchError) {
                console.error('Could not fetch existing detailed_metrics for saving:', fetchError);
                // Fallback: do not include detailed_metrics or include an empty object
                scoresToSave.detailed_metrics = {}; 
            }

            // Save to backend
            try {
                const response = await window.pywebview.api.save_scores(window.currentGuid, scoresToSave);
                if (!response.success) {
                    console.error('Error saving scores:', response.error);
                }
            } catch (error) {
                console.error('Error saving scores:', error);
            }
        });
    });
}

function updateDetailedMetrics(detailedMetrics) {
    console.log("updateDetailedMetrics called with (detailedMetrics):", detailedMetrics ? JSON.parse(JSON.stringify(detailedMetrics)) : "undefined/null");

    // Update Heart Rate metrics (uses 'score' structure)
    const hrMetrics = detailedMetrics?.heart_rate_metrics?.score || {};
    const avgHRElement = document.getElementById('avgHR');
    if (avgHRElement) avgHRElement.textContent = `${hrMetrics.avg_hr?.toFixed(0) || '--'} BPM`;
    const hrVariabilityElement = document.getElementById('hrVariability');
    if (hrVariabilityElement) hrVariabilityElement.textContent = `${hrMetrics.hr_variability?.toFixed(1) || '--'} BPM`;
    const spikeCountElement = document.getElementById('spikeCount');
    if (spikeCountElement) spikeCountElement.textContent = hrMetrics.spike_count || '--';

    // Update Pitch metrics (uses 'score' structure)
    const pitchRanges = detailedMetrics?.pitch_ranges?.score || {};
    const pitchDetails = document.getElementById('pitchDetails');
    if (pitchDetails) {
        if (Object.keys(pitchRanges).length > 0) {
            pitchDetails.innerHTML = Object.entries(pitchRanges)
                .map(([speaker, rangeData]) => {
                    // Assuming rangeData could be a single number or an array/object like [min, max] or {pitch: val}
                    let displayValue = '-- Hz';
                    if (typeof rangeData === 'number') {
                        displayValue = `${rangeData.toFixed(1)} Hz`;
                    } else if (Array.isArray(rangeData) && rangeData.length === 2) {
                         // If it's an array like [fmin, fmax], you might want to display both or an average
                        displayValue = `Range: ${rangeData[0].toFixed(1)} - ${rangeData[1].toFixed(1)} Hz`;
                    } else if (typeof rangeData === 'object' && rangeData !== null && rangeData.pitch !== undefined) {
                        displayValue = `${parseFloat(rangeData.pitch).toFixed(1)} Hz`;
                    } else if (typeof rangeData === 'object' && rangeData !== null && rangeData.f0_mean !== undefined ) { // From potential future librosa output
                        displayValue = `${parseFloat(rangeData.f0_mean).toFixed(1)} Hz (mean)`;
                    }
                    return `
                        <div class="detail-item">
                            <span class="detail-label">${speaker.replace(/_/g, ' ')}:</span>
                            <span class="detail-value">${displayValue}</span>
                        </div>`;
                }).join('');
        } else {
            pitchDetails.innerHTML = '<p>No pitch data available.</p>';
        }
    }


    // Update Speech Rate metrics (uses 'score' structure)
    const speechRates = detailedMetrics?.speech_rates?.score || {};
    const speechRateDetails = document.getElementById('speechRateDetails');
    if (speechRateDetails) {
        if (Object.keys(speechRates).length > 0) {
            speechRateDetails.innerHTML = Object.entries(speechRates)
                .map(([speaker, rate]) => `
                    <div class="detail-item">
                        <span class="detail-label">${speaker.replace(/_/g, ' ')}:</span>
                        <span class="detail-value">${parseFloat(rate).toFixed(1)} WPM</span>
                    </div>
                `).join('');
        } else {
            speechRateDetails.innerHTML = '<p>No speech rate data available.</p>';
        }
    }

    // Update Silence metrics (uses 'score' structure)
    const silenceMetrics = detailedMetrics?.silence_metrics?.score || {};
    const totalSilenceEl = document.getElementById('totalSilence');
    if (totalSilenceEl) totalSilenceEl.textContent = `${silenceMetrics.total_silence?.toFixed(1) || '--'} s`;
    const silenceRatioEl = document.getElementById('silenceRatio');
    if (silenceRatioEl) silenceRatioEl.textContent = `${(silenceMetrics.silence_ratio * 100)?.toFixed(1) || '--'}%`;
    const avgSilenceEl = document.getElementById('avgSilence');
    if (avgSilenceEl) avgSilenceEl.textContent = `${silenceMetrics.avg_silence?.toFixed(1) || '--'} s`;

    // Update Sentiment Analysis metrics (uses 'score' structure)
    const sentimentContainer = document.getElementById('sentimentAnalysisData');
    if (!sentimentContainer) {
        console.error("Sentiment container 'sentimentAnalysisData' not found!");
    } else {
        // More robust check for the presence and structure of sentiment data
        if (detailedMetrics && detailedMetrics.sentiment_analysis && detailedMetrics.sentiment_analysis.score) {
            const sentimentData = detailedMetrics.sentiment_analysis.score;
            console.log("Sentiment data to display (sentiment_analysis.score):", sentimentData ? JSON.parse(JSON.stringify(sentimentData)) : "undefined/null");

            if (typeof sentimentData === 'object' && sentimentData !== null && Object.keys(sentimentData).length > 0) {
                sentimentContainer.innerHTML = Object.entries(sentimentData)
                    .map(([speaker, emotions]) => {
                        let speakerHtml = `<div class="speaker-sentiment-details mb-3">
                                             <h5>${speaker.replace(/_/g, ' ')}</h5><ul>`;
                        if (emotions && typeof emotions === 'object') {
                            const emotionOrder = ['joy', 'sadness', 'love', 'anger', 'fear', 'surprise'];
                            emotionOrder.forEach(emotionKey => {
                                 const score = emotions[emotionKey];
                                 speakerHtml += `<li>${emotionKey.charAt(0).toUpperCase() + emotionKey.slice(1)}: ${score !== undefined && score !== null ? parseFloat(score).toFixed(3) : 'N/A'}</li>`;
                            });

                            speakerHtml += `<li class="mt-2"><strong>Dominant Emotion: ${emotions.dominant_emotion || 'N/A'}</strong></li>`;
                            if (emotions.segments_analyzed !== undefined) {
                                speakerHtml += `<li>Segments Analyzed: ${emotions.segments_analyzed}</li>`;
                            }
                        } else {
                            speakerHtml += '<li>No specific emotion data found for this speaker.</li>';
                        }
                        speakerHtml += `</ul></div>`;
                        return speakerHtml;
                    }).join('');
            } else {
                console.log("Sentiment data (sentiment_analysis.score) is empty or not an object. Displaying default message.");
                sentimentContainer.innerHTML = '<p>No sentiment data processed for this video. Click "Load/Process Full Analytics" to generate it.</p>';
            }
        } else {
            console.log("Path to sentiment data (detailedMetrics.sentiment_analysis.score) is invalid. Full detailedMetrics.sentiment_analysis:", detailedMetrics ? detailedMetrics.sentiment_analysis : "undefined/null");
            sentimentContainer.innerHTML = '<p>Sentiment data not found or structure is incorrect. Click "Load/Process Full Analytics" to generate it.</p>';
        }
    }
}

// New or Modified function to update main score sliders (called by initializeScoring and analytics button)
function updateMainScoresUI(scoresData) {
    const sliders = document.querySelectorAll('.scoring-slider');
    sliders.forEach(slider => {
        const metricKey = slider.id.replace('Score', '');
        const metricItem = slider.closest('.metric-item');
        const metricValueDisplay = metricItem.querySelector('.metric-value');
        const sliderValueDisplay = metricItem.querySelector('.slider-value'); // Assuming this exists
        const metricLabel = metricItem.querySelector('label');

        const scoreInfo = scoresData[metricKey] || {};
        const currentValue = scoreInfo.current !== undefined ? scoreInfo.current : 0;

        slider.value = currentValue;
        if (metricValueDisplay) metricValueDisplay.textContent = `${currentValue}%`;
        if (sliderValueDisplay) sliderValueDisplay.textContent = scoreInfo.description || 'Adjust to score';
        if (metricLabel && scoreInfo.label) metricLabel.textContent = scoreInfo.label;
        if (metricLabel && scoreInfo.description) metricLabel.title = scoreInfo.description; // Tooltip
    });
}

// Initialize diarization functionality
async function initializeDiarization() {
    const transcriptContent = document.getElementById('transcriptContent');
    const saveChangesBtn = document.getElementById('saveChangesBtn');
    const speakerBtns = document.querySelectorAll('.speaker-btn');
    let selectedSegments = [];
    let isEditing = false;
    
    try {
        // Load diarized transcript
        const response = await window.pywebview.api.get_diarized_transcript(window.currentGuid);
        if (response.success) {
            displayDiarizedTranscript(response.data.segments);
        } else {
            console.error('Error loading diarized transcript:', response.error);
            transcriptContent.innerHTML = `
                <div class="alert alert-danger">
                    Error loading diarized transcript: ${response.error}
                </div>
            `;
        }
    } catch (error) {
        console.error('Error initializing diarization:', error);
        transcriptContent.innerHTML = `
            <div class="alert alert-danger">
                Error initializing diarization: ${error}
            </div>
        `;
    }
    
    // Handle segment selection
    transcriptContent.addEventListener('click', (e) => {
        const segment = e.target.closest('.transcript-segment');
        if (!segment) return;
        
        if (!isEditing) {
            showMessage('Please unlock editing first', 'info');
            return;
        }
        
        if (e.ctrlKey || e.metaKey) {
            // Toggle selection with Ctrl/Cmd
            segment.classList.toggle('selected');
            updateSelectedSegments();
        } else {
            // Clear previous selections and select only this segment
            document.querySelectorAll('.transcript-segment.selected').forEach(s => {
                s.classList.remove('selected');
            });
            segment.classList.add('selected');
            selectedSegments = [segment];
            updateSaveButton();
        }
    });
    
    // Handle speaker button clicks
    speakerBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            if (!isEditing) {
                showMessage('Please unlock editing first', 'info');
                return;
            }
            const speaker = btn.dataset.speaker;
            assignSpeakerToSelected(speaker);
        });
    });
    
    // Handle keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (!isEditing) return;
        if (e.key === '1' || e.key === '2') {
            const speaker = e.key;
            assignSpeakerToSelected(speaker);
        }
    });
    
    // Handle save button click
    saveChangesBtn.addEventListener('click', async () => {
        if (isEditing) {
            // Save changes
            try {
                const segments = Array.from(document.querySelectorAll('.transcript-segment')).map(segment => ({
                    start: parseFloat(segment.dataset.start),
                    end: parseFloat(segment.dataset.end),
                    speaker: parseInt(segment.classList.contains('speaker-1') ? '1' : '2'),
                    text: segment.querySelector('.text').textContent
                }));
                
                const response = await window.pywebview.api.save_diarization(window.currentGuid, segments);
                if (response.success) {
                    showMessage('Changes saved successfully', 'success');
                    isEditing = false;
                    saveChangesBtn.innerHTML = '<i class="bi bi-pencil"></i> Edit';
                    document.querySelectorAll('.transcript-segment').forEach(segment => {
                        segment.classList.remove('selected');
                    });
                    selectedSegments = [];
                    updateSaveButton();
                } else {
                    showMessage('Error saving changes: ' + response.error, 'error');
                }
            } catch (error) {
                console.error('Error saving diarization:', error);
                showMessage('Error saving changes', 'error');
            }
        } else {
            // Enable editing
            isEditing = true;
            saveChangesBtn.innerHTML = '<i class="bi bi-save"></i> Save Changes';
        }
    });
    
    function updateSelectedSegments() {
        selectedSegments = Array.from(document.querySelectorAll('.transcript-segment.selected'));
        updateSaveButton();
    }
    
    function updateSaveButton() {
        saveChangesBtn.disabled = !isEditing;
    }
    
    function assignSpeakerToSelected(speaker) {
        if (selectedSegments.length === 0) return;
        
        // Update UI
        selectedSegments.forEach(segment => {
            segment.classList.remove('speaker-1', 'speaker-2');
            segment.classList.add(`speaker-${speaker}`);
            segment.querySelector('.speaker-label').textContent = `Speaker ${speaker}`;
        });
        
        // Clear selection
        selectedSegments.forEach(segment => segment.classList.remove('selected'));
        selectedSegments = [];
        updateSaveButton();
    }
}

// Initialize notes functionality
async function initializeNotes() {
    const notesTextarea = document.querySelector('#notes textarea');
    
    if (!notesTextarea) {
        console.error('Notes textarea not found');
        return;
    }
    
    try {
        // Load saved notes
        console.log('Loading saved notes for GUID:', window.currentGuid);
        const response = await window.pywebview.api.get_notes(window.currentGuid);
        if (response.success) {
            notesTextarea.value = response.data;
            console.log('Loaded notes:', response.data.length, 'characters');
        } else {
            console.error('Failed to load notes:', response.error);
        }
    } catch (error) {
        console.error('Error loading notes:', error);
    }
    
    // Add event listener for notes changes with shorter debounce
    notesTextarea.addEventListener('input', debounce(async function(event) {
        try {
            console.log('Saving notes - length:', this.value.length, 'content preview:', this.value.substring(0, 50));
            const response = await window.pywebview.api.save_notes(window.currentGuid, this.value);
            if (response.success) {
                console.log('Notes saved successfully - length:', this.value.length);
            } else {
                console.error('Error saving notes:', response.error);
            }
        } catch (error) {
            console.error('Error saving notes:', error);
        }
    }, 500)); // Reduced from 1000ms to 500ms
    
    // Also save on blur to ensure content is saved when user clicks away
    notesTextarea.addEventListener('blur', async function() {
        try {
            console.log('Saving notes on blur - length:', this.value.length);
            const response = await window.pywebview.api.save_notes(window.currentGuid, this.value);
            if (response.success) {
                console.log('Notes saved on blur successfully');
            } else {
                console.error('Error saving notes on blur:', response.error);
            }
        } catch (error) {
            console.error('Error saving notes on blur:', error);
        }
    });
}

// Debounce function to limit API calls
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
} 