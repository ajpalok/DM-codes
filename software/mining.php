<?php
/**
 * Analysis view: every method used in the data-mining study, with its type of learning, why it was needed,
 * its results and what they mean. Numbers come from the notebook's exports in ml_service/artifacts/,
 * figures from assets/figures/, and live figures from api_stats.php.
 */

function artifact($name) {
    $path = __DIR__ . '/ml_service/artifacts/' . $name;
    return file_exists($path) ? json_decode(file_get_contents($path), true) : null;
}

$m = artifact('metrics.json');
$card = artifact('model_card.json');
$clusters = artifact('clusters.json');
$rules = artifact('rules.json');
$ready = $m && $card && $clusters && $rules;

function e($text) {
    return htmlspecialchars((string) $text, ENT_QUOTES, 'UTF-8');
}

function pct($value, $digits = 0) {
    return $value === null ? '&ndash;' : number_format($value * 100, $digits) . '%';
}

function f3($value) {
    return $value === null ? '&ndash;' : number_format($value, 3);
}

function n($value) {
    return number_format($value);
}

function fig($file, $caption) {
    if (!file_exists(__DIR__ . '/assets/figures/' . $file)) {
        return;
    }
    echo '<figure><img src="assets/figures/' . e($file) . '" alt="' . e($caption) . '" loading="lazy">'
        . '<figcaption>' . e($caption) . '</figcaption></figure>';
}

function head($id, $number, $title, $type, $why) {
    echo '<header class="sec-head" id="' . e($id) . '"><div class="sec-num">' . e($number) . '</div><div>'
        . '<h2>' . e($title) . ' <span class="tag tag-' . e(strtolower(strtok($type, ' :'))) . '">' . e($type) . '</span></h2>'
        . '<p class="why"><strong>Why it is needed here.</strong> ' . e($why) . '</p></div></header>';
}

$sections = [
    'findings' => 'Findings',
    'data' => 'Data and label audit',
    'similarity' => 'Similarity',
    'olap' => 'OLAP',
    'apriori' => 'Association rules',
    'pca' => 'PCA',
    'clustering' => 'Clustering',
    'task-a' => 'Task A: honeypot evasion',
    'task-b' => 'Task B: spam vs legitimate',
    'verdict' => 'Which algorithm, which job',
    'trend' => 'Regression',
    'live' => 'Live scoring',
];

