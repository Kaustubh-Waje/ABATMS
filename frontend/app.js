
// API Base URL
const API_URL = 'http://localhost:8000/api';

// State
let charts = {};
let currentRunId = 'latest';
let loadedData = { adaptive: [], fixed: [] };
let pollingInterval = null;

// Elements
const dom = {
    tabs: document.querySelectorAll('.tab-btn'),
    tabContents: document.querySelectorAll('.tab-content'),
    historyList: document.getElementById('history-list'),
    btnRun: document.getElementById('btn-run'),
    btnRefreshHistory: document.getElementById('btn-refresh-history'),
    status: {
        bar: document.getElementById('status-bar'),
        text: document.getElementById('status-text')
    },
    metrics: {
        adaptiveWait: document.getElementById('metric-adaptive-wait'),
        adaptiveQueue: document.getElementById('metric-adaptive-queue'),
        fixedWait: document.getElementById('metric-fixed-wait'),
        fixedQueue: document.getElementById('metric-fixed-queue'),
    },
    comparison: {
        score: document.getElementById('eff-score'),
        improvement: document.getElementById('eff-improvement')
    },
    tableBody: document.getElementById('data-table-body')
};

// --- Initialization ---

document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    setupTabs();
    fetchHistory();
    loadRunData('latest'); // Initial load

    dom.btnRun.addEventListener('click', runSimulation);
    dom.btnRefreshHistory.addEventListener('click', fetchHistory);
});

function setupTabs() {
    dom.tabs.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active class
            dom.tabs.forEach(b => {
                b.classList.remove('bg-blue-600', 'text-white', 'shadow-lg');
                b.classList.add('text-gray-400', 'hover:text-white', 'hover:bg-white/5');
            });
            dom.tabContents.forEach(c => c.classList.add('hidden'));

            // Add active class
            btn.classList.add('bg-blue-600', 'text-white', 'shadow-lg');
            btn.classList.remove('text-gray-400', 'hover:text-white', 'hover:bg-white/5');

            // Show content
            const target = btn.dataset.tab;
            document.getElementById(`tab-${target}`).classList.remove('hidden');
        });
    });
}

function initCharts() {
    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'top', labels: { color: 'white' } } },
        scales: {
            x: { grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: 'rgba(255, 255, 255, 0.7)' } },
            y: { grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: 'rgba(255, 255, 255, 0.7)' } }
        },
        elements: {
            line: { tension: 0.4 } // Smooth curves
        }
    };

    const ctxWait = document.getElementById('chart-wait-time').getContext('2d');
    charts.wait = new Chart(ctxWait, {
        type: 'line',
        data: { labels: [], datasets: [] },
        options: commonOptions
    });

    const ctxQueue = document.getElementById('chart-queue-length').getContext('2d');
    charts.queue = new Chart(ctxQueue, {
        type: 'line',
        data: { labels: [], datasets: [] },
        options: commonOptions
    });

    const ctxTrend = document.getElementById('chart-trend').getContext('2d');
    charts.trend = new Chart(ctxTrend, {
        type: 'line',
        data: { labels: [], datasets: [] },
        options: {
            ...commonOptions,
            plugins: {
                ...commonOptions.plugins,
                annotation: {
                    annotations: {
                        line1: {
                            type: 'line',
                            yMin: 0,
                            yMax: 0,
                            borderColor: 'rgba(255, 255, 255, 0.2)',
                            borderWidth: 1,
                            borderDash: [5, 5]
                        }
                    }
                }
            }
        }
    });
}

// --- Data Fetching ---

async function fetchHistory() {
    try {
        const res = await fetch(`${API_URL}/history`);
        const history = await res.json();
        renderHistoryList(history);
        fetchAggregateData(); // Also fetch aggregate when history loads
    } catch (e) {
        console.error("Failed to fetch history", e);
    }
}

async function fetchAggregateData() {
    try {
        const res = await fetch(`${API_URL}/history/aggregate`);
        const runs = await res.json();
        updateGlobalComparison(runs);
    } catch (e) {
        console.error("Failed to fetch aggregate data", e);
    }
}

