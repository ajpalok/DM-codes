<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contact Us - Secure Form</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #e35f27;
            --primary-hover: #ca4e20;
            --text-dark: #111827;
            --text-gray: #6b7280;
            --bg-gray: #f9fafb;
            --border: #d1d5db;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-gray);
            color: var(--text-dark);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        header {
            background: white;
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

        main {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 40px 24px;
            background-image: 
                radial-gradient(#e5e7eb 1px, transparent 1px),
                radial-gradient(#e5e7eb 1px, transparent 1px);
            background-size: 20px 20px;
            background-position: 0 0, 10px 10px;
        }


        footer {
            padding: 32px 24px;
            text-align: center;
            color: var(--text-gray);
            border-top: 1px solid rgba(0,0,0,0.05);
            background: white;
        }
        
        footer p {
            margin-bottom: 8px;
            font-size: 14px;
        }
        
        footer .small-text {
            font-size: 12px;
            opacity: 0.7;
        }

        .container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            padding: 48px;
            max-width: 540px;
            width: 100%;
            border: 1px solid rgba(0,0,0,0.05);
        }
        h1 {
            color: var(--text-dark);
            margin-bottom: 8px;
            font-size: 24px;
            font-weight: 600;
            text-align: center;
        }
        .subtitle {
            color: var(--text-gray);
            margin-bottom: 32px;
            font-size: 14px;
            text-align: center;
            line-height: 1.5;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 6px;
            color: var(--text-dark);
            font-weight: 500;
            font-size: 14px;
        }
        input[type="text"],
        input[type="email"],
        textarea {
            width: 100%;
            padding: 10px 14px;
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 15px;
            font-family: inherit;
            color: var(--text-dark);
            transition: all 0.2s ease;
            background-color: #fff;
        }
        input:focus, textarea:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
        }
        textarea {
            resize: vertical;
            min-height: 120px;
        }
        button {
            background-color: var(--primary);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 15px;
            font-weight: 500;
            cursor: pointer;
            width: 100%;
            transition: background-color 0.2s;
            margin-top: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        button:hover {
            background-color: var(--primary-hover);
        }
        button:active {
            transform: translateY(1px);
        }
        .required { color: #dc2626; }
        
        /* Honeypot fields - hidden from users */
        .hp-text-hidden {
            position: absolute;
            left: -9999px;
            width: 1px;
            height: 1px;
            opacity: 0;
            pointer-events: none;
        }
        .hp-semantic {
            display: none;
        }
        
        #response-message {
            margin-top: 24px;
            padding: 12px;
            border-radius: 6px;
            display: none;
            font-size: 14px;
            text-align: center;
        }
        #response-message.success {
            background: #ecfdf5;
            color: #047857;
            border: 1px solid #a7f3d0;
        }
        #response-message.error {
            background: #fef2f2;
            color: #b91c1c;
            border: 1px solid #fecaca;
        }
    </style>
</head>
<body>
    <header>
        <a href="/" class="logo">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-right: 8px;">
                <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="#e35f27" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 17L12 22L22 17" stroke="#e35f27" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 12L12 17L22 12" stroke="#e35f27" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Form<span>Trap</span>
        </a>
        <nav>
            <a href="dashboard.php" class="nav-link">Dashboard</a>
            <a href="mining.php" class="nav-link">Data Mining</a>
            <a href="about.php" class="nav-link">About</a>
        </nav>
    </header>

    <main>
        <div class="container">
            <div style="text-align: center; margin-bottom: 24px;">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect x="3" y="5" width="18" height="14" rx="2" stroke="#e35f27" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M3 7L12 13L21 7" stroke="#e35f27" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </div>
            <h1>Contact Us</h1>
        <p class="subtitle">This form includes deception-based security measures to detect automated submissions.</p>
        
        <form id="contactForm" method="POST" action="submit.php">
            <div class="form-group">
                <label for="name">Name <span class="required">*</span></label>
                <input type="text" id="name" name="name" required>
            </div>

            <div class="form-group">
                <label for="email">Email <span class="required">*</span></label>
                <input type="email" id="email" name="email" required>
            </div>

            <div class="form-group">
                <label for="subject">Subject <span class="required">*</span></label>
                <input type="text" id="subject" name="subject" required>
            </div>

            <div class="form-group">
                <label for="message">Message <span class="required">*</span></label>
                <textarea id="message" name="message" required></textarea>
            </div>

            <!-- HONEYPOT: Hidden text field (CSS-based invisibility) -->
            <div class="hp-text-hidden">
                <label for="website_url">Website URL</label>
                <input type="text" id="website_url" name="website_url" tabindex="-1" autocomplete="off">
            </div>

                <span>Send Message</span>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M22 2L11 13" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            
            <!-- HONEYPOT: Semantic trap (hidden but looks legit in source) -->
            <div class="hp-semantic">
                <label for="company_code">Company Code <span class="required">*</span></label>
                <input type="text" id="company_code" name="company_code" tabindex="-1" autocomplete="off">
            </div>

            <!-- HONEYPOT: Time-trap field (JS will populate after delay) -->
            <input type="hidden" id="security_token" name="security_token" value="">
            
            <!-- Client timing token -->
            <input type="hidden" id="form_render_time" name="form_render_time" value="">

            <button type="submit">Send Message</button>
        </form>

        <div id="response-message"></div>
        </div>
    </main>

    <footer>
        <p>Protected by advanced honeypot technology.</p>
        <p class="small-text">&copy; 2026 FormTrap Security Systems. All rights reserved.</p>
    </footer>

    <script src="assets/form.js"></script>
</body>
</html>
