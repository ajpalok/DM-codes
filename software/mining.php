<?php
/**
 * Data-mining view: what was mined from five years of submissions and how it is used on live traffic.
 * Reads the notebook's exports from ml_service/artifacts/ and live figures from api_stats.php.
 */

function artifact($name) {
    $path = __DIR__ . '/ml_service/artifacts/' . $name;
    return file_exists($path) ? json_decode(file_get_contents($path), true) : null;
}

$metrics = artifact('metrics.json');
$card = artifact('model_card.json');
$clusters = artifact('clusters.json');
$rules = artifact('rules.json');
$ready = $metrics && $card && $clusters && $rules;

function e($text) {
    return htmlspecialchars((string) $text, ENT_QUOTES, 'UTF-8');
}

function pct($value, $digits = 0) {
    return $value === null ? '&ndash;' : number_format($value * 100, $digits) . '%';
}

// One row per classifier: cross-validated scores joined with the out-of-corpus checks
$models = [];
if ($ready) {
    $cross = array_column($metrics['task_b']['cross_source'], null, 'model');
    foreach ($metrics['task_b']['cv'] as $row) {
        if (strpos($row['model'], 'Baseline: majority') === 0) {
            continue;
        }
        $models[] = $row + ['cross' => $cross[$row['model']] ?? null];
    }
    usort($models, fn($a, $b) => $b['balanced_acc'] <=> $a['balanced_acc']);
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Mining - FormTrap</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        :root {
            --primary: #e35f27;
            --text-dark: #111827;
            --text-gray: #6b7280;
            --bg-gray: #f9fafb;
            --border: #e5e7eb;
            --white: #ffffff;
            --danger: #ef4444;
            --success: #10b981;
            --series: #2a78d6;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', system-ui, -apple-system, sans-serif; background: var(--bg-gray); color: var(--text-dark); min-height: 100vh; }
        header { background: var(--white); padding: 0 40px; height: 70px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 50; }
        .logo { font-weight: 700; font-size: 20px; color: var(--text-dark); text-decoration: none; display: flex; align-items: center; letter-spacing: -0.5px; }
        .logo span { color: var(--primary); }
        .nav-link { color: var(--text-gray); text-decoration: none; font-weight: 500; font-size: 14px; padding: 8px 16px; border-radius: 6px; }
        .nav-link:hover, .nav-link.active { color: var(--primary); background: #fef2f1; }
        .main-content { padding: 40px; max-width: 1400px; margin: 0 auto; width: 100%; }
        .page-header { margin-bottom: 30px; }
        .page-header h1 { font-size: 24px; font-weight: 600; margin-bottom: 8px; }
        .page-header p { color: var(--text-gray); font-size: 14px; max-width: 900px; line-height: 1.6; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 24px; margin-bottom: 30px; }
        .stat-card { background: var(--white); padding: 22px 24px; border-radius: 12px; border: 1px solid var(--border); }
        .stat-card h3 { font-size: 13px; font-weight: 500; color: var(--text-gray); margin-bottom: 8px; }
        .stat-card .value { font-size: 28px; font-weight: 600; }
        .stat-card .subtext { font-size: 13px; color: var(--text-gray); margin-top: 4px; }
        .panel { background: var(--white); border-radius: 12px; border: 1px solid var(--border); padding: 24px; margin-bottom: 24px; }
        .panel-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
        .panel-header h2 { font-size: 16px; font-weight: 600; }
        .panel-header p, .note { font-size: 13px; color: var(--text-gray); line-height: 1.6; max-width: 880px; }
        .tag { display: inline-block; font-size: 11px; font-weight: 600; letter-spacing: .3px; text-transform: uppercase; color: var(--text-gray); border: 1px solid var(--border); border-radius: 999px; padding: 2px 9px; margin-left: 8px; vertical-align: middle; }
        .table-wrap { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
        th { text-align: left; font-weight: 600; color: var(--text-gray); font-size: 12px; padding: 10px 12px; border-bottom: 1px solid var(--border); white-space: nowrap; }
        td { padding: 10px 12px; border-bottom: 1px solid var(--border); vertical-align: top; }
        td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
        tr.chosen td { background: #fff7f3; }
        tr.total td { font-weight: 600; background: var(--bg-gray); }
        tr.subtotal td { color: var(--text-gray); }
        .badge { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 12px; font-weight: 600; }
        .badge.spam { background: #fef2f2; color: #b91c1c; }
        .badge.legitimate { background: #ecfdf5; color: #047857; }
        .badge.deployed { background: #fff1ea; color: #c2410c; }
        .meter { display: inline-block; width: 70px; height: 6px; border-radius: 3px; background: #dbe8f8; vertical-align: middle; margin-right: 8px; overflow: hidden; }
        .meter i { display: block; height: 100%; background: var(--series); }
        .controls { display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 18px; }
        .controls label { font-size: 12px; font-weight: 500; color: var(--text-gray); display: flex; flex-direction: column; gap: 5px; }
        select { font: inherit; font-size: 13.5px; padding: 7px 28px 7px 10px; border: 1px solid var(--border); border-radius: 8px; background: var(--white); color: var(--text-dark); }
        .charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 24px; margin-bottom: 18px; }
        .chart-box { position: relative; height: 240px; }
        .chart-title { font-size: 13px; font-weight: 600; margin-bottom: 8px; }
        .two-col { display: grid; grid-template-columns: repeat(auto-fit, minmax(440px, 1fr)); gap: 24px; }
        pre { background: var(--bg-gray); border: 1px solid var(--border); border-radius: 8px; padding: 14px; font-size: 12.5px; line-height: 1.5; overflow-x: auto; }
        .terms span { display: inline-block; background: var(--bg-gray); border: 1px solid var(--border); border-radius: 6px; padding: 1px 7px; margin: 0 4px 4px 0; font-size: 12px; }
        .msg { color: var(--text-gray); max-width: 420px; overflow-wrap: anywhere; }
        .empty { color: var(--text-gray); font-size: 13.5px; padding: 14px 0; }
        .warn { background: #fffbeb; border: 1px solid #fde68a; color: #92400e; border-radius: 8px; padding: 12px 14px; font-size: 13.5px; margin-bottom: 24px; }
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
            <a href="dashboard.php" class="nav-link">Dashboard</a>
            <a href="mining.php" class="nav-link active">Data Mining</a>
            <a href="index.php" class="nav-link">Form</a>
            <a href="about.php" class="nav-link">About</a>
        </nav>
    </header>

    <div class="main-content">
        <div class="page-header">
            <h1>Data Mining</h1>
            <p>Patterns mined from five years of submissions, and how they score live traffic. The honeypot catches a
               sender only if its bot fills hidden fields; the mined text model looks at what the message says.</p>
        </div>

<?php if (!$ready): ?>
        <div class="warn">The mined models are missing. Run the notebook and then <code>python tools/sync_artifacts.py</code>
            to copy its exports into <code>ml_service/artifacts/</code>.</div>
<?php else: ?>
        <div id="service-warning" class="warn" style="display:none">No submission has a model score yet. Start the
            scoring service with <code>python ml_service/app.py</code>; until then FormTrap scores with its rules alone.</div>

        <div class="stats-grid">
            <div class="stat-card">
                <h3>Submissions scored by the model</h3>
                <div class="value" id="stat-scored">&ndash;</div>
                <div class="subtext"><span id="stat-unscored">&ndash;</span> without a score</div>
            </div>
            <div class="stat-card">
                <h3>Flagged as spam</h3>
                <div class="value" id="stat-spam">&ndash;</div>
                <div class="subtext"><span id="stat-spam-share">&ndash;</span> of scored submissions</div>
            </div>
            <div class="stat-card">
                <h3>Deployed model</h3>
                <div class="value" style="font-size:20px; line-height:1.4"><?= e($card['model']) ?></div>
                <div class="subtext">balanced accuracy <?= number_format($card['cv']['balanced_acc'], 3) ?> in 5-fold cross-validation</div>
            </div>
            <div class="stat-card">
                <h3>Campaigns found</h3>
                <div class="value"><?= (int) $clusters['k'] ?></div>
                <div class="subtext">K-means on <?= number_format($metrics['clustering']['templates_clustered']) ?> message templates</div>
            </div>
        </div>

        <!-- OLAP -->
        <div class="panel">
            <div class="panel-header">
                <div>
                    <h2>OLAP explorer <span class="tag">descriptive</span></h2>
                    <p>Roll up or drill down along time, slice one year, dice by the model's label, and add a second
                       dimension. Totals come from <code>GROUP BY &hellip; WITH ROLLUP</code>.</p>
                </div>
            </div>
            <div class="controls">
                <label>Time level (roll-up / drill-down)
                    <select id="olap-level"><option value="year">Year</option><option value="quarter">Quarter</option><option value="month">Month</option></select>
                </label>
                <label>Slice: year
                    <select id="olap-year"><option value="">All years</option></select>
                </label>
                <label>Dice: model label
                    <select id="olap-label"><option value="">All</option><option value="spam">Spam</option><option value="legitimate">Legitimate</option></select>
                </label>
                <label>Second dimension
                    <select id="olap-by"><option value="none">None</option><option value="label">Model label</option><option value="campaign">Campaign</option><option value="risk">Risk level</option></select>
                </label>
            </div>
            <div class="charts" id="olap-charts">
                <div><div class="chart-title">Submissions</div><div class="chart-box"><canvas id="chart-volume"></canvas></div></div>
                <div><div class="chart-title">Honeypot hit rate (%)</div><div class="chart-box"><canvas id="chart-rate"></canvas></div></div>
            </div>
            <div class="table-wrap" id="olap-table"><div class="empty">Loading&hellip;</div></div>
            <p class="note" style="margin-top:12px">Hit rate = honeypot hits &divide; submissions with a recorded honeypot outcome.
                Imported rows from <?= e(substr($metrics['window']['start'], 0, 10)) ?> to <?= e(substr($metrics['window']['end'], 0, 10)) ?>
                have no outcome: the form had no honeypot field in that period (<?= number_format($metrics['window']['rows']) ?> submissions), so they count as
                submissions and not toward the hit rate.</p>
        </div>

        <!-- Models -->
        <div class="panel">
            <div class="panel-header">
                <div>
                    <h2>Spam versus legitimate: model comparison <span class="tag">supervised</span></h2>
                    <p>All word-based models score alike on data like their training data. The last two columns test
                       them outside it, and those decided which model is deployed.</p>
                </div>
            </div>
            <div class="table-wrap">
                <table>
                    <thead><tr>
                        <th>Model</th><th class="num">Balanced accuracy</th><th class="num">F1</th><th class="num">AUC</th>
                        <th class="num">Same-source AUC</th><th class="num">Genuine messages flagged (of 40)</th><th class="num">Size (KB)</th>
                    </tr></thead>
                    <tbody>
<?php foreach ($models as $m): $chosen = $m['model'] === $card['model']; ?>
                        <tr<?= $chosen ? ' class="chosen"' : '' ?>>
                            <td><?= e($m['model']) ?><?= $chosen ? ' <span class="badge deployed">deployed</span>' : '' ?></td>
                            <td class="num"><?= number_format($m['balanced_acc'], 3) ?></td>
                            <td class="num"><?= number_format($m['f1'], 3) ?></td>
                            <td class="num"><?= number_format($m['auc'], 3) ?></td>
                            <td class="num"><?= $m['cross'] ? number_format($m['cross']['same-source AUC'], 3) : '&ndash;' ?></td>
                            <td class="num"><?= $m['cross'] ? (int) $m['cross']['contact-form legitimate flagged (false positives of 40)'] : '&ndash;' ?></td>
                            <td class="num"><?= number_format($m['size_kb']) ?></td>
                        </tr>
<?php endforeach; ?>
                    </tbody>
                </table>
            </div>
            <p class="note" style="margin-top:12px"><?= e($card['limits']) ?></p>
        </div>

        <!-- Campaigns -->
        <div class="panel">
            <div class="panel-header">
                <div>
                    <h2>Spam campaigns <span class="tag">unsupervised</span></h2>
                    <p>K-means groups of message templates, named by their most characteristic words. A new submission is
                       assigned to the nearest campaign. The honeypot hit rate differs sharply from one campaign to the next.</p>
                </div>
            </div>
            <div class="table-wrap">
                <table>
                    <thead><tr><th>Campaign</th><th class="num">In the dataset</th><th class="num">Honeypot hit rate</th><th class="num">Scored here</th><th>Example</th></tr></thead>
                    <tbody>
<?php foreach ($clusters['campaigns'] as $c): ?>
                        <tr>
                            <td><?= e($c['label']) ?></td>
                            <td class="num"><?= number_format($c['submissions']) ?></td>
                            <td class="num"><?= pct($c['honeypot_rate']) ?></td>
                            <td class="num" data-campaign="<?= (int) $c['campaign'] ?>">&ndash;</td>
                            <td class="msg"><?= e($c['example']) ?></td>
                        </tr>
<?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Rules -->
        <div class="two-col">
            <div class="panel">
                <div class="panel-header">
                    <div>
                        <h2>Mined association rules <span class="tag">Apriori</span></h2>
                        <p>Minimum support <?= e($rules['min_support']) ?>, minimum confidence <?= e($rules['min_confidence']) ?>.
                           Each rule comes with a measured confidence.</p>
                    </div>
                </div>
                <div class="table-wrap">
                    <table>
                        <thead><tr><th>If</th><th>Then</th><th class="num">Support</th><th class="num">Confidence</th><th class="num">Lift</th></tr></thead>
                        <tbody>
<?php foreach (array_merge($rules['honeypot_filled'], $rules['honeypot_empty']) as $r): ?>
                            <tr>
                                <td><?= e($r['antecedent']) ?></td>
                                <td><?= e($r['consequent']) ?></td>
                                <td class="num"><?= pct($r['support']) ?></td>
                                <td class="num"><?= pct($r['confidence']) ?></td>
                                <td class="num"><?= number_format($r['lift'], 2) ?></td>
                            </tr>
<?php endforeach; ?>
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="panel">
                <div class="panel-header">
                    <div>
                        <h2>Scoring rules in use</h2>
                        <p>The hand-written rules and their hand-picked weights, with the model's rule among them.</p>
                    </div>
                </div>
                <div class="table-wrap" id="rules-table"><div class="empty">Loading&hellip;</div></div>
            </div>
        </div>

        <div class="panel">
            <div class="panel-header">
                <div>
                    <h2>Decision tree, depth 3 <span class="tag">supervised</span></h2>
                    <p>Predicts whether a sender fills the honeypot (class 1) from the submission's features.
                       Count features are on a log(1 + x) scale.</p>
                </div>
            </div>
            <pre><?= e($rules['decision_tree_depth3']) ?></pre>
        </div>

        <!-- Live predictions -->
        <div class="panel">
            <div class="panel-header">
                <div>
                    <h2>Latest scored submissions</h2>
                    <p>Spam probability, the words that pushed it up, and the campaign a spam message resembles.</p>
                </div>
            </div>
            <div class="table-wrap" id="recent-table"><div class="empty">Loading&hellip;</div></div>
        </div>
<?php endif; ?>
    </div>

<?php if ($ready): ?>
    <script>
        Chart.defaults.font.family = "'Inter', system-ui, -apple-system, sans-serif";
        Chart.defaults.color = '#6b7280';
        const GRID = '#e5e7eb', SERIES = '#2a78d6';
        let volumeChart = null, rateChart = null;

        function esc(text) {
            const div = document.createElement('div');
            div.textContent = text == null ? '' : String(text);
            return div.innerHTML;
        }
        const num = v => Number(v).toLocaleString();
        const pct = (v, d = 0) => v == null ? '–' : (v * 100).toFixed(d) + '%';

        async function loadSummary() {
            const data = await (await fetch('api_stats.php?action=ml_summary')).json();
            const t = data.totals;
            document.getElementById('stat-scored').textContent = num(t.scored);
            document.getElementById('stat-unscored').textContent = num(t.unscored);
            document.getElementById('stat-spam').textContent = num(t.spam);
            document.getElementById('stat-spam-share').textContent = t.scored > 0 ? pct(t.spam / t.scored) : '–';
            document.getElementById('service-warning').style.display = Number(t.scored) === 0 ? 'block' : 'none';

            data.campaigns.forEach(c => {
                const cell = document.querySelector(`[data-campaign="${c.campaign_id}"]`);
                if (cell) cell.textContent = num(c.submissions);
            });

            document.getElementById('rules-table').innerHTML = `<table>
                <thead><tr><th>Rule</th><th>Checks</th><th class="num">Weight</th></tr></thead><tbody>` +
                data.rules.map(r => `<tr${r.condition_type === 'ml_score' ? ' class="chosen"' : ''}>
                    <td>${esc(r.name)}</td><td>${esc(r.description)}</td><td class="num">${esc(r.weight)}</td></tr>`).join('') +
                '</tbody></table>';

            const recent = document.getElementById('recent-table');
            if (!data.recent.length) {
                recent.innerHTML = '<div class="empty">Nothing scored yet.</div>';
                return;
            }
            recent.innerHTML = `<table>
                <thead><tr><th>#</th><th>Received</th><th>Message</th><th>Spam probability</th><th>Words pushing toward spam</th>
                <th>Campaign</th><th class="num">Rule score</th></tr></thead><tbody>` +
                data.recent.map(r => {
                    const p = Number(r.spam_probability);
                    return `<tr>
                        <td>${esc(r.id)}</td>
                        <td style="white-space:nowrap">${esc(r.created_at)}</td>
                        <td class="msg">${esc(r.message)}</td>
                        <td style="white-space:nowrap"><span class="meter"><i style="width:${(p * 100).toFixed(0)}%"></i></span>${p.toFixed(2)}
                            <span class="badge ${esc(r.label)}">${esc(r.label)}</span></td>
                        <td class="terms">${(r.top_terms || []).map(t => `<span>${esc(t.term)}</span>`).join('')}</td>
                        <td>${r.label === 'spam' ? esc(r.campaign_label) : '–'}</td>
                        <td class="num">${r.score == null ? '–' : esc(r.score) + ' (' + esc(r.risk_level) + ')'}</td>
                    </tr>`;
                }).join('') + '</tbody></table>';
        }

        function drawCharts(rows) {
            const labels = rows.map(r => r.period);
            const common = {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { x: { grid: { display: false } }, y: { beginAtZero: true, grid: { color: GRID }, border: { display: false } } },
            };
            if (volumeChart) volumeChart.destroy();
            if (rateChart) rateChart.destroy();
            volumeChart = new Chart(document.getElementById('chart-volume'), {
                type: 'bar',
                data: { labels, datasets: [{ label: 'Submissions', data: rows.map(r => r.submissions), backgroundColor: SERIES, maxBarThickness: 24, borderRadius: 4 }] },
                options: common,
            });
            rateChart = new Chart(document.getElementById('chart-rate'), {
                type: 'line',
                data: { labels, datasets: [{ label: 'Honeypot hit rate (%)', data: rows.map(r => r.hit_rate == null ? null : +(r.hit_rate * 100).toFixed(1)),
                    borderColor: SERIES, backgroundColor: SERIES, borderWidth: 2, pointRadius: 4, pointBorderColor: '#fff', pointBorderWidth: 2, spanGaps: false }] },
                options: { ...common, scales: { ...common.scales, y: { ...common.scales.y, max: 100 } } },
            });
        }

        async function loadOlap() {
            const q = new URLSearchParams({
                action: 'olap',
                level: document.getElementById('olap-level').value,
                year: document.getElementById('olap-year').value,
                label: document.getElementById('olap-label').value,
                by: document.getElementById('olap-by').value,
            });
            const data = await (await fetch('api_stats.php?' + q)).json();

            const yearSelect = document.getElementById('olap-year');
            if (yearSelect.options.length === 1) {
                data.years.forEach(y => yearSelect.add(new Option(y, y)));
            }

            const grouped = data.by !== 'none';
            const periods = data.rows.filter(r => !r.is_total && (grouped ? r.is_subtotal : true));
            document.getElementById('olap-charts').style.display = periods.length ? 'grid' : 'none';
            if (periods.length) drawCharts(periods);

            const table = document.getElementById('olap-table');
            if (!data.rows.length) {
                table.innerHTML = '<div class="empty">No submissions match this selection.</div>';
                return;
            }
            table.innerHTML = `<table>
                <thead><tr><th>Period</th>${grouped ? '<th>' + esc(document.getElementById('olap-by').selectedOptions[0].text) + '</th>' : ''}
                <th class="num">Submissions</th><th class="num">Honeypot recorded</th><th class="num">Honeypot hits</th>
                <th class="num">Hit rate</th><th class="num">Flagged by model</th><th class="num">Share flagged</th></tr></thead><tbody>` +
                data.rows.map(r => `<tr class="${r.is_total ? 'total' : r.is_subtotal ? 'subtotal' : ''}">
                    <td>${r.is_total ? 'All periods' : esc(r.period)}</td>
                    ${grouped ? '<td>' + (r.is_total ? '' : r.is_subtotal ? 'subtotal' : esc(r.grp)) + '</td>' : ''}
                    <td class="num">${num(r.submissions)}</td><td class="num">${num(r.labelled)}</td>
                    <td class="num">${num(r.honeypot_hits)}</td><td class="num">${pct(r.hit_rate)}</td>
                    <td class="num">${num(r.ml_spam)}</td><td class="num">${pct(r.ml_spam_rate)}</td>
                </tr>`).join('') + '</tbody></table>';
        }

        ['olap-level', 'olap-year', 'olap-label', 'olap-by'].forEach(id => document.getElementById(id).addEventListener('change', loadOlap));
        loadSummary();
        loadOlap();
    </script>
<?php endif; ?>
</body>
</html>