function updateGlobalComparison(runs) {
    if (!runs || runs.length === 0) return;

    // Filter valid data points for each mode
    const adaptiveRuns = runs.filter(r => r.adaptive?.average_waiting_time).map(r => ({
        id: r.run_id,
        val: r.adaptive.average_waiting_time
    }));

    const fixedRuns = runs.filter(r => r.fixed?.average_waiting_time).map(r => ({
        id: r.run_id,
        val: r.fixed.average_waiting_time
    }));

    // Stats Logic
    const avgAdaptive = adaptiveRuns.length ? (adaptiveRuns.reduce((a, b) => a + b.val, 0) / adaptiveRuns.length) : 0;
    const avgFixed = fixedRuns.length ? (fixedRuns.reduce((a, b) => a + b.val, 0) / fixedRuns.length) : 0;
    const bestAdaptive = adaptiveRuns.length ? Math.min(...adaptiveRuns.map(r => r.val)) : 0;

    document.getElementById('global-total-runs').innerText = runs.length;
    document.getElementById('global-avg-improvement').innerText = `${avgAdaptive.toFixed(1)}s`;
    document.getElementById('global-avg-improvement-label').innerText = "Avg Wait (Adaptive)";

    document.getElementById('global-max-improvement').innerText = `${avgFixed.toFixed(1)}s`;
    document.getElementById('global-max-improvement-label').innerText = "Avg Wait (Fixed)";

    // Chart Data Construction
    // Since runs might be missing one mode, we align by Run ID
    const labels = runs.map(r => r.run_id.substring(0, 8)); // X-Axis: All Run IDs

    const adaptiveData = runs.map(r => r.adaptive?.average_waiting_time || null);
    const fixedData = runs.map(r => r.fixed?.average_waiting_time || null);

    charts.trend.data.labels = labels;
    charts.trend.data.datasets = [
        {
            label: 'Adaptive Wait Time (s)',
            data: adaptiveData,
            borderColor: '#3b82f6', // Blue
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            tension: 0.3,
            spanGaps: true
        },
        {
            label: 'Fixed Wait Time (s)',
            data: fixedData,
            borderColor: '#ef4444', // Red
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            tension: 0.3,
            spanGaps: true
        }
    ];
    charts.trend.update();
}

function renderHistoryList(history) {
    dom.historyList.innerHTML = '';

    // Add Latest option
    const latestItem = createHistoryItem('Latest (Local)', 'Current Workspace', 'latest', true);
    dom.historyList.appendChild(latestItem);

    // Add past runs
    history.forEach(run => {
        const item = createHistoryItem(run.timestamp, `${run.mode.toUpperCase()} Mode`, run.run_id, false);
        dom.historyList.appendChild(item);
    });
}

function createHistoryItem(title, subtitle, runId, isLatest) {
    const div = document.createElement('div');
    div.className = `p-3 rounded cursor-pointer transition-all border-l-4 mb-2 ${currentRunId === runId ? 'bg-white/10 border-blue-500' : 'bg-white/5 border-transparent hover:bg-white/10'
        }`;
    div.innerHTML = `
        <p class="font-bold text-sm">${title}</p>
        <p class="text-xs text-gray-400">${subtitle}</p>
    `;
    div.onclick = () => loadRunData(runId);
    return div;
}

async function loadRunData(runId) {
    currentRunId = runId;
    fetchHistory(); // Re-render list to highlight active

    // 1. Fetch Summary
    try {
        const url = runId === 'latest' ? `${API_URL}/latest` : `${API_URL}/run/${runId}`;
        const res = await fetch(url);
        const data = await res.json();
        updateMetrics(data);
    } catch (e) { console.error(e); }

    // 2. Fetch Series Data
    try {
        const [adaptiveRes, fixedRes] = await Promise.all([
            fetch(`${API_URL}/data/${runId}/adaptive`),
            fetch(`${API_URL}/data/${runId}/fixed`)
        ]);

        const adaptiveData = await adaptiveRes.json();
        const fixedData = await fixedRes.json();

        loadedData = { adaptive: adaptiveData, fixed: fixedData };
        updateCharts(adaptiveData, fixedData);
        updateTable(adaptiveData, fixedData);

    } catch (e) { console.error(e); }
}

// --- UI Updates ---

function updateMetrics(data) {
    // Helper to safe get
    const getVal = (obj, key, unit = '') => obj ? (obj[key]?.toFixed(1) + unit) : '--';
    const getInt = (obj, key) => obj ? Math.round(obj[key]) : '--';

    dom.metrics.adaptiveWait.innerText = getVal(data.adaptive, 'average_waiting_time', 's');
    dom.metrics.adaptiveQueue.innerText = getInt(data.adaptive, 'average_queue_length');

    dom.metrics.fixedWait.innerText = getVal(data.fixed, 'average_waiting_time', 's');
    dom.metrics.fixedQueue.innerText = getInt(data.fixed, 'average_queue_length');

    // Comparison Logic
    if (data.adaptive && data.fixed) {
        const fixedWait = data.fixed.average_waiting_time;
        const adaptiveWait = data.adaptive.average_waiting_time;
        const improvement = ((fixedWait - adaptiveWait) / fixedWait) * 100;

        dom.comparison.score.innerText = `${Math.min(100, Math.max(0, improvement + 50)).toFixed(0)}%`; // Fake score logic or real if available
        dom.comparison.improvement.innerText = `${improvement.toFixed(1)}%`;
        dom.comparison.improvement.className = `text-4xl font-bold mb-1 ${improvement > 0 ? 'text-green-400' : 'text-red-400'}`;
    } else {
        dom.comparison.score.innerText = '--%';
        dom.comparison.improvement.innerText = '--%';
    }
}

