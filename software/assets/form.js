/**
 * Client-side honeypot logic and form submission handler
 */

(function() {
    'use strict';

    const formRenderTime = Date.now();
    let timeTrapPopulated = false;

    // Populate render time immediately
    document.getElementById('form_render_time').value = formRenderTime;

    // Time-based honeypot: populate security_token after 1.5 seconds
    // Bots submitting immediately won't have this value
    setTimeout(function() {
        const token = generateToken();
        document.getElementById('security_token').value = token;
        timeTrapPopulated = true;
    }, 1500);

    // Generate random token
    function generateToken() {
        return 'tk_' + Math.random().toString(36).substring(2, 15) + 
               Math.random().toString(36).substring(2, 15);
    }

    // Form submission handler
    const form = document.getElementById('contactForm');
    const responseDiv = document.getElementById('response-message');
    const submitButton = form.querySelector('button[type="submit"]');

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // UI Loading state
        const originalBtnText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.textContent = 'Sending...';
        submitButton.style.opacity = '0.7';

        const submitTime = Date.now();
        const timeDiff = submitTime - formRenderTime;

        // Client-side validation: warn if submitting too quickly
        if (timeDiff < 2000) {
            console.warn('[Honeypot] Rapid submission detected:', timeDiff, 'ms');
        }

        // Check if time trap was populated
        if (!timeTrapPopulated) {
            console.warn('[Honeypot] Time trap not ready');
        }

        // Prepare form data
        const formData = new FormData(form);

        // Submit via AJAX
        fetch('submit.php', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            // Reset button state
            submitButton.disabled = false;
            submitButton.textContent = originalBtnText;
            submitButton.style.opacity = '1';

            responseDiv.style.display = 'block';
            
            if (data.success) {
                responseDiv.className = 'success';
                responseDiv.textContent = data.message || 'Thank you! Your message has been received.';
                form.reset();
                
                // Reset timing for next submission
                document.getElementById('form_render_time').value = Date.now();
                timeTrapPopulated = false;
                setTimeout(function() {
                    document.getElementById('security_token').value = generateToken();
                    timeTrapPopulated = true;
                }, 1500);
            } else {
                responseDiv.className = 'error';
                responseDiv.textContent = data.message || 'Submission failed. Please try again.';
            }
        })
        .catch(error => {
            // Reset button state
            submitButton.disabled = false;
            submitButton.textContent = originalBtnText;
            submitButton.style.opacity = '1';

            console.error('[Form Error]', error);
            responseDiv.style.display = 'block';
            responseDiv.className = 'error';
            responseDiv.textContent = 'Network error. Please try again.';
        });
    });

    // Monitor honeypot fields for tampering (additional defense)
    function monitorHoneypots() {
        const honeypots = ['website_url', 'company_code'];
        honeypots.forEach(function(fieldId) {
            const field = document.getElementById(fieldId);
            if (field) {
                field.addEventListener('change', function() {
                    console.warn('[Honeypot] Field "' + fieldId + '" was modified');
                });
            }
        });
    }

    monitorHoneypots();

    // Prevent autofill in honeypot fields
    window.addEventListener('load', function() {
        document.getElementById('website_url').value = '';
        document.getElementById('company_code').value = '';
    });
})();
