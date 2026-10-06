<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Honeypot Security Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        :root {
            --primary: #e35f27;
            --primary-hover: #ca4e20;
            --text-dark: #111827;
            --text-gray: #6b7280;
            --bg-gray: #f9fafb;
            --border: #e5e7eb;
            --white: #ffffff;
            --danger: #ef4444;
            --warning: #f59e0b;
            --success: #10b981;
            --panel-bg: #ffffff;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background: var(--bg-gray);
            color: var(--text-dark);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        header {
            background: var(--white);
            padding: 0 40px;
            height: 70px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border);
            position: sticky;
            top: 0;
            z-index: 50;
        }

        .logo {
            font-weight: 700;
            font-size: 20px;
            color: var(--text-dark);
            text-decoration: none;
            display: flex;
            align-items: center;
            /* gap: 8px; */
            letter-spacing: -0.5px;
        }
        
        .logo span {
            color: var(--primary);
        }

        .nav-link {
            color: var(--text-gray);
            text-decoration: none;
            font-weight: 500;
            font-size: 14px;
            transition: color 0.2s;
            padding: 8px 16px;
            border-radius: 6px;
        }
        .nav-link:hover {
            color: var(--primary);
            background: #fef2f1;
        }

        .main-content {
            padding: 40px;
            max-width: 1400px;
            margin: 0 auto;
            width: 100%;
        }

        .dashboard-header {
            margin-bottom: 30px;
        }

        .dashboard-header h1 {
            font-size: 24px;
            font-weight: 600;
            color: var(--text-dark);
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .dashboard-header p {
            color: var(--text-gray);
            font-size: 14px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 24px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: var(--panel-bg);
            padding: 24px;
            border-radius: 12px;
            border: 1px solid var(--border);
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .stat-card h3 {
            font-size: 13px;
            font-weight: 500;
            color: var(--text-gray);
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .stat-card .value {
            font-size: 32px;
            font-weight: 600;
            color: var(--text-dark);
            margin-bottom: 8px;
            line-height: 1;
        }
        
        /* Modifiers for accent colors on values instead of borders */
        .stat-card.danger .value { color: var(--danger); }
        .stat-card.warning .value { color: var(--warning); }
        .stat-card.success .value { color: var(--success); }

        .stat-card .subtext {
            font-size: 13px;
            color: var(--text-gray);
        }

        .panel {
            background: var(--panel-bg);
            padding: 24px;
            border-radius: 12px;
            border: 1px solid var(--border);
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }

        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border);
        }

        .panel-header h2 {
            font-size: 18px;
            font-weight: 600;
            color: var(--text-dark);
        }

        .btn {
            background: var(--primary);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: background-color 0.2s;
        }

        .btn:hover {
            background: var(--primary-hover);
        }

        .time-range-selector {
            display: flex;
            align-items: center;
        }

        .form-select {
            background: white;
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 13px;
            color: var(--text-dark);
            cursor: pointer;
            min-width: 120px;
        }

        .form-select:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.1);
        }

        .btn-sm {
            padding: 6px 12px;
            font-size: 12px;
        }

        table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
        }

        th {
            padding: 12px 16px;
            text-align: left;
            font-weight: 500;
            font-size: 12px;
            color: var(--text-gray);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            background: #f9fafb;
            border-bottom: 1px solid var(--border);
        }
        
        th:first-child { border-top-left-radius: 8px; }
        th:last-child { border-top-right-radius: 8px; }

        td {
            padding: 16px;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
            color: var(--text-dark);
        }
        
        tr:last-child td { border-bottom: none; }

        tbody tr:hover {
            background: #f9fafb;
        }

        .risk-badge {
            display: inline-flex;
            align-items: center;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: 500;
            text-transform: uppercase;
        }

        .risk-low {
            background: #ecfdf5;
            color: #047857;
            border: 1px solid #d1fae5;
        }
        .risk-medium {
            background: #fffbeb;
            color: #b45309;
            border: 1px solid #fde68a;
        }
        .risk-high {
            background: #fef2f2;
            color: #b91c1c;
            border: 1px solid #fecaca;
        }
        .risk-critical {
            background: #450a0a;
            color: #fca5a5;
            border: 1px solid #7f1d1d;
        }

        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 10px;
        }

        #timeline-chart {
            width: 100%;
            height: 100%;
        }

        .pattern-item {
            background: #f9fafb;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 12px;
            border: 1px solid var(--border);
            display: flex;
            align-items: flex-start;
            gap: 16px;
        }

        .pattern-item .count {
            font-size: 20px;
            font-weight: 600;
            color: var(--primary);
            min-width: 40px;
            text-align: center;
        }

        .pattern-item .details { flex: 1; }

        .pattern-item .template {
            font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
            font-size: 13px;
            color: var(--text-gray);
            word-break: break-all;
            background: #ffffff;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid var(--border);
            margin-top: 4px;
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: var(--text-gray);
            font-size: 14px;
        }

        .code {
            font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
            background: #f3f4f6;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 12px;
            color: #ef4444;
        }

        .timestamp {
            color: var(--text-gray);
            font-size: 12px;
        }
        
        /* Grid layout for main content */
        .dashboard-grid {
            display: grid;
            grid-template-columns: 1fr; /* Force single column */
            gap: 24px;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        @media (max-width: 1024px) {
            .dashboard-grid {
                grid-template-columns: 1fr;
            }
        }

        .chart-container-large {
            height: 400px;
            width: 100%;
        }

        /* Improved clean look for panels */
        .panel {
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            border: 1px solid rgba(0,0,0,0.08);
        }
    </style>
</head>
<body>
    <header>
        <a href="index.php" class="logo">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-right:8px;">
                <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="#e35f27" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 17L12 22L22 17" stroke="#e35f27" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 12L12 17L22 12" stroke="#e35f27" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Form<span>Trap</span>
        </a>
        <nav>
            <a href="mining.php" class="nav-link">Data Mining</a>
            <a href="index.php" class="nav-link">Back to Form</a>
            <a href="about.php" class="nav-link">About</a>
        </nav>
    </header>

    <div class="main-content">
        <div class="dashboard-header">
            <h1>
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" stroke="#111827" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M2 12H22" stroke="#111827" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M12 2A15.3 15.3 0 0 1 12 22A15.3 15.3 0 0 1 12 2" stroke="#111827" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                Analysis Dashboard
            </h1>
            <p>Real-time attack pattern analysis and threat detection system</p>
        </div>

        <!-- Statistics Overview -->
        <div class="stats-grid" id="stats-grid">
            <div class="stat-card">
                <h3>Total Submissions</h3>
                <div class="value" id="stat-total">-</div>
                <div class="subtext"><span id="stat-today">-</span> today</div>
            </div>
            <div class="stat-card danger">
                <h3>Honeypot Triggered</h3>
                <div class="value" id="stat-honeypot">-</div>
                <div class="subtext"><span id="stat-detection-rate">-</span>% detection rate</div>
            </div>
            <div class="stat-card warning">
                <h3>High Risk Submissions</h3>
                <div class="value" id="stat-high-risk">-</div>
                <div class="subtext">Critical or high severity</div>
            </div>
            <div class="stat-card success">
                <h3>Unique Signatures</h3>
                <div class="value" id="stat-signatures">-</div>
                <div class="subtext"><span id="stat-clusters">-</span> clusters</div>
            </div>
        </div>

        <!-- Main Single Column Layout -->
        <div class="dashboard-grid">
            
            <!-- Risk Distribution Chart (Timeline) -->
            <div class="panel">
                <div class="panel-header">
                    <h2>Submission Activity Timeline</h2>
                    <div class="time-range-selector">
                        <select id="timeline-range" class="form-select">
                            <option value="30m">30 minutes</option>
                            <option value="1h">Last hour</option>
                            <option value="12h">Last 12 hours</option>
                            <option value="1d">Last day</option>
                            <option value="7d">7 days</option>
                            <option value="30d" selected>30 days</option>
                        </select>
                    </div>
                </div>
                <!-- Updated height container for better visibility -->
                <div class="chart-container-large">
                    <canvas id="timeline-chart"></canvas>
                </div>
            </div>

            <!-- Recent Submissions -->
            <div class="panel">
                <div class="panel-header">
                    <h2>Recent Submissions</h2>
                    <button class="btn btn-sm" onclick="loadSubmissions()">Refresh</button>
                </div>
                <div id="submissions-table">
                    <div class="loading">Loading submissions...</div>
                </div>
            </div>

            <!-- Top Attack Patterns & Effectiveness (2 Column Grid for these panels) -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 24px;">
                <!-- Top Attack Patterns -->
                <div class="panel">
                    <div class="panel-header">
                        <h2>Top Attack Patterns</h2>
                    </div>
                    <div id="patterns-list">
                        <div class="loading">Loading patterns...</div>
                    </div>
                </div>

                <!-- Honeypot Effectiveness -->
                <div class="panel">
                    <div class="panel-header">
                        <h2>Honeypot Effectiveness</h2>
                    </div>
                    <div id="honeypot-effectiveness">
                        <div class="loading">Loading effectiveness data...</div>
                    </div>
                </div>
            </div>

        </div>
    </div>
    
    <script>
        // Use updated Chart.js defaults for modern look
        Chart.defaults.font.family = "'Inter', system-ui, -apple-system, sans-serif";
        Chart.defaults.color = '#6b7280';
        Chart.defaults.scale.grid.color = '#e5e7eb';
        
        // Initialize dashboard
        let timelineChart = null;

        async function loadDashboard() {
            const currentRange = document.getElementById('timeline-range').value;
            await Promise.all([
                loadStats(),
                loadSubmissions(),
                loadTimeline(currentRange),
                loadPatterns(),
                loadHoneypotEffectiveness()
            ]);
        }

        async function loadStats() {
            try {
                const response = await fetch('api_stats.php?action=stats');
                const data = await response.json();

                document.getElementById('stat-total').textContent = data.total_submissions.toLocaleString();
                document.getElementById('stat-today').textContent = data.today_submissions.toLocaleString();
                document.getElementById('stat-honeypot').textContent = data.honeypot_triggered.toLocaleString();
                document.getElementById('stat-detection-rate').textContent = data.detection_rate;
                document.getElementById('stat-high-risk').textContent = data.high_risk_count.toLocaleString();
                document.getElementById('stat-signatures').textContent = data.unique_signatures.toLocaleString();
                document.getElementById('stat-clusters').textContent = data.total_clusters.toLocaleString();
            } catch (error) {
                console.error('Failed to load stats:', error);
            }
        }

        async function loadSubmissions() {
            try {
                const response = await fetch('api_stats.php?action=recent_submissions&limit=20');
                const data = await response.json();

                const table = `
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Timestamp</th>
                                <th>IP Address</th>
                                <th>Honeypot Hits</th>
                                <th>Timing (ms)</th>
                                <th>Risk</th>
                                <th>Score</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.map(row => `
                                <tr>
                                    <td><span class="code">#${row.id}</span></td>
                                    <td class="timestamp">${new Date(row.created_at).toLocaleString()}</td>
                                    <td><span class="code">${row.ip}</span></td>
                                    <td>${row.honeypot_count || 0}</td>
                                    <td>${row.client_render_time || '-'}</td>
                                    <td><span class="risk-badge risk-${row.risk_level || 'low'}">${row.risk_level || 'N/A'}</span></td>
                                    <td>${row.score || '-'}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;

                document.getElementById('submissions-table').innerHTML = table;
            } catch (error) {
                console.error('Failed to load submissions:', error);
            }
        }

        // Helper function to generate empty labels based on time range
        function generateEmptyLabels(range) {
            const now = new Date();
            let labels = [];
            let unit = 'day';

            switch (range) {
                case '30m':
                    unit = 'minute';
                    for (let i = 29; i >= 0; i--) {
                        const date = new Date(now);
                        date.setMinutes(date.getMinutes() - i);
                        labels.push(date.toLocaleTimeString('en-US', { 
                            hour: '2-digit', 
                            minute: '2-digit' 
                        }));
                    }
                    break;
                case '1h':
                    unit = 'minute';
                    for (let i = 59; i >= 0; i--) {
                        const date = new Date(now);
                        date.setMinutes(date.getMinutes() - i);
                        labels.push(date.toLocaleTimeString('en-US', { 
                            hour: '2-digit', 
                            minute: '2-digit' 
                        }));
                    }
                    break;
                case '12h':
                    unit = 'hour';
                    for (let i = 11; i >= 0; i--) {
                        const date = new Date(now);
                        date.setHours(date.getHours() - i);
                        labels.push(date.toLocaleTimeString('en-US', { 
                            hour: '2-digit', 
                            minute: '2-digit' 
                        }));
                    }
                    break;
                case '1d':
                    unit = 'hour';
                    for (let i = 23; i >= 0; i--) {
                        const date = new Date(now);
                        date.setHours(date.getHours() - i);
                        labels.push(date.toLocaleTimeString('en-US', { 
                            hour: '2-digit', 
                            minute: '2-digit' 
                        }));
                    }
                    break;
                case '7d':
                    unit = 'day';
                    for (let i = 6; i >= 0; i--) {
                        const date = new Date(now);
                        date.setDate(date.getDate() - i);
                        labels.push(date.toLocaleDateString('en-US', { 
                            month: 'short', 
                            day: 'numeric' 
                        }));
                    }
                    break;
                case '30d':
                default:
                    unit = 'day';
                    for (let i = 29; i >= 0; i--) {
                        const date = new Date(now);
                        date.setDate(date.getDate() - i);
                        labels.push(date.toLocaleDateString('en-US', { 
                            month: 'short', 
                            day: 'numeric' 
                        }));
                    }
                    break;
            }

            return { labels, unit };
        }

        // Helper function to generate complete timeline with all time periods
        function generateCompleteTimeline(data, range, now) {
            const labels = [];
            const dataMap = {};

            // First, create a map of the actual data keyed by formatted label
            data.forEach(d => {
                const date = new Date(d.date);
                let key;
                switch (range) {
                    case '30m':
                    case '1h':
                        key = date.toLocaleTimeString('en-US', { 
                            hour: '2-digit', 
                            minute: '2-digit' 
                        });
                        break;
                    case '12h':
                    case '1d':
                        key = date.toLocaleTimeString('en-US', { 
                            hour: '2-digit', 
                            minute: '2-digit' 
                        });
                        break;
                    case '7d':
                    case '30d':
                    default:
                        key = date.toLocaleDateString('en-US', { 
                            month: 'short', 
                            day: 'numeric' 
                        });
                        break;
                }
                dataMap[key] = {
                    total: parseInt(d.total),
                    honeypot_triggered: parseInt(d.honeypot_triggered)
                };
            });

            // Generate all labels for the complete time range (oldest to newest)
            switch (range) {
                case '30m':
                    for (let i = 0; i < 30; i++) {
                        const date = new Date(now);
                        date.setMinutes(date.getMinutes() - (29 - i)); // Start from oldest
                        labels.push(date.toLocaleTimeString('en-US', { 
                            hour: '2-digit', 
                            minute: '2-digit' 
                        }));
                    }
                    break;
                case '1h':
                    for (let i = 0; i < 60; i++) {
                        const date = new Date(now);
                        date.setMinutes(date.getMinutes() - (59 - i)); // Start from oldest
                        labels.push(date.toLocaleTimeString('en-US', { 
                            hour: '2-digit', 
                            minute: '2-digit' 
                        }));
                    }
                    break;
                case '12h':
                    for (let i = 0; i < 12; i++) {
                        const date = new Date(now);
                        date.setHours(date.getHours() - (11 - i)); // Start from oldest
                        labels.push(date.toLocaleTimeString('en-US', { 
                            hour: '2-digit', 
                            minute: '2-digit' 
                        }));
                    }
                    break;
                case '1d':
                    for (let i = 0; i < 24; i++) {
                        const date = new Date(now);
                        date.setHours(date.getHours() - (23 - i)); // Start from oldest
                        labels.push(date.toLocaleTimeString('en-US', { 
                            hour: '2-digit', 
                            minute: '2-digit' 
                        }));
                    }
                    break;
                case '7d':
                    for (let i = 0; i < 7; i++) {
                        const date = new Date(now);
                        date.setDate(date.getDate() - (6 - i)); // Start from oldest
                        labels.push(date.toLocaleDateString('en-US', { 
                            month: 'short', 
                            day: 'numeric' 
                        }));
                    }
                    break;
                case '30d':
                default:
                    for (let i = 0; i < 30; i++) {
                        const date = new Date(now);
                        date.setDate(date.getDate() - (29 - i)); // Start from oldest
                        labels.push(date.toLocaleDateString('en-US', { 
                            month: 'short', 
                            day: 'numeric' 
                        }));
                    }
                    break;
            }

            return { labels, dataMap };
        }
        // Helper function to get appropriate max ticks for different time ranges
        function getMaxTicksForRange(range) {
            switch (range) {
                case '30m':
                    return 10; // Show every 3 minutes
                case '1h':
                    return 12; // Show every 5 minutes
                case '12h':
                    return 12; // Show every hour
                case '1d':
                    return 8; // Show every 3 hours
                case '7d':
                    return 7; // Show daily
                case '30d':
                default:
                    return 7; // Show ~4-5 day intervals
            }
        }

        async function loadTimeline(range) {
            try {
                const response = await fetch(`api_stats.php?action=timeline&range=${range}`);
                const data = await response.json();

                console.log('Timeline data received:', data); // Debug log

                // Handle empty data
                if (!data || data.length === 0) {
                    console.log('No timeline data available, creating empty chart');
                    // Create empty chart with placeholder data based on range
                    const { labels, unit } = generateEmptyLabels(range);
                    
                    const ctx = document.getElementById('timeline-chart').getContext('2d');
                    if (timelineChart) {
                        timelineChart.destroy();
                    }

                    timelineChart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: labels,
                            datasets: [
                                {
                                    label: 'Total Submissions',
                                    data: new Array(labels.length).fill(0),
                                    borderColor: '#4f46e5', // Primary Brand Color
                                    backgroundColor: (context) => {
                                        const ctx = context.chart.ctx;
                                        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
                                        gradient.addColorStop(0, 'rgba(79, 70, 229, 0.2)');
                                        gradient.addColorStop(1, 'rgba(79, 70, 229, 0)');
                                        return gradient;
                                    },
                                    borderWidth: 2,
                                    tension: 0.4,
                                    pointRadius: 0,
                                    pointHoverRadius: 6,
                                    fill: true
                                },
                                {
                                    label: 'Honeypot Triggered',
                                    data: new Array(labels.length).fill(0),
                                    borderColor: '#ef4444', // Danger Color
                                    backgroundColor: 'transparent',
                                    borderWidth: 2,
                                    borderDash: [5, 5],
                                    tension: 0.4,
                                    pointRadius: 0,
                                    pointHoverRadius: 6,
                                    fill: false
                                }
                            ]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            interaction: {
                                mode: 'index',
                                intersect: false,
                            },
                            plugins: {
                                legend: {
                                    position: 'top',
                                    align: 'end',
                                    labels: {
                                        usePointStyle: true,
                                        boxWidth: 8,
                                        padding: 20,
                                        font: {
                                            size: 12,
                                            family: "'Inter', sans-serif"
                                        }
                                    }
                                },
                                tooltip: {
                                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                                    titleColor: '#111827',
                                    bodyColor: '#4b5563',
                                    borderColor: '#e5e7eb',
                                    borderWidth: 1,
                                    padding: 12,
                                    displayColors: true,
                                    boxPadding: 6
                                }
                            },
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    grid: {
                                        color: '#f3f4f6',
                                        drawBorder: false,
                                    },
                                    ticks: {
                                        padding: 10,
                                        font: { size: 11 }
                                    },
                                    border: { display: false }
                                },
                                x: {
                                    type: 'category',
                                    grid: {
                                        display: false,
                                        drawBorder: false
                                    },
                                    ticks: {
                                        padding: 10,
                                        maxTicksLimit: getMaxTicksForRange(range),
                                        font: { size: 11 },
                                        autoSkip: true,
                                        maxRotation: 45,
                                        minRotation: 0
                                    }
                                }
                            }
                        }
                    });
                    return;
                }

                // Process data with appropriate label formatting and fill missing periods
                const now = new Date();
                const { labels, dataMap } = generateCompleteTimeline(data, range, now);
                const totals = labels.map(label => dataMap[label]?.total || 0);
                const honeypots = labels.map(label => dataMap[label]?.honeypot_triggered || 0);

                const ctx = document.getElementById('timeline-chart').getContext('2d');

                if (timelineChart) {
                    timelineChart.destroy();
                }

                timelineChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [
                            {
                                label: 'Total Submissions',
                                data: totals,
                                borderColor: '#4f46e5', // Primary Brand Color
                                backgroundColor: (context) => {
                                    const ctx = context.chart.ctx;
                                    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
                                    gradient.addColorStop(0, 'rgba(79, 70, 229, 0.2)');
                                    gradient.addColorStop(1, 'rgba(79, 70, 229, 0)');
                                    return gradient;
                                },
                                borderWidth: 2,
                                tension: 0.4,
                                pointRadius: 0,
                                pointHoverRadius: 6,
                                fill: true
                            },
                            {
                                label: 'Honeypot Triggered',
                                data: honeypots,
                                borderColor: '#ef4444', // Danger Color
                                backgroundColor: 'transparent',
                                borderWidth: 2,
                                borderDash: [5, 5],
                                tension: 0.4,
                                pointRadius: 0,
                                pointHoverRadius: 6,
                                fill: false
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: {
                            mode: 'index',
                            intersect: false,
                        },
                        plugins: {
                            legend: {
                                position: 'top',
                                align: 'end',
                                labels: {
                                    usePointStyle: true,
                                    boxWidth: 8,
                                    padding: 20,
                                    font: {
                                        size: 12,
                                        family: "'Inter', sans-serif"
                                    }
                                }
                            },
                            tooltip: {
                                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                                titleColor: '#111827',
                                bodyColor: '#4b5563',
                                borderColor: '#e5e7eb',
                                borderWidth: 1,
                                padding: 12,
                                displayColors: true,
                                boxPadding: 6
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                grid: {
                                    color: '#f3f4f6',
                                    drawBorder: false,
                                },
                                ticks: {
                                    padding: 10,
                                    font: { size: 11 }
                                },
                                border: { display: false }
                            },
                            x: {
                                type: 'category',
                                grid: {
                                    display: false,
                                    drawBorder: false
                                },
                                ticks: {
                                    padding: 10,
                                    maxTicksLimit: getMaxTicksForRange(range),
                                    font: { size: 11 },
                                    autoSkip: true,
                                    maxRotation: 45,
                                    minRotation: 0
                                }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error('Failed to load timeline:', error);
                // Show error message in chart area
                const chartContainer = document.querySelector('.chart-container-large');
                if (chartContainer) {
                    chartContainer.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #6b7280; font-size: 14px; text-align: center;">Unable to load chart data<br><small>Check console for details</small></div>';
                }
            }
        }

        async function loadPatterns() {
            try {
                const response = await fetch('api_stats.php?action=top_patterns&limit=10');
                const data = await response.json();

                const html = data.map(pattern => {
                    const occurrence = pattern.occurrence || 0;
                    const patternText = escapeHtml(pattern.pattern || '');
                    const lastSeen = pattern.last_seen ? new Date(pattern.last_seen).toLocaleString() : 'Unknown';
                    
                    return `
                        <div class="pattern-item">
                            <div class="count">${occurrence} occurrences</div>
                            <div class="template">${patternText}</div>
                            <div class="timestamp">Last seen: ${lastSeen}</div>
                        </div>
                    `;
                }).join('');

                document.getElementById('patterns-list').innerHTML = html || '<p style="color: #64748b;">No patterns detected yet.</p>';
            } catch (error) {
                console.error('Failed to load patterns:', error);
            }
        }

        async function loadHoneypotEffectiveness() {
            try {
                const response = await fetch('api_stats.php?action=honeypot_effectiveness');
                const data = await response.json();

                const html = Object.entries(data).map(([type, info]) => {
                    const hits = info.hits || 0;
                    const fieldName = escapeHtml(info.field_name || '');
                    const typeName = escapeHtml(type || '');
                    
                    return `
                        <div class="pattern-item">
                            <div class="count">${hits} hits</div>
                            <div class="template">${typeName}: <strong>${fieldName}</strong></div>
                        </div>
                    `;
                }).join('');

                document.getElementById('honeypot-effectiveness').innerHTML = html;
            } catch (error) {
                console.error('Failed to load honeypot effectiveness:', error);
            }
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Auto-refresh every 30 seconds
        setInterval(loadDashboard, 30000);

        // Timeline range selector event listener
        document.getElementById('timeline-range').addEventListener('change', function(e) {
            loadTimeline(e.target.value);
        });

        // Initial load - wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', loadDashboard);
        } else {
            loadDashboard();
        }
    </script>
</body>
</html>