function updateCharts(adaptiveData, fixedData) {
    // Assuming CSV has 'simulation_time', 'average_waiting_time', 'total_queue_length'

    // Process Labels (Time) - Take from whichever dataset is available
    const labels = (adaptiveData.length > 0 ? adaptiveData : fixedData).map(d => d.simulation_time);

    // Wait Time Chart
    charts.wait.data.labels = labels;
    charts.wait.data.datasets = [
        {
            label: 'Adaptive AI',
            data: adaptiveData.map(d => d.average_waiting_time),
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            fill: true,
            borderWidth: 2
        },
        {
            label: 'Fixed-Time',
            data: fixedData.map(d => d.average_waiting_time),
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            fill: true,
            borderWidth: 2
        }
    ];
    charts.wait.update();

    // Queue Chart
    charts.queue.data.labels = labels;
    charts.queue.data.datasets = [
        {
            label: 'Adaptive AI',
            data: adaptiveData.map(d => d.total_queue_length), // or average_queue_length
            borderColor: '#3b82f6',
            borderWidth: 2
        },
        {
            label: 'Fixed-Time',
            data: fixedData.map(d => d.total_queue_length),
            borderColor: '#ef4444',
            borderWidth: 2
        }
    ];
    charts.queue.update();
}

function updateTable(adaptive, fixed) {
    dom.tableBody.innerHTML = '';

    // Combine for display (limited to 100 rows for performance)
    const limit = 100;
    const data = adaptive.length > 0 ? adaptive : fixed;

    data.slice(0, limit).forEach(row => {
        const tr = document.createElement('tr');
        tr.className = 'border-b border-white/5 hover:bg-white/5';
        tr.innerHTML = `
            <td class="px-6 py-3">${row.simulation_time}</td>
            <td class="px-6 py-3 text-blue-300 font-mono">${row.average_waiting_time.toFixed(1)}</td>
            <td class="px-6 py-3 font-mono">${row.total_queue_length}</td>
            <td class="px-6 py-3 text-gray-400">${row.average_speed?.toFixed(1) || '--'}</td>
        `;
        dom.tableBody.appendChild(tr);
    });
}

// --- Simulation Control ---

async function runSimulation() {
    const mode = document.getElementById('sim-mode').value;
    const duration = document.getElementById('sim-duration').value;
    const useGui = document.getElementById('sim-gui').checked;

    showStatus("Starting simulation...", true);

    try {
        const res = await fetch(`${API_URL}/simulate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode, duration: parseInt(duration), use_gui: useGui })
        });

        await res.json();
        showStatus("Simulation running in background...");

        // Polling
        if (pollingInterval) clearInterval(pollingInterval);
        pollingInterval = setInterval(() => loadRunData('latest'), 2000);

    } catch (error) {
        showStatus("Error starting simulation", false, true);
        console.error(error);
    }
}

function showStatus(msg, loading = false, error = false) {
    dom.status.bar.classList.remove('opacity-0', 'translate-y-10');
    dom.status.text.innerText = msg;

    const dot = dom.status.bar.querySelector('div');
    dot.className = `w-2 h-2 rounded-full ${error ? 'bg-red-500' : 'bg-green-500'} ${loading ? 'animate-pulse' : ''}`;

    if (!loading && !error) {
        setTimeout(() => {
            dom.status.bar.classList.add('opacity-0', 'translate-y-10');
        }, 5000);
    }
}

function downloadCSV() {
    const data = [...loadedData.adaptive, ...loadedData.fixed]; // Simple merge for export
    if (data.length === 0) return alert("No data to download");

    const headers = Object.keys(data[0]).join(',');
    const rows = data.map(row => Object.values(row).join(','));
    const csvContent = "data:text/csv;charset=utf-8," + [headers, ...rows].join('\n');

    const link = document.createElement("a");
    link.setAttribute("href", encodeURI(csvContent));
    link.setAttribute("download", "traffic_data.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}
