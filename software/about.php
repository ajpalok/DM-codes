<?php
// Read the Quickstart guide content
$quickstartContent = file_exists('docs/QUICKSTART.md') ? file_get_contents('docs/QUICKSTART.md') : '# Quickstart Guide Not Found';
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>About - FormTrap</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <!-- Marked.js for Markdown rendering -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        :root {
            --primary: #e35f27;
            --primary-hover: #ca4e20;
            --text-dark: #111827;
            --text-gray: #6b7280;
            --bg-gray: #f9fafb;
            --border: #e5e7eb;
            --white: #ffffff;
            --panel-bg: #ffffff;
            --code-bg: #f3f4f6;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background: var(--bg-gray);
            color: var(--text-dark);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            line-height: 1.6;
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

        nav {
            display: flex;
            gap: 8px;
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
        
        .nav-link:hover, .nav-link.active {
            color: var(--primary);
            background: #f3f4f6;
        }
        
        .nav-link.active {
            font-weight: 600;
        }

        main {
            flex: 1;
            padding: 40px 24px;
            max-width: 960px;
            margin: 0 auto;
            width: 100%;
        }

        .hero-section {
            background: white;
            padding: 48px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            margin-bottom: 32px;
            border: 1px solid var(--border);
            text-align: center;
        }

        .hero-section h1 {
            font-size: 36px;
            margin-bottom: 16px;
            color: var(--text-dark);
        }

        .hero-section p {
            color: var(--text-gray);
            font-size: 18px;
            max-width: 700px;
            margin: 0 auto;
        }

        .content-card {
            background: white;
            padding: 48px;
            border-radius: 12px;
            box-shadow: 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            border: 1px solid var(--border);
        }

        /* Markdown Styles */
        .markdown-body {
            color: var(--text-dark);
        }
        
        .markdown-body h1, .markdown-body h2, .markdown-body h3 {
            margin-top: 24px;
            margin-bottom: 16px;
            font-weight: 600;
            line-height: 1.25;
        }

        .markdown-body h1 { font-size: 2em; border-bottom: 1px solid var(--border); padding-bottom: 0.3em; }
        .markdown-body h2 { font-size: 1.5em; border-bottom: 1px solid var(--border); padding-bottom: 0.3em; margin-top: 1.5em; }
        .markdown-body h3 { font-size: 1.25em; }
        
        .markdown-body p { margin-bottom: 16px; }
        .markdown-body ul, .markdown-body ol { padding-left: 2em; margin-bottom: 16px; }
        .markdown-body li { margin-bottom: 4px; }
        
        .markdown-body code {
            background-color: var(--code-bg);
            padding: 0.2em 0.4em;
            border-radius: 4px;
            font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
            font-size: 85%;
        }
        
        .markdown-body pre {
            background-color: #1e293b;
            padding: 16px;
            border-radius: 8px;
            overflow: auto;
            margin-bottom: 16px;
            color: #e2e8f0;
        }
        
        .markdown-body pre code {
            background: none;
            padding: 0;
            font-size: 14px;
            color: inherit;
        }
        
        .markdown-body blockquote {
            border-left: 4px solid var(--primary);
            padding-left: 16px;
            color: var(--text-gray);
            margin-bottom: 16px;
            background: #f9fafb;
            padding: 16px;
            border-radius: 0 8px 8px 0;
        }

        .markdown-body a { color: var(--primary); text-decoration: none; }
        .markdown-body a:hover { text-decoration: underline; }

        footer {
            padding: 32px 24px;
            text-align: center;
            color: var(--text-gray);
            border-top: 1px solid rgba(0,0,0,0.05);
            background: white;
            margin-top: auto;
        }
        
        footer p { margin-bottom: 8px; font-size: 14px; }
        footer .small-text { font-size: 12px; opacity: 0.7; }
    </style>
</head>
<body>
    <header>
        <a href="index.php" class="logo">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-left: 8px;">
                <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="#e35f27" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 17L12 22L22 17" stroke="#e35f27" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 12L12 17L22 12" stroke="#e35f27" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Form<span>Trap</span>
        </a>
        <nav>
            <a href="index.php" class="nav-link">Home</a>
            <a href="dashboard.php" class="nav-link">Dashboard</a>
            <a href="mining.php" class="nav-link">Data Mining</a>
            <a href="about.php" class="nav-link active">About</a>
        </nav>
    </header>

    <main>
        <div class="hero-section">
            <h1>About FormTrap</h1>
            <p>A sophisticated honeypot security system aimed at detecting and blocking automated bot submissions without affecting user experience.</p>
        </div>

        <div class="content-card">
            <div id="markdown-content" class="markdown-body"></div>
        </div>
    </main>

    <footer>
        <p>Protected by advanced honeypot technology.</p>
        <p class="small-text">&copy; <?php echo date('Y'); ?> FormTrap Security Systems. All rights reserved.</p>
    </footer>

    <!-- Hidden div to store the raw markdown -->
    <div id="raw-markdown" style="display:none;" data-content="<?php echo htmlspecialchars(json_encode($quickstartContent), ENT_QUOTES, 'UTF-8'); ?>"></div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            try {
                const rawMarkdownElement = document.getElementById('raw-markdown');
                const rawMarkdown = JSON.parse(rawMarkdownElement.dataset.content);
                const contentDiv = document.getElementById('markdown-content');

                // Render Markdown
                contentDiv.innerHTML = marked.parse(rawMarkdown);
            } catch (error) {
                console.error('Error rendering markdown:', error);
                document.getElementById('markdown-content').innerHTML = '<p style="color: #ef4444;">Error loading documentation. Please check the console for details.</p>';
            }
        });
    </script>
</body>
</html>
