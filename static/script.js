let realTimeUpdate = true; // Global variable to control real-time updates

document.addEventListener("DOMContentLoaded", function() {
    // Initialize WebSocket and Plotly
    const socket = new WebSocket("ws://tendergarden.io/ws/carbon-footprint");
    // const socket = new WebSocket("ws://localhost:8000/ws/carbon-footprint");
    const trace1 = createTrace('Server: Carbon Emitted', '#1f77b4');
    const trace2 = createTrace('Plant: Carbon Sequestered', '#1fb465');
    const layout = createLayout();
    Plotly.newPlot('graph', [trace1, trace2], layout, {displayModeBar: false});

    // Initialize Popups
    const $hoverPopup = createPopup('hover-popup');
    const $citationPopup = createPopup('citation-popup');

    // WebSocket event handlers
    socket.onmessage = (event) => {
        handleSocketMessage(event, trace1, trace2, layout, realTimeUpdate);
    };

    socket.onclose = logWebSocketEvent;
    socket.onerror = logWebSocketError;

    // Setup event listeners
    // setupToggleButtons(trace1, layout);
    setupPopupListeners($hoverPopup, $citationPopup);

    // "seconds" button
    document.getElementById("toggle-seconds").addEventListener("click", function() {
        realTimeUpdate = true; // Enable real-time updates
    
        // Get the current time
        const latestTime = new Date();
        const minTime = new Date(latestTime.getTime() - 60000); // 60 seconds before
    
        // Adjust the x-axis range to show only the last 60 seconds
        Plotly.relayout('graph', {
            'xaxis.range': [minTime, latestTime],
            'xaxis.tickformat': '%H:%M:%S', // Show time in hours, minutes, seconds
            'xaxis.title': 'Time (seconds)',
            'xaxis.tickvals': Array.from({ length: 60 }, (_, i) => minTime.getTime() + i * 1000), // Ticks for each second
            'xaxis.ticktext': Array.from({ length: 60 }, (_, i) => {
                const date = new Date(minTime.getTime() + i * 1000);
                return i % 5 === 0 ? date.toLocaleTimeString("en-US", { hour12: false }) : "";
            }), // Labels for every 5 seconds
            'xaxis.dtick': 5000, // 1 second in milliseconds
            'xaxis.showgrid': true // Show grid lines
            
        });
    
        // Continue to update the graph in real-time
        socket.onmessage = (event) => {
            handleSocketMessage(event, trace1, trace2, layout, realTimeUpdate);
        };
    });
    

    // exhibition view
    document.getElementById("toggle-exhibition-view").addEventListener("click", function() {
        realTimeUpdate = false;
        zoomToExhibition();
        updateTraceForExhibitionView(trace1);
        populateTreeDataFromArchive(trace2);
    });

    // ecological view
    document.getElementById("toggle-ecological-view").addEventListener("click", function() {
        realTimeUpdate = false;
        zoomToLifetime();
        updateTraceForLifetimeView(trace1);
        populateTreeDataFromArchive(trace2);
        insertTreePlantingStart(trace2);
    });

    // Fetch server data after the initial graph is rendered
    fetchServerData();
    pollingInterval = setInterval(pollForUpdates, 600000); // 600000 ms = 10 minutes

    // Function definitions
    function createTrace(name, color) {
        return { x: [], y: [], mode: 'lines', name, line: { color } };
    }

    function createLayout() {
            return {
                dragmode: false,
                title: 'Carbon Footprint',
                margin: { t: 50, l: 50, r: 30, b: 100 },
                yaxis: { 
                        range: [0, 0.1], 
                        title: { text: 'Carbon (kg)', standoff: 20 },
                        automargin: true 
                    },
                xaxis: {
                    title: { text: 'Time (s)', standoff: 15 },
                    automargin: true,
                    tickformat: "%H:%M:%S",
                    tickangle: -45,
                    dtick: 5000,
                    tickmode: "linear",
                    gridcolor: "#ccc",
                    tickvals: [],
                    ticktext: []
                },
                showlegend: false
            };
        }

    function handleSocketMessage(event, trace1, trace2, layout, realTimeUpdate) {
        const data = JSON.parse(event.data);
        if (realTimeUpdate) {
            updateTraces(data, trace1, trace2);
            Plotly.update('graph', { x: [trace1.x, trace2.x], y: [trace1.y, trace2.y] }, layout);
            updateYAxisRange([trace1, trace2], layout);
        }
        updateDisplayElements(data);
    }

    function updateTraces(data, trace1, trace2) {
        const time = new Date(); // Use the current time as X-axis
        const capturedValue = getMostRecentCapturedValue();
        trace1.x.push(time);
        trace1.y.push(data.total_co2_emissions);

        trace2.x.push(time);
        trace2.y.push(capturedValue);

        // Remove older points to keep the graph within 60 seconds
        if (trace1.x.length > 60) {
            trace1.x.shift();
            trace1.y.shift();
        }
        if (trace2.x.length > 60) {
            trace2.x.shift();
            trace2.y.shift();
        }

        // Update X-axis layout
        const latestTime = time;
        const minTime = new Date(latestTime.getTime() - 60000); // 60 seconds before

        layout.xaxis.range = [minTime, latestTime];
        layout.xaxis.tickvals = Array.from({ length: 60 }, (_, i) => minTime.getTime() + i * 1000);
        layout.xaxis.ticktext = layout.xaxis.tickvals.map((val, i) => {
            const date = new Date(val);
            return i % 5 === 0 ? date.toLocaleTimeString("en-US", { hour12: false }) : "";
        });
    }

    function getMostRecentCapturedValue() {
        // Assuming the most recent archive object is the first in the list
        const mostRecentArchive = document.querySelector('.archive-item:first-child');
        return mostRecentArchive ? parseFloat(mostRecentArchive.getAttribute('data-captured-value')) : 0;
    }

    function fetchLastSixtySecondsData(trace1, trace2, layout) {
        fetch("/graph/seconds")
            .then(response => response.json())
            .then(data => {
                const secondsData = data.meter_seconds;
                const xValues = secondsData.map(d => new Date(d.date));
                const yValues1 = secondsData.map(d => d.value); // Assuming this corresponds to trace1
                const yValues2 = []; // Populate based on your data structure

                trace1.x = xValues;
                trace1.y = yValues1;
                trace2.x = xValues;
                trace2.y = yValues2;

                const latestTime = new Date(xValues[xValues.length - 1]);
                const minTime = new Date(latestTime.getTime() - 60000); // 60 seconds before

                layout.xaxis.range = [minTime, latestTime];
                layout.xaxis.tickvals = Array.from({ length: 60 }, (_, i) => minTime.getTime() + i * 1000);
                layout.xaxis.ticktext = layout.xaxis.tickvals.map((val, i) => {
                    const date = new Date(val);
                    return i % 5 === 0 ? date.toLocaleTimeString("en-US", { hour12: false }) : "";
                });

                Plotly.react('graph', [trace1, trace2], layout);
            });
    }

    function zoomToExhibition() {
        console.log('Zooming to exhibition');
        Plotly.relayout('graph', {
            'xaxis.range': ['2024-08-16T00:00:00Z', new Date().toISOString()], // Hardcoded start date, current date as end
            'xaxis.dtick': 3600000, // 1 hour in milliseconds (1 hour * 60 minutes * 60 seconds * 1000 milliseconds)
            'xaxis.tickformat': '%H:%M', // Show time in hours and minutes
            'xaxis.title': 'Time (days)'        });
        //update so that it checks if the latest entry in the energyRecord table is after the last plot pointed, if it is, add it to trace 1
    }

    function zoomToLifetime() {
        console.log('Zooming to lifeTime');

        Plotly.relayout('graph', {
            'xaxis.range': ['2022-04-05T00:00:00Z', new Date().toISOString()], // Hardcoded start date, current date as end
            // 'xaxis.tickvals': tickvals, // Show only the first day of each month
            // 'xaxis.ticktext': ticktext, // Label for each tick
            'xaxis.tickformat': '%b %d', // Show date in "Month Day" format (e.g., "Apr 01")
            'xaxis.title': 'Time (months)',
            'xaxis.dtick': 2592000000, // Approx 1 month in milliseconds (30 days * 24 hours * 60 minutes * 60 seconds * 1000 milliseconds)
            'xaxis.showgrid': true // Show grid lines at these ticks
        });
    }

    function insertTreePlantingStart(trace) {
        // Insert the new point at the beginning of the x and y arrays
        trace.x.unshift('2022-04-05T00:00:00Z');
        trace.y.unshift(0);
    
        // Update the graph to reflect the change
        Plotly.redraw('graph');
    }

    function populateTreeDataFromArchive(trace) {
        const archiveItems = document.querySelectorAll('.archive-item');
        const newX = [];
        const newY = [];
    
        archiveItems.forEach(item => {
            const time = item.getAttribute('data-time');
            console.log(`${time} - ${item.getAttribute('data-captured-value')}`);
            const value = parseFloat(item.getAttribute('data-captured-value'));
    
            newX.push(time);
            newY.push(value);
        });
    
        trace.x = newX;
        trace.y = newY;
    
        Plotly.redraw('graph');
    }

    function updateTraceForLifetimeView(serverTrace) {
        // Update for server trace
        const dailyData = {};
    
        // Iterate over serverData to get the latest value for each day
        serverData.forEach(point => {
            const date = point.datetime.split('T')[0]; // Get the date part only
            dailyData[date] = point; // This will overwrite to ensure we get the latest value of the day
        });
    
        const filteredData = Object.values(dailyData);
    
        serverTrace.x = filteredData.map(point => point.datetime);
        serverTrace.y = filteredData.map(point => point.total_co2_emissions);
    
        Plotly.redraw('graph');
    }

    function updateTraceForExhibitionView(trace) {
        // Use the entire serverData
        trace.x = serverData.map(point => point.datetime);
        trace.y = serverData.map(point => point.total_co2_emissions);

        // Filter the x values to get one tick every 24 hours
        const tickvals = [];
        const ticktext = [];

        serverData.forEach(point => {
            const hour = new Date(point.datetime).getHours();
            // Check if it's exactly 00:00:00 (midnight)
            if (hour === 0) {
                tickvals.push(point.datetime);
                ticktext.push(point.datetime.split(' ')[0]); // Only show the date part
            }
        });

        // Update the graph with the filtered tick values
        Plotly.relayout('graph', {
            'xaxis.tickvals': tickvals,
            'xaxis.ticktext': ticktext,
            'xaxis.tickformat': '%b %d', // Format the ticks to show only the date
            'xaxis.tickangle': -45, // Rotate the ticks for better readability
            'xaxis.showgrid': true, // Show grid lines at these ticks
            'xaxis.dtick': 86400000 // Ensure ticks are every 24 hours (in milliseconds)
        });
    
        Plotly.redraw('graph');
    }

    async function fetchServerData() {
        try {
            const response = await fetch('/graph/hours'); // API call
            data = await response.json(); // Store the data globally

            if (data && Array.isArray(data.serverHistory)) {
                serverData = data.serverHistory;
            } else {
                console.error('Unexpected data format:', data);
                return;
            }

        } catch (error) {
            console.error('Error fetching server data:', error);
        }
    }
    
    async function pollForUpdates() {
        try {
            const response = await fetch('/graph/hours/last'); // API call to get the latest entry
            const latestData = await response.json();
    
            if (latestData && serverData.length > 0) {
                const lastRecorded = serverData[serverData.length - 1];
    
                // Check if the new data is different from the last recorded data
                if (latestData.time !== lastRecorded.time) {
                    serverData.push(latestData); // Add the new data to the serverData array
                }
            }
        } catch (error) {
            console.error('Error polling for updates:', error);
        }
    }
    
    // Function to update the Y-axis range based on trace data
    function updateYAxisRange(traces, layout) {
        let maxYValue = 0;
        traces.forEach(trace => {
            const maxTraceY = Math.max(...trace.y);
            if (maxTraceY > maxYValue) {
                maxYValue = maxTraceY;
            }
        });
        layout.yaxis.range = [0, maxYValue + 0.2];
        Plotly.relayout('graph', layout);
    };

    function updateDisplayElements(data) {
        document.getElementById("current-watts").textContent = data.current_watts.toFixed(2);
        document.getElementById("total-kwh").textContent = data.total_kwh.toFixed(6);
        document.getElementById("carbon-output").textContent = data.total_co2_emissions.toFixed(6);
        // console.log(JSON.stringify(data, null, 2)); // Pretty print the JSON object
        // document.getElementById("total-carbon-offset").textContent = data.total_co2_offset.toFixed(6);

        const uptime = parseInt(data.uptime_seconds);
        document.getElementById("uptime").textContent = formatTime(uptime);
    }

    function formatTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    function logWebSocketEvent(event) {
        console.log("WebSocket closed:", event);
    }

    function logWebSocketError(error) {
        console.log("WebSocket error:", error);
    }

    function createPopup(className) {
        return $('<div class="popup ' + className + '"></div>').appendTo('body').hide();
    }

    function setupPopupListeners($hoverPopup, $citationPopup) {
        $('.hover-popup').on('click', function(event) {
            event.stopPropagation();
            const tagId = $(this).data('tag-id');
            fetchPopupContent(`/get-popup-content/${tagId}`, showHoverPopup, event, $hoverPopup);
        });

        $(document).on('click', function(event) {
            if (!$(event.target).closest('.citation-popup').length && !$(event.target).is('.citation-popup-trigger')) {
                $citationPopup.hide();
            }
        });

        $hoverPopup.on('click', function(event) {
            event.stopPropagation();
            $hoverPopup.hide();
        });
    }

    function showHoverPopup(event, content, $hoverPopup) {
        const column = $(event.target).closest('.left-column');
        if (column.length === 0) {
            console.error("Column not found.");
            return;
        }

        const { leftPosition, topPosition } = calculatePopupPosition(event, column);
        $hoverPopup.html(content).css({ left: leftPosition, top: topPosition, display: 'block' });
        attachCitationClickHandler($hoverPopup);
    }

    function calculatePopupPosition(event, column) {
        const columnOffset = column.offset();
        const columnWidth = column.outerWidth();
        const topPosition = event.pageY - ((event.pageY - 0) * 2 / 3);
        const leftPosition = event.pageX + ((columnOffset.left + columnWidth - event.pageX) * 5 / 7);
        return { leftPosition: leftPosition + 'px', topPosition: topPosition + 'px' };
    }

    function attachCitationClickHandler($popup) {
        $popup.find('.citation-popup-trigger').on('click', function(event) {
            event.stopPropagation();
            const citationId = $(this).data('id');
            fetchPopupContent(`/get-popup-content/${citationId}`, showCitationPopup, event, $citationPopup);
        });
    }

    function showCitationPopup(event, content, $citationPopup) {
        $citationPopup.html(content).css({
            left: event.pageX + 10 + 'px',
            top: event.pageY + 10 + 'px',
            display: 'block'
        });
    }

    function fetchPopupContent(url, callback, event, $popup) {
        $.ajax({
            url: url,
            method: 'GET',
            success: function(data) {
                callback(event, data, $popup);
            },
            error: function() {
                callback(event, '<p>Error loading content.</p>', $popup);
            }
        });
    }

    // function setupToggleButtons(trace1, layout) {
    //     document.getElementById("toggle-seconds").addEventListener("click", function() {
    //         updateXAxis(trace1.x, layout, 'Time (s)');
    //     });

    //     document.getElementById("toggle-hours").addEventListener("click", function() {
    //         updateXAxis([trace1.x[0], trace1.x[0] + 3600], layout, 'Time (hours)');
    //     });

    //     document.getElementById("toggle-days").addEventListener("click", function() {
    //         updateXAxis([trace1.x[0], trace1.x[0] + 86400], layout, 'Time (days)');
    //     });

    //     document.getElementById("toggle-years").addEventListener("click", function() {
    //         updateXAxis([trace1.x[0], trace1.x[0] + 31536000], layout, 'Time (years)');
    //     });

    //     document.getElementById("toggle-exhibition").addEventListener("click", function() {
    //         updateXAxis(trace1.x, layout, 'Time (since the beginning of the exhibition)');
    //     });
    // }

    // function updateXAxis(range, layout, title) {
    //     Plotly.relayout('graph', {
    //         'xaxis.range': range,
    //         'xaxis.title': title
    //     });
    // }
});