if ($ready) {
    $d = $m['data'];
    $w = $m['window'];
    $a = $m['task_a'];
    $b = $m['task_b'];
    $c = $m['clustering'];
    $cvA = array_column($a['cv'], null, 'model');
    $tsA = array_column($a['time_split'], null, 'model');
    $cross = array_column($b['cross_source'], null, 'model');
    $FP = 'contact-form legitimate flagged (false positives of 40)';
    $lrA = 'Logistic regression';
    $years = $m['olap']['by_year'];
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analysis - FormTrap</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        :root {
            --primary: #e35f27;
            --ink: #1b1a17;
            --ink-2: #57544d;
            --ink-3: #85817a;
            --page: #faf9f7;
            --surface: #fffefc;
            --rule: #e6e3dd;
            --wash: #f3f1ec;
            --series: #2a78d6;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html { scroll-behavior: smooth; scroll-padding-top: 90px; }
        body { font-family: 'Inter', system-ui, -apple-system, sans-serif; background: var(--page); color: var(--ink); font-size: 15px; line-height: 1.6; }
        .site-header { background: var(--surface); padding: 0 40px; height: 70px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--rule); position: sticky; top: 0; z-index: 50; }
        .logo { font-weight: 700; font-size: 20px; color: var(--ink); text-decoration: none; display: flex; align-items: center; letter-spacing: -0.5px; }
        .logo span { color: var(--primary); }
        .nav-link { color: var(--ink-2); text-decoration: none; font-weight: 500; font-size: 14px; padding: 8px 16px; border-radius: 6px; }
        .nav-link:hover, .nav-link.active { color: var(--primary); background: #fdf0ea; }

        .layout { display: grid; grid-template-columns: 230px minmax(0, 1fr); gap: 56px; max-width: 1320px; margin: 0 auto; padding: 40px; }
        .toc { position: sticky; top: 100px; align-self: start; max-height: calc(100vh - 120px); overflow-y: auto; }
        .toc-title { font-size: 12px; font-weight: 600; color: var(--ink-3); letter-spacing: .4px; text-transform: uppercase; margin-bottom: 10px; }
        .toc a { display: block; padding: 6px 12px; border-radius: 6px; color: var(--ink-2); text-decoration: none; font-size: 14px; }
        .toc a:hover { background: var(--wash); color: var(--ink); }
        .toc a.current { background: #fdf0ea; color: #b8431a; font-weight: 600; }
        .toc a:focus-visible, .nav-link:focus-visible, select:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }

        main { min-width: 0; }
        h1 { font-size: 28px; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 8px; }
        .lead { color: var(--ink-2); max-width: 72ch; margin-bottom: 8px; }
        section { padding: 44px 0 8px; border-top: 1px solid var(--rule); margin-top: 44px; }
        section:first-of-type { border-top: 0; margin-top: 12px; padding-top: 20px; }
        .sec-head { display: grid; grid-template-columns: 44px 1fr; gap: 6px; margin-bottom: 22px; }
        .sec-num { font-size: 15px; font-weight: 600; color: var(--ink-3); padding-top: 5px; font-variant-numeric: tabular-nums; }
        h2 { font-size: 21px; font-weight: 650; letter-spacing: -0.2px; }
        h3 { font-size: 15px; font-weight: 600; margin: 30px 0 10px; }
        p { max-width: 74ch; }
        .why { color: var(--ink-2); margin-top: 6px; }
        .tag { display: inline-block; font-size: 11px; font-weight: 600; letter-spacing: .3px; text-transform: uppercase; border-radius: 999px; padding: 2px 10px; margin-left: 8px; vertical-align: 3px; border: 1px solid var(--rule); color: var(--ink-2); background: var(--surface); }
        .tag-unsupervised { background: #eaf2fc; border-color: #c9dcf5; color: #1c5cab; }
        .tag-supervised { background: #fdf0ea; border-color: #f5d2c1; color: #b8431a; }
        .body { margin-left: 50px; }
        .analysis { margin: 14px 0 6px; padding-left: 20px; max-width: 76ch; }
        .analysis li { margin-bottom: 8px; }
        .analysis li::marker { color: var(--ink-3); }

        .facts { display: flex; flex-wrap: wrap; gap: 10px 36px; margin: 6px 0 18px; }
        .facts div { min-width: 120px; }
        .facts dt { font-size: 12.5px; color: var(--ink-3); }
        .facts dd { font-size: 20px; font-weight: 600; font-variant-numeric: tabular-nums; }
        .findings { counter-reset: finding; list-style: none; max-width: 78ch; }
        .findings li { counter-increment: finding; display: grid; grid-template-columns: 34px 1fr; padding: 12px 0; border-bottom: 1px solid var(--rule); }
        .findings li::before { content: counter(finding); font-weight: 600; color: var(--primary); }
        .findings li:last-child { border-bottom: 0; }

        figure { margin: 18px 0 8px; background: var(--surface); border: 1px solid var(--rule); border-radius: 10px; padding: 16px; max-width: 900px; }
        figure img { display: block; width: 100%; height: auto; }
        figcaption { font-size: 13px; color: var(--ink-2); margin-top: 10px; }
        .pair { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 16px; max-width: 1000px; }
        .pair figure { margin: 8px 0; }

        .table-wrap { overflow-x: auto; margin: 10px 0 6px; background: var(--surface); border: 1px solid var(--rule); border-radius: 10px; }
        table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
        th { text-align: left; font-weight: 600; color: var(--ink-2); font-size: 12px; padding: 10px 14px; border-bottom: 1px solid var(--rule); white-space: nowrap; background: var(--wash); }
        td { padding: 9px 14px; border-bottom: 1px solid var(--rule); vertical-align: top; }
        tr:last-child td { border-bottom: 0; }
        td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
        tr.chosen td { background: #fff6f1; font-weight: 500; }
        tr.total td { font-weight: 600; background: var(--wash); }
        tr.subtotal td { color: var(--ink-2); }
        tr.base td { color: var(--ink-3); }
        .best { font-weight: 700; }
        .note { font-size: 13px; color: var(--ink-2); margin-top: 8px; }
        .badge { display: inline-block; padding: 1px 9px; border-radius: 999px; font-size: 12px; font-weight: 600; }
        .badge.spam { background: #fdecec; color: #b42318; }
        .badge.legitimate { background: #e8f6ee; color: #0a7a45; }
        .badge.deployed { background: #fdf0ea; color: #b8431a; }
        .meter { display: inline-block; width: 70px; height: 6px; border-radius: 3px; background: #dbe8f8; vertical-align: middle; margin-right: 8px; overflow: hidden; }
        .meter i { display: block; height: 100%; background: var(--series); }
        .controls { display: flex; gap: 14px; flex-wrap: wrap; margin: 6px 0 16px; }
        .controls label { font-size: 12px; font-weight: 500; color: var(--ink-2); display: flex; flex-direction: column; gap: 5px; }
        select { font: inherit; font-size: 13.5px; padding: 7px 28px 7px 10px; border: 1px solid var(--rule); border-radius: 8px; background: var(--surface); color: var(--ink); }
        .charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 16px; margin-bottom: 14px; }
        .chart-card { background: var(--surface); border: 1px solid var(--rule); border-radius: 10px; padding: 14px 16px; }
        .chart-box { position: relative; height: 230px; }
        .chart-title { font-size: 13px; font-weight: 600; margin-bottom: 8px; }
        pre { background: var(--surface); border: 1px solid var(--rule); border-radius: 10px; padding: 14px; font-size: 12.5px; line-height: 1.5; overflow-x: auto; max-width: 900px; }
        code { font-size: 0.92em; background: var(--wash); padding: 1px 5px; border-radius: 4px; }
        .terms span { display: inline-block; background: var(--wash); border-radius: 6px; padding: 1px 7px; margin: 0 4px 4px 0; font-size: 12px; }
        .msg { color: var(--ink-2); max-width: 420px; overflow-wrap: anywhere; }
        .empty { color: var(--ink-2); font-size: 13.5px; padding: 14px; }
        .warn { background: #fff8e6; border: 1px solid #f3dc9c; color: #7a5200; border-radius: 8px; padding: 12px 14px; font-size: 13.5px; margin: 16px 0; max-width: 76ch; }

        @media (max-width: 960px) {
            .layout { grid-template-columns: 1fr; gap: 20px; padding: 24px 18px; }
            .toc { position: static; max-height: none; display: flex; flex-wrap: wrap; gap: 4px; }
            .toc-title { width: 100%; }
            .body { margin-left: 0; }
            .sec-head { grid-template-columns: 30px 1fr; }
            .site-header { padding: 0 18px; }
        }
        @media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }
    </style>
</head>
<body>
    <header class="site-header">
        <a href="index.php" class="logo">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-right:8px;" aria-hidden="true">
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

<?php if (!$ready): ?>
    <div class="layout" style="grid-template-columns: 1fr"><main>
        <h1>Data mining analysis</h1>
        <div class="warn">The analysis results are missing. Run <code>npm run notebook</code> in the project folder: it executes
            the notebook and copies its exports into <code>ml_service/artifacts/</code> and <code>assets/figures/</code>.</div>
    </main></div>
<?php else: ?>
    <div class="layout">
        <nav class="toc" aria-label="Sections">
            <div class="toc-title">Analysis</div>
<?php foreach ($sections as $id => $label): ?>
            <a href="#<?= e($id) ?>"><?= e($label) ?></a>
<?php endforeach; ?>
        </nav>

        <main>
            <h1>Data mining analysis</h1>
            <p class="lead">What was mined from <?= n($d['raw rows']) ?> contact-form submissions received between 2020 and 2025,
                method by method: the type of learning, why the method was needed, what it found and what that means.
                The last section shows the result at work on live submissions.</p>

            <!-- ============================================================ Findings -->
            <section>
                <header class="sec-head" id="findings"><div class="sec-num">0</div><div><h2>Findings</h2></div></header>
                <div class="body">
                    <ol class="findings">
                        <li><span><strong>The honeypot is not dependable.</strong> It caught <?= pct($years['2022']['hit_rate']) ?> of submissions in 2022,
                            <?= pct($m['olap']['by_quarter']["('2023', '4')"]['hit_rate']) ?> in the last quarter of 2023 and <?= pct($years['2025']['hit_rate']) ?> in spring 2025.</span></li>
                        <li><span><strong>Checking the label mattered.</strong> <?= n($w['rows']) ?> consecutive submissions over <?= n($w['days']) ?> days never fill the
                            honeypot, because the form had no honeypot field then. They are treated as unlabelled.</span></li>
                        <li><span><strong>Honeypot behaviour belongs to the campaign.</strong> One campaign fills the hidden field
                            <?= pct($m['apriori']['top_filled'][0]['confidence']) ?> of the time; a one-line multilingual enquiry leaves it empty
                            <?= pct($m['apriori']['top_empty'][1]['confidence']) ?> of the time.</span></li>
                        <li><span><strong>Evasion is moderately predictable now and poorly predictable later.</strong> Balanced accuracy
                            <?= f3($cvA[$lrA]['balanced_acc']) ?> in cross-validation, <?= f3($tsA[$lrA]['balanced_acc']) ?> on the following period, where only logistic regression holds up.</span></li>
                        <li><span><strong>Spam-versus-legitimate scores look excellent and are partly an artefact.</strong> Every model reaches about 0.96,
                            yet message length alone reaches <?= f3(array_column($b['cv'], null, 'model')['Baseline: message length only']['balanced_acc']) ?>. Checks outside the corpus chose the deployed model.</span></li>
                        <li><span><strong>The two defences share a blind spot.</strong> The text model misses short spam (median
                            <?= n($b['errors']['median length, missed spam']) ?> characters), which is also what evades the honeypot. The mined rules recognise it by shape.</span></li>
                    </ol>
                </div>
            </section>

            <!-- ============================================================ Data -->
            <section>
                <?php head('data', '1', 'Data and label audit', 'Preprocessing', 'Every later result depends on clean rows and on a label that means what it says.'); ?>
                <div class="body">
                    <dl class="facts">
                        <div><dt>Raw submissions</dt><dd><?= n($d['raw rows']) ?></dd></div>
                        <div><dt>After cleaning</dt><dd><?= n($d['rows after cleaning']) ?></dd></div>
                        <div><dt>Distinct templates</dt><dd><?= n($d['distinct message templates']) ?></dd></div>
                        <div><dt>Usable labels</dt><dd><?= n($d['label used in this notebook']) ?></dd></div>
                        <div><dt>Features per row</dt><dd><?= n($a['features']) ?></dd></div>
                    </dl>
                    <ul class="analysis">
                        <li><strong>Missing values are behaviour, not error.</strong> A skipped field gets a presence flag; nothing is imputed.</li>
                        <li><strong>Redundant columns.</strong> First, middle and last name held the same string in <?= n($d['rows where First = Middle = Last name (redundant columns)']) ?> rows and were merged.</li>
                        <li><strong>Duplicates.</strong> Exact duplicate rows were removed. Repeated templates were kept and counted:
                            <?= n($d["rows whose message repeats another row's template"]) ?> submissions repeat another one's template.</li>
                        <li><strong>Scaling.</strong> Count features are skewed, so they pass through log(1 + x) and are standardized on training folds only.</li>
                        <li><strong>Anonymization.</strong> Names, e-mail addresses and phone numbers are removed; inside messages they are replaced by tokens.</li>
                    </ul>
                    <?php fig('fig_missing_raw.png', 'Share of missing values per column of the raw export.'); ?>

                    <h3>The window without a honeypot</h3>
                    <p>Sorting submissions by time and measuring runs with an empty honeypot shows one run of <?= n($w['rows']) ?> submissions over
                        <?= n($w['days']) ?> days (<?= e(substr($w['start'], 0, 10)) ?> to <?= e(substr($w['end'], 0, 10)) ?>). The next longest is
                        <?= n($w['second_longest_rows']) ?> submissions in <?= n($w['second_longest_days']) ?> days.</p>
                    <div class="table-wrap"><table>
                        <thead><tr><th>Evidence</th><th class="num">Value</th></tr></thead>
                        <tbody>
                            <tr><td>Honeypot filled in the 90 days before the run</td><td class="num"><?= pct($w['hit_rate_90d_before']) ?></td></tr>
                            <tr><td>Honeypot filled inside the run</td><td class="num">0%</td></tr>
                            <tr><td>Honeypot filled in the 90 days after the run</td><td class="num"><?= pct($w['hit_rate_90d_after']) ?></td></tr>
                            <tr><td>Templates seen on both sides: hit rate outside the run</td><td class="num"><?= pct($w['shared_hit_rate_outside'], 1) ?></td></tr>
                            <tr><td>The same templates inside the run (<?= n($w['shared_rows_inside']) ?> submissions)</td><td class="num">0</td></tr>
                            <tr><td>Chance of that under unchanged behaviour</td><td class="num"><?= sprintf('%.0e', $w['chance_of_zero']) ?></td></tr>
                        </tbody>
                    </table></div>
                    <p class="note">The site owner confirmed that the form had no honeypot field in this period. Those rows keep their place in the
                        unsupervised analyses and leave every analysis that uses the label, which leaves <?= n($d['of which honeypot filled']) ?> filled
                        and <?= n($d['of which honeypot left empty']) ?> empty.</p>
                </div>
            </section>

            <!-- ============================================================ Similarity -->
            <section>
                <?php head('similarity', '2', 'Distance and similarity', 'Descriptive', 'Campaign discovery rests on one question: is this message a variant of that one?'); ?>
                <div class="body">
                    <p>Euclidean and Minkowski distance are used on the numeric features, the Jaccard coefficient on the binary flags (shared
                        absences say nothing about spam, so simple matching is misleading), and cosine similarity on TF-IDF text vectors.</p>
                    <dl class="facts">
<?php foreach ($m['similarity']['near_duplicate_share'] as $threshold => $share): ?>
                        <div><dt>Templates with a twin at cosine <?= e($threshold) ?></dt><dd><?= pct($share) ?></dd></div>
<?php endforeach; ?>
                    </dl>
                    <?php fig('fig_nearest_similarity.png', 'Cosine similarity of each template to its nearest other template.'); ?>
                    <ul class="analysis"><li>Many "distinct" templates are small rewrites of one another. Campaigns exist beyond exact copies, which is why the templates are clustered below.</li></ul>
                </div>
            </section>

            <!-- ============================================================ OLAP -->
            <section>
                <?php head('olap', '3', 'OLAP', 'Descriptive', 'The operator asks how many, of what kind, when, and whether the honeypot caught them. Those are aggregates over dimensions, not row lookups.'); ?>
                <div class="body">
                    <?php fig('fig_honeypot_rate.png', 'Honeypot hit rate and submissions per quarter. The shaded band is the period in which the form had no honeypot field.'); ?>
                    <div class="table-wrap"><table>
                        <thead><tr><th>Year (roll-up)</th><th class="num">Submissions</th><th class="num">With a label</th><th class="num">Honeypot hit rate</th></tr></thead>
                        <tbody>
<?php foreach ($years as $year => $row): ?>
                            <tr><td><?= e($year) ?></td><td class="num"><?= n($row['submissions']) ?></td><td class="num"><?= n($row['labelled']) ?></td><td class="num"><?= pct($row['hit_rate'], 1) ?></td></tr>
<?php endforeach; ?>
                        </tbody>
                    </table></div>
                    <ul class="analysis">
                        <li><strong>Roll-up</strong> to years gives the headline: high through 2022, under half in 2023.</li>
                        <li><strong>Drill-down</strong> into 2023 shows when it fell: <?= pct($m['olap']['drill_2023_by_month']['1']) ?> in January,
                            <?= pct($m['olap']['drill_2023_by_month']['10']) ?> in October, <?= pct($m['olap']['drill_2023_by_month']['11']) ?> in November.</li>
                        <li><strong>Slice</strong> at that quarter: most submissions carry no topic keyword and almost none of them fills the field. A different kind of sender arrived.</li>
                        <li><strong>Dice</strong> by topic and script for 2022 against 2023: the rate changes for the same topic, so topic alone does not decide it.</li>
                    </ul>

                    <h3>Explore the cube on the live database</h3>
                    <p class="note">Totals come from <code>GROUP BY &hellip; WITH ROLLUP</code>. Rows from the period without a honeypot count as submissions and not toward the hit rate.</p>
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
                        <div class="chart-card"><div class="chart-title">Submissions</div><div class="chart-box"><canvas id="chart-volume"></canvas></div></div>
                        <div class="chart-card"><div class="chart-title">Honeypot hit rate (%)</div><div class="chart-box"><canvas id="chart-rate"></canvas></div></div>
                    </div>
                    <div class="table-wrap" id="olap-table"><div class="empty">Loading&hellip;</div></div>
                </div>
            </section>

            <!-- ============================================================ Apriori -->
            <section>
                <?php head('apriori', '4', 'Association rules (Apriori)', 'Unsupervised', "FormTrap's 14 scoring rules were written by hand. Apriori produces rules of the same if-then form from the data, with measured confidence instead of guessed weights."); ?>
                <div class="body">
                    <dl class="facts">
                        <div><dt>Transactions</dt><dd><?= n($m['apriori']['transactions']) ?></dd></div>
                        <div><dt>Items</dt><dd><?= n($m['apriori']['items']) ?></dd></div>
                        <div><dt>Min. support / confidence</dt><dd><?= e($m['apriori']['min_support']) ?> / <?= e($m['apriori']['min_confidence']) ?></dd></div>
                        <div><dt>Frequent itemsets</dt><dd><?= n($m['apriori']['frequent_itemsets']) ?></dd></div>
                        <div><dt>Rules</dt><dd><?= n($m['apriori']['rules']) ?></dd></div>
                    </dl>
                    <div class="table-wrap"><table>
                        <thead><tr><th>If</th><th>Then</th><th class="num">Support</th><th class="num">Confidence</th><th class="num">Lift</th></tr></thead>
                        <tbody>
<?php foreach (array_merge($rules['honeypot_filled'], $rules['honeypot_empty']) as $r): ?>
                            <tr><td><?= e($r['antecedent']) ?></td><td><?= e($r['consequent']) ?></td><td class="num"><?= pct($r['support']) ?></td>
                                <td class="num"><?= pct($r['confidence']) ?></td><td class="num"><?= number_format($r['lift'], 2) ?></td></tr>
<?php endforeach; ?>
                        </tbody>
                    </table></div>
                    <ul class="analysis">
                        <li><strong>Honeypot filled.</strong> A medium-length message about money is one campaign, the "financial robot" adverts. Its bot fills every field it finds, hidden ones included.</li>
                        <li><strong>Honeypot empty.</strong> A short message under a joined name such as <code>CarlosSob</code> is a single sentence, "Hi, I wanted to know your price", translated into dozens of languages. That sender skips the hidden field.</li>
                        <li><strong>Lift</strong> near 3 for the second group means these traits triple the chance of evasion against the base rate.</li>
                        <li>A rule reports co-occurrence in the period it was mined from, not cause.</li>
                    </ul>
                    <h3>Sensitivity to the thresholds</h3>
                    <div class="table-wrap"><table>
                        <thead><tr><th class="num">Min. support</th><th class="num">Frequent itemsets</th><th class="num">Largest itemset</th><th class="num">Rules, conf. 0.6</th><th class="num">Rules, conf. 0.8</th><th class="num">Rules, conf. 0.9</th></tr></thead>
                        <tbody>
<?php foreach ($m['apriori']['sensitivity'] as $s): ?>
                            <tr<?= $s['min support'] == $m['apriori']['min_support'] ? ' class="chosen"' : '' ?>><td class="num"><?= number_format($s['min support'], 2) ?></td><td class="num"><?= n($s['frequent itemsets']) ?></td><td class="num"><?= n($s['largest itemset']) ?></td>
                                <td class="num"><?= n($s['rules at confidence 0.6']) ?></td><td class="num"><?= n($s['rules at confidence 0.8']) ?></td><td class="num"><?= n($s['rules at confidence 0.9']) ?></td></tr>
<?php endforeach; ?>
                        </tbody>
                    </table></div>
                    <p class="note">The from-scratch implementation agrees with the mlxtend library on every frequent itemset and its support.</p>
                </div>
            </section>

            <!-- ============================================================ PCA -->
            <section>
                <?php head('pca', '5', 'Principal component analysis', 'Unsupervised', 'The features overlap. Redundant features are counted twice in every distance and make the covariance matrix impossible to invert.'); ?>
                <div class="body">
                    <dl class="facts">
                        <div><dt>Features</dt><dd><?= n($m['pca']['features']) ?></dd></div>
                        <div><dt>Components for 90% of variance</dt><dd><?= n($m['pca']['components_90']) ?></dd></div>
                        <div><dt>Components for 95%</dt><dd><?= n($m['pca']['components_95']) ?></dd></div>
                        <div><dt>PC 1 / PC 2</dt><dd><?= pct($m['pca']['pc1_ratio'], 1) ?> / <?= pct($m['pca']['pc2_ratio'], 1) ?></dd></div>
                    </dl>
                    <div class="pair">
                        <?php fig('fig_pca_variance.png', 'Cumulative variance explained by the principal components.'); ?>
                        <?php fig('fig_pca_scatter.png', 'Submissions on the first two components, by honeypot outcome.'); ?>
                    </div>
                    <?php fig('fig_correlation.png', 'Correlation between selected features: several measure the same thing.'); ?>
                    <ul class="analysis">
                        <li>Fewer than half of the dimensions carry 90% of the variance, which confirms the redundancy in the correlation matrix.</li>
                        <li>PC 1 separates "contact fields filled, short message" from "contact fields empty, long message".</li>
                        <li>The two honeypot outcomes occupy different regions and overlap: learnable, and not trivially so.</li>
                        <li><strong>Effect on models.</strong> KNN is unchanged by PCA (<?= f3($a['pca_effect']['KNN']['all 45 features']) ?> against <?= f3($a['pca_effect']['KNN']['PCA, 90% of variance']) ?>);
                            logistic regression loses a little (<?= f3($a['pca_effect'][$lrA]['all 45 features']) ?> against <?= f3($a['pca_effect'][$lrA]['PCA, 90% of variance']) ?>). PCA is applied only where it is required.</li>
                    </ul>
                </div>
            </section>

            <!-- ============================================================ Clustering -->
            <section>
                <?php head('clustering', '6', 'Clustering: K-means, K-medoids, EM', 'Unsupervised', 'Nobody labelled the campaigns. Grouping templates lets an operator review a handful of campaigns instead of thousands of messages.'); ?>
                <div class="body">
                    <dl class="facts">
                        <div><dt>Templates clustered</dt><dd><?= n($c['templates_clustered']) ?></dd></div>
                        <div><dt>Campaigns (k)</dt><dd><?= n($c['k']) ?></dd></div>
                        <div><dt>Silhouette, K-means</dt><dd><?= number_format($c['kmeans_silhouette'], 2) ?></dd></div>
                        <div><dt>Templates with no shared words</dt><dd><?= n($c['templates_no_vocabulary']) ?></dd></div>
                    </dl>
                    <?php fig('fig_kmeans_k.png', 'Choosing k: sum of squared errors (elbow) and silhouette coefficient.'); ?>
                    <?php fig('fig_campaigns.png', 'Campaigns found by K-means, with submissions and honeypot hit rate.'); ?>
                    <div class="table-wrap"><table>
                        <thead><tr><th>Campaign (top terms)</th><th class="num">Submissions</th><th class="num">Honeypot hit rate</th><th class="num">Scored here</th><th>Example</th></tr></thead>
                        <tbody>
<?php foreach ($clusters['campaigns'] as $camp): ?>
                            <tr><td><?= e($camp['label']) ?></td><td class="num"><?= n($camp['submissions']) ?></td><td class="num"><?= pct($camp['honeypot_rate']) ?></td>
                                <td class="num" data-campaign="<?= (int) $camp['campaign'] ?>">&ndash;</td><td class="msg"><?= e($camp['example']) ?></td></tr>
<?php endforeach; ?>
                        </tbody>
                    </table></div>
                    <h3>Three methods compared</h3>
                    <div class="table-wrap"><table>
                        <thead><tr><th>Method</th><th>What it adds</th><th class="num">Silhouette</th><th class="num">Agreement with K-means (ARI)</th></tr></thead>
                        <tbody>
                            <tr class="chosen"><td>K-means <span class="badge deployed">deployed</span></td><td>Centroids are cheap to apply to a new submission</td><td class="num"><?= number_format($c['kmedoids']['silhouette_kmeans_same_sample'], 2) ?></td><td class="num">&ndash;</td></tr>
                            <tr><td>K-medoids</td><td>The centre is a real message the operator can read</td><td class="num"><?= number_format($c['kmedoids']['silhouette_kmedoids'], 2) ?></td><td class="num"><?= number_format($c['kmedoids']['ari_vs_kmeans'], 2) ?></td></tr>
                            <tr><td>EM, Gaussian mixture</td><td>Soft membership: <?= pct($c['gmm']['share_soft_below_0.9']) ?> of templates are not clearly in one group</td><td class="num"><?= number_format($c['gmm']['silhouette'], 2) ?></td><td class="num"><?= number_format($c['gmm']['ari_vs_kmeans'], 2) ?></td></tr>
                        </tbody>
                    </table></div>
                    <div class="pair">
                        <?php fig('fig_em_length.png', 'EM in one dimension separates one-line messages from full adverts.'); ?>
                        <?php fig('fig_campaign_year.png', 'Each campaign has its own active period.'); ?>
                    </div>
                    <ul class="analysis">
                        <li><strong>No natural k.</strong> The error falls smoothly and the silhouette is still rising at the largest k tried. A silhouette near 0.25 means coarse topics, not crisp groups.</li>
                        <li><strong>Honeypot behaviour is a property of the campaign.</strong> Hit rates range from 0% to 100% across campaigns, which explains the swings in the OLAP view.</li>
                        <li><strong>What text clustering cannot do.</strong> The templates with no shared words include the multilingual price enquiry. No two versions share a word; Apriori caught that campaign by its shape.</li>
                        <li>EM splits messages into one-liners (about <?= n($c['em_1d']['typical_length'][0]) ?> characters) and full adverts (about <?= n($c['em_1d']['typical_length'][1]) ?>).</li>
                    </ul>
                </div>
            </section>

            <!-- ============================================================ Task A -->
            <section>
                <?php head('task-a', '7', 'Task A: predicting honeypot evasion', 'Supervised: classification', 'If the features of a submission predict who evades the honeypot, the operator knows which spam needs a second line of defence.'); ?>
                <div class="body">
                    <dl class="facts">
                        <div><dt>Labelled rows</dt><dd><?= n($a['rows']) ?></dd></div>
                        <div><dt>Train 2020-2023</dt><dd><?= n($a['train_rows']) ?></dd></div>
                        <div><dt>Test 2024-2025</dt><dd><?= n($a['test_rows']) ?></dd></div>
                        <div><dt>Honeypot filled</dt><dd><?= pct($a['positive_rate']) ?></dd></div>
                    </dl>
                    <p>Every model is scored the same way: grouped five-fold cross-validation (all copies of a template stay in one fold) and a
                        time split that trains on the past and tests on the following period. No feature comes from the honeypot field or from time.</p>
                    <?php fig('fig_task_a_models.png', 'Balanced accuracy in cross-validation and on the later period.'); ?>
                    <div class="table-wrap"><table>
                        <thead><tr><th>Model</th><th class="num">Balanced acc., CV</th><th class="num">AUC, CV</th><th class="num">Balanced acc., later period</th><th class="num">AUC, later period</th><th class="num">Size (KB)</th></tr></thead>
                        <tbody>
<?php foreach ($a['cv'] as $row): $t = $tsA[$row['model']]; $base = strpos($row['model'], 'Baseline') === 0; ?>
                            <tr class="<?= $base ? 'base' : ($row['model'] === $a['best_model_time_split'] ? 'chosen' : '') ?>">
                                <td><?= e($row['model']) ?></td><td class="num"><?= f3($row['balanced_acc']) ?></td><td class="num"><?= f3($row['auc']) ?></td>
                                <td class="num"><?= f3($t['balanced_acc']) ?></td><td class="num"><?= f3($t['auc']) ?></td><td class="num"><?= number_format($t['size_kb'], 1) ?></td></tr>
<?php endforeach; ?>
                        </tbody>
                    </table></div>
                    <ul class="analysis">
                        <li><strong>The features carry signal and nothing leaked.</strong> No score is near 1.00, which is what an observed, noisy label looks like.</li>
                        <li><strong>A one-line rule is hard to beat.</strong> "The message has a URL" reaches <?= f3($cvA["Baseline: rule 'has a URL'"]['balanced_acc']) ?>; the learned models rank submissions better.</li>
                        <li><strong>Forward in time, most models fall to chance.</strong> Only logistic regression keeps a useful score. In 2025 the form changed and almost every sender fills the field: that is concept drift, and content features cannot see it.</li>
                    </ul>

                    <h3>Decision tree: information gain (ID3) against gain ratio (C4.5)</h3>
                    <div class="table-wrap"><table>
                        <thead><tr><th>Attribute at the root</th><th class="num">Distinct values</th><th class="num">Information gain</th><th class="num">Split information</th><th class="num">Gain ratio</th></tr></thead>
                        <tbody>
<?php usort($m['tree_root']['table'], fn($x, $y) => $y['information gain'] <=> $x['information gain']);
      foreach ($m['tree_root']['table'] as $row): ?>
                            <tr><td><?= e($row['attribute']) ?></td><td class="num"><?= n($row['distinct values']) ?></td>
                                <td class="num<?= $row['attribute'] === $m['tree_root']['id3_choice'] ? ' best' : '' ?>"><?= f3($row['information gain']) ?></td>
                                <td class="num"><?= f3($row['split information']) ?></td>
                                <td class="num<?= $row['attribute'] === $m['tree_root']['c45_choice'] ? ' best' : '' ?>"><?= f3($row['gain ratio']) ?></td></tr>
<?php endforeach; ?>
                        </tbody>
                    </table></div>
                    <p class="note">Root entropy <?= f3($m['tree_root']['root_entropy']) ?> bits. ID3 would pick "<?= e($m['tree_root']['id3_choice']) ?>", which only memorises the data;
                        C4.5 picks "<?= e($m['tree_root']['c45_choice']) ?>". Tuned depth: <?= e($a['tree_depth']) ?>.</p>
                    <pre><?= e($rules['decision_tree_depth3']) ?></pre>

                    <h3>What each model showed</h3>
                    <div class="table-wrap"><table>
                        <thead><tr><th>Model</th><th>Comparison</th><th class="num">Balanced accuracy</th></tr></thead>
                        <tbody>
<?php foreach ($a['nb_variants'] as $name => $value): ?>
                            <tr><td>Naive Bayes</td><td><?= e($name) ?></td><td class="num"><?= f3($value) ?></td></tr>
<?php endforeach; foreach ($a['knn_scaling'] as $name => $value): ?>
                            <tr><td>KNN (k = <?= e($a['knn_k']) ?>)</td><td><?= e($name) ?></td><td class="num"><?= f3($value) ?></td></tr>
<?php endforeach; foreach ($a['mahalanobis_vs_euclidean'] as $name => $value): ?>
                            <tr><td>Distance to class mean</td><td><?= e($name) ?></td><td class="num"><?= f3($value) ?></td></tr>
<?php endforeach; foreach ($a['mlp_train_vs_later'] as $name => $value): ?>
                            <tr><td>MLP</td><td><?= e($name) ?></td><td class="num"><?= f3($value) ?></td></tr>
<?php endforeach; foreach ($a['lr_train_vs_later'] as $name => $value): ?>
                            <tr><td>Logistic regression</td><td><?= e($name) ?></td><td class="num"><?= f3($value) ?></td></tr>
<?php endforeach; ?>
                        </tbody>
                    </table></div>
                    <ul class="analysis">
                        <li><strong>Naive Bayes.</strong> The Bernoulli variant on yes/no flags beats the Gaussian one: count features are far from Gaussian.</li>
                        <li><strong>KNN.</strong> Scaling matters for a distance-based method, and the model is the whole training set.</li>
                        <li><strong>Mahalanobis.</strong> Correcting distance for covariance beats plain Euclidean distance to the class mean.</li>
                        <li><strong>Perceptron and MLP.</strong> The perceptron never settles because the classes are not linearly separable. The MLP fits its training rows best and is at chance later: its capacity went into memorising one period.</li>
                    </ul>
                    <div class="pair">
                        <?php fig('fig_tuning.png', 'Over-fitting: training against held-out accuracy for tree depth and K.'); ?>
                        <?php fig('fig_learning_curves.png', 'Perceptron errors per pass and MLP training loss.'); ?>
                    </div>
                    <?php fig('fig_task_a_roc.png', 'ROC curves in cross-validation and on the later period.'); ?>
                    <?php fig('fig_task_a_explain.png', 'What the tree and logistic regression rely on.'); ?>
                </div>
            </section>

            <!-- ============================================================ Task B -->
            <section>
                <?php head('task-b', '8', 'Task B: spam versus legitimate', 'Supervised: classification', 'This is the model that scores an incoming message when the honeypot stays silent.'); ?>
                <div class="body">
                    <p>The dataset has no legitimate messages, so <?= n($b['rows']) ?> messages were assembled from the form's spam templates and public
                        legitimate SMS. The two classes come from different sources, so the last two columns test the models outside that corpus.</p>
                    <div class="table-wrap"><table>
                        <thead><tr><th>Model</th><th class="num">Balanced acc.</th><th class="num">F1</th><th class="num">AUC</th><th class="num">Same-source AUC</th><th class="num">Genuine messages flagged (of 40)</th><th class="num">Size (KB)</th></tr></thead>
                        <tbody>
<?php foreach ($b['cv'] as $row): if (strpos($row['model'], 'Baseline: majority') === 0) continue;
      $x = $cross[$row['model']] ?? null; $chosen = $row['model'] === $card['model']; ?>
                            <tr class="<?= $chosen ? 'chosen' : (strpos($row['model'], 'Baseline') === 0 ? 'base' : '') ?>">
                                <td><?= e($row['model']) ?><?= $chosen ? ' <span class="badge deployed">deployed</span>' : '' ?></td>
                                <td class="num"><?= f3($row['balanced_acc']) ?></td><td class="num"><?= f3($row['f1']) ?></td><td class="num"><?= f3($row['auc']) ?></td>
                                <td class="num"><?= $x ? f3($x['same-source AUC']) : '&ndash;' ?></td><td class="num"><?= $x ? (int) $x[$FP] : '&ndash;' ?></td><td class="num"><?= n($row['size_kb']) ?></td></tr>
<?php endforeach; ?>
                        </tbody>
                    </table></div>
                    <div class="pair">
                        <?php fig('fig_task_b_models.png', 'Scores inside the corpus are close; false positives on genuine messages differ.'); ?>
                        <?php fig('fig_task_b_controls.png', 'With lengths matched, length alone fails and words still work.'); ?>
                    </div>
                    <ul class="analysis">
                        <li><strong>Much of the score is the source difference.</strong> Message length alone, with no words, already separates most of the corpus.</li>
                        <li><strong>Words still carry real signal.</strong> With lengths matched, the length baseline drops to chance and the word models hold.</li>
                        <li><strong>Higher accuracy was not a better filter.</strong> The perceptron and the MLP lead the table and flag the most genuine messages.</li>
                        <li><strong>Naive Bayes smoothing.</strong> <?= n($b['zero_frequency']['never_in_legitimate']) ?> of <?= n($b['zero_frequency']['vocabulary']) ?> vocabulary words never occur in the legitimate class; without Laplace smoothing each would force a probability of zero.</li>
                        <li><strong>Where it fails.</strong> It passes <?= n($b['errors']['spam passed as legitimate']) ?> spam templates with a median length of <?= n($b['errors']['median length, missed spam']) ?> characters
                            (caught spam: <?= n($b['errors']['median length, caught spam']) ?>). These are the senders that also evade the honeypot.</li>
                    </ul>
                    <h3>Decision threshold of the deployed model</h3>
                    <div class="table-wrap"><table>
                        <thead><tr><th class="num">Threshold</th><th class="num">Precision</th><th class="num">Recall</th><th class="num">Specificity</th><th class="num">Genuine messages flagged (of 40)</th></tr></thead>
                        <tbody>
<?php foreach ($b['thresholds'] as $t): ?>
                            <tr<?= $t['threshold'] == $card['default_threshold'] ? ' class="chosen"' : '' ?>><td class="num"><?= number_format($t['threshold'], 1) ?></td><td class="num"><?= f3($t['precision']) ?></td><td class="num"><?= f3($t['recall']) ?></td>
                                <td class="num"><?= f3($t['specificity']) ?></td><td class="num"><?= (int) $t['contact-form legitimate flagged (of 40)'] ?></td></tr>
<?php endforeach; ?>
                        </tbody>
                    </table></div>
                    <p class="note"><?= e($card['limits']) ?></p>
                </div>
            </section>

            <!-- ============================================================ Verdict -->
            <section>
                <?php head('verdict', '9', 'Which algorithm suits which job', 'Comparison', 'A score on data like the training data says little about how a model holds up when the data differs.'); ?>
                <div class="body">
                    <div class="table-wrap"><table>
                        <thead><tr><th>Algorithm</th><th class="num">A: CV</th><th class="num">A: later period</th><th class="num">B: CV</th><th class="num">B: same-source AUC</th><th class="num">B: genuine flagged</th><th>Verdict</th></tr></thead>
                        <tbody>
<?php $verdicts = [
    'Naive Bayes' => 'Good fallback when no tuning is possible',
    'Logistic regression' => 'Deployed: most reliable outside its training data, gives a probability',
    'Decision tree' => 'Use for explanation, not for scoring',
    'KNN' => 'Stores all data; not for a small server',
    'Mahalanobis' => 'Shows the value of covariance; needs PCA',
    'Perceptron' => 'No probability; superseded by logistic regression',
    'MLP' => 'Memorises its period; not justified at this size',
];
foreach ($m['summary'] as $row): ?>
                            <tr<?= $row['model'] === 'Logistic regression' ? ' class="chosen"' : '' ?>><td><?= e($row['model']) ?></td>
                                <td class="num"><?= f3($row['A: balanced acc, cross-validation']) ?></td><td class="num"><?= f3($row['A: balanced acc, future period']) ?></td>
                                <td class="num"><?= f3($row['B: balanced acc, cross-validation']) ?></td><td class="num"><?= f3($row['B: same-source AUC']) ?></td>
                                <td class="num"><?= (int) $row['B: genuine messages flagged (of 40)'] ?></td><td><?= e($verdicts[$row['model']] ?? '') ?></td></tr>
<?php endforeach; ?>
                        </tbody>
                    </table></div>
                </div>
            </section>

            <!-- ============================================================ Regression -->
            <section>
                <?php head('trend', '10', 'Regression: is there a trend?', 'Supervised: regression', 'Two operator questions are about trend: is spam volume growing, and is the honeypot hit rate falling steadily?'); ?>
                <div class="body">
                    <?php fig('fig_trend.png', 'Monthly volume and monthly hit rate with linear and second-degree fits.'); ?>
                    <div class="table-wrap"><table>
                        <thead><tr><th>Quantity</th><th class="num">Months</th><th class="num">Slope per month</th><th class="num">R&sup2;, linear</th><th class="num">R&sup2;, degree 2</th></tr></thead>
                        <tbody>
                            <tr><td>Submissions per month</td><td class="num"><?= n($m['trend']['submissions']['months']) ?></td><td class="num"><?= number_format($m['trend']['submissions']['w1_per_month'], 2) ?></td><td class="num"><?= number_format($m['trend']['submissions']['r2_linear'], 2) ?></td><td class="num"><?= number_format($m['trend']['submissions']['r2_degree2'], 2) ?></td></tr>
                            <tr><td>Honeypot hit rate (%)</td><td class="num"><?= n($m['trend']['hit_rate']['months']) ?></td><td class="num"><?= number_format($m['trend']['hit_rate']['w1_per_month'], 2) ?></td><td class="num"><?= number_format($m['trend']['hit_rate']['r2_linear'], 2) ?></td><td class="num"><?= number_format($m['trend']['hit_rate']['r2_degree2'], 2) ?></td></tr>
                        </tbody>
                    </table></div>
                    <ul class="analysis"><li>Neither quantity follows a smooth trend. Volume comes in bursts as campaigns switch on and off, and the hit rate jumps with the campaign mix. A trend line would be the wrong forecast; the campaign view is the informative one.</li></ul>
                </div>
            </section>

            <!-- ============================================================ Live -->
            <section>
                <?php head('live', '11', 'Live scoring', 'In use', 'The mined model, campaigns and rules score every submission the form receives.'); ?>
                <div class="body">
                    <div id="service-warning" class="warn" style="display:none">No submission has a model score yet. Start the scoring service
                        (<code>npm run dev</code>); until then FormTrap scores with its rules alone.</div>
                    <dl class="facts">
                        <div><dt>Scored by the model</dt><dd id="stat-scored">&ndash;</dd></div>
                        <div><dt>Flagged as spam</dt><dd id="stat-spam">&ndash;</dd></div>
                        <div><dt>Share flagged</dt><dd id="stat-spam-share">&ndash;</dd></div>
                        <div><dt>Without a score</dt><dd id="stat-unscored">&ndash;</dd></div>
                        <div><dt>Deployed model</dt><dd style="font-size:16px; padding-top:4px"><?= e($card['model']) ?></dd></div>
                    </dl>
                    <h3>Latest scored submissions</h3>
                    <div class="table-wrap" id="recent-table"><div class="empty">Loading&hellip;</div></div>
                    <h3>Scoring rules in use</h3>
                    <p class="note">The hand-written rules with their hand-picked weights, and the model's rule among them.</p>
                    <div class="table-wrap" id="rules-table"><div class="empty">Loading&hellip;</div></div>
                </div>
            </section>
        </main>
    </div>

    <script>
        Chart.defaults.font.family = "'Inter', system-ui, -apple-system, sans-serif";
        Chart.defaults.color = '#57544d';
        const GRID = '#e6e3dd', SERIES = '#2a78d6';
        let volumeChart = null, rateChart = null;

        function esc(text) {
            const div = document.createElement('div');
            div.textContent = text == null ? '' : String(text);
            return div.innerHTML;
        }
        const num = v => Number(v).toLocaleString();
        const pct = (v, d = 0) => v == null ? '–' : (v * 100).toFixed(d) + '%';

        // highlight the section in view
        const links = new Map([...document.querySelectorAll('.toc a')].map(a => [a.getAttribute('href').slice(1), a]));
        const spy = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (!entry.isIntersecting) return;
                links.forEach(a => a.classList.remove('current'));
                links.get(entry.target.id)?.classList.add('current');
            });
        }, { rootMargin: '-90px 0px -70% 0px' });
        links.forEach((_, id) => { const el = document.getElementById(id); if (el) spy.observe(el); });

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
                recent.innerHTML = '<div class="empty">Nothing scored yet. Submit the form, or run <code>npm run import</code> to load the dataset history.</div>';
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
                    borderColor: SERIES, backgroundColor: SERIES, borderWidth: 2, pointRadius: 4, pointBorderColor: '#fffefc', pointBorderWidth: 2, spanGaps: false }] },
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
                table.innerHTML = '<div class="empty">No submissions match this selection. Run <code>npm run import</code> to load the dataset history.</div>';
                return;
            }
            table.innerHTML = `<table>
                <thead><tr><th>Period</th>${grouped ? '<th>' + esc(document.getElementById('olap-by').selectedOptions[0].text) + '</th>' : ''}
                <th class="num">Submissions</th><th class="num">With a label</th><th class="num">Honeypot hits</th>
                <th class="num">Hit rate</th><th class="num">Flagged by model</th><th class="num">Share flagged</th></tr></thead><tbody>` +
                data.rows.map(r => `<tr class="${r.is_total ? 'total' : r.is_subtotal ? 'subtotal' : ''}">
                    <td>${r.is_total ? 'All periods' : esc(r.period)}</td>
                    ${grouped ? '<td>' + (r.is_total ? '' : r.is_subtotal ? 'subtotal' : esc(r.grp)) + '</td>' : ''}
                    <td class="num">${num(r.submissions)}</td><td class="num">${num(r.labelled)}</td>
                    <td class="num">${num(r.honeypot_hits)}</td><td class="num">${pct(r.hit_rate)}</td>
                    <td class="num">${num(r.ml_spam)}</td><td class="num">${pct(r.ml_spam_rate)}</td>
                </tr>`).join('') + '</tbody></table>';
        }

        const failed = id => { document.getElementById(id).innerHTML = '<div class="empty">Could not load this from the database. Is MySQL running?</div>'; };
        ['olap-level', 'olap-year', 'olap-label', 'olap-by'].forEach(id => document.getElementById(id).addEventListener('change', () => loadOlap().catch(() => failed('olap-table'))));
        loadSummary().catch(() => { failed('recent-table'); failed('rules-table'); });
        loadOlap().catch(() => failed('olap-table'));
    </script>
<?php endif; ?>
</body>
</html>
