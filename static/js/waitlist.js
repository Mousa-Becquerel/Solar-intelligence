// Waitlist Landing Page JavaScript

// Google Analytics Event Tracking Helper
function trackEvent(eventName, eventParams = {}) {
    if (typeof gtag !== 'undefined') {
        gtag('event', eventName, eventParams);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('waitlist-form');
    const emailInput = document.getElementById('waitlist-email');
    const submitBtn = document.getElementById('waitlist-submit-btn');
    const successMessage = document.getElementById('success-message');
    const errorMessage = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');
    const waitlistCount = document.getElementById('waitlist-count');

    // Track page view
    trackEvent('page_view', {
        page_title: 'Waitlist Landing Page',
        page_location: window.location.href
    });

    // Rotating text animation
    const rotatingTextElement = document.getElementById('rotating-text');
    const rotatingTexts = [
        'Next-generation AI for the photovoltaic market.',
        'Reliable insights, validated by experts.',
        'Built by leaders in PV research and consulting.',
        'Simple, intuitive, and designed for everyone.'
    ];
    let currentTextIndex = 0;

    function rotateText() {
        // Fade out current text
        rotatingTextElement.style.opacity = '0';
        rotatingTextElement.style.transform = 'translateY(-20px)';

        setTimeout(() => {
            // Change text
            currentTextIndex = (currentTextIndex + 1) % rotatingTexts.length;
            rotatingTextElement.textContent = rotatingTexts[currentTextIndex];

            // Fade in new text
            rotatingTextElement.style.opacity = '1';
            rotatingTextElement.style.transform = 'translateY(0)';
        }, 600);
    }

    // Start with first text visible
    setTimeout(() => {
        rotatingTextElement.style.opacity = '1';
        rotatingTextElement.style.transform = 'translateY(0)';
    }, 300);

    // Rotate every 4 seconds
    setInterval(rotateText, 4000);

    // Step navigation
    const nextStepBtn = document.getElementById('next-step-btn');
    const backBtn = document.getElementById('back-btn');
    const stepEmail = document.getElementById('step-email');
    const stepAgents = document.getElementById('step-agents');

    // Track email input interaction
    emailInput.addEventListener('focus', function() {
        trackEvent('email_input_started');
    });

    nextStepBtn.addEventListener('click', function() {
        const email = emailInput.value.trim();
        if (!email) {
            showError('Please enter your email address');
            trackEvent('email_validation_failed', { reason: 'empty' });
            return;
        }
        if (!isValidEmail(email)) {
            showError('Please enter a valid email address');
            trackEvent('email_validation_failed', { reason: 'invalid_format' });
            return;
        }

        // Track progression to step 2
        trackEvent('waitlist_step_1_completed');

        // Move to agent selection step
        stepEmail.style.display = 'none';
        stepAgents.style.display = 'block';
        hideMessages();
    });

    backBtn.addEventListener('click', function() {
        // Track back button
        trackEvent('waitlist_back_to_email');

        // Go back to email step
        stepAgents.style.display = 'none';
        stepEmail.style.display = 'block';
    });

    // Track agent selections
    document.querySelectorAll('input[name="agents"]').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            if (this.checked) {
                trackEvent('agent_selected', { agent_type: this.value });
            } else {
                trackEvent('agent_deselected', { agent_type: this.value });
            }
        });
    });

    // Get CSRF token
    function getCSRFToken() {
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) {
            return metaToken.getAttribute('content');
        }
        const inputToken = document.querySelector('input[name="csrf_token"]');
        if (inputToken) {
            return inputToken.value;
        }
        return '';
    }

    // Smooth scroll for navigation links
    document.querySelectorAll('.waitlist-nav-link').forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href.startsWith('#')) {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }
        });
    });

    // Update active nav link on scroll
    const sections = document.querySelectorAll('section[id], main[id]');
    const navLinks = document.querySelectorAll('.waitlist-nav-link');

    function updateActiveNavLink() {
        let current = 'home';
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.offsetHeight;
            if (window.scrollY >= sectionTop - 100) {
                current = section.getAttribute('id') || 'home';
            }
        });

        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${current}`) {
                link.classList.add('active');
            }
        });
    }

    window.addEventListener('scroll', updateActiveNavLink);

    // Form submission
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const email = emailInput.value.trim();
        if (!email) {
            showError('Please enter your email address');
            return;
        }

        // Validate email format
        if (!isValidEmail(email)) {
            showError('Please enter a valid email address');
            return;
        }

        // Disable form
        submitBtn.disabled = true;
        submitBtn.innerHTML = `
            <span class="waitlist-btn-text">Joining...</span>
            <svg class="waitlist-btn-icon animate-spin" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
            </svg>
        `;

        // Get selected agents
        const selectedAgents = Array.from(document.querySelectorAll('input[name="agents"]:checked'))
            .map(checkbox => checkbox.value);

        try {
            const response = await fetch('/waitlist', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({
                    email: email,
                    interested_agents: selectedAgents
                })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                // Track successful waitlist signup
                trackEvent('waitlist_signup_success', {
                    agents_count: selectedAgents.length,
                    agents_selected: selectedAgents.join(',')
                });

                // Show success message
                showSuccess(data.message || 'Thank you! We\'ll notify you at launch.');

                // Update waitlist count
                if (data.waitlist_count !== undefined) {
                    updateWaitlistCount(data.waitlist_count);
                }

                // Clear form
                emailInput.value = '';
                document.querySelectorAll('input[name="agents"]:checked').forEach(checkbox => {
                    checkbox.checked = false;
                });

                // Reset to email step
                stepAgents.style.display = 'none';
                stepEmail.style.display = 'block';

                // Hide form after success
                setTimeout(() => {
                    form.style.display = 'none';
                }, 2000);
            } else {
                // Track failed submission
                trackEvent('waitlist_signup_failed', {
                    error_message: data.error || data.message
                });
                showError(data.error || data.message || 'Something went wrong. Please try again.');
            }
        } catch (error) {
            console.error('Error joining waitlist:', error);
            // Track network error
            trackEvent('waitlist_signup_error', {
                error_type: 'network_error'
            });
            showError('Network error. Please check your connection and try again.');
        } finally {
            // Re-enable form
            submitBtn.disabled = false;
            submitBtn.innerHTML = `
                <span class="waitlist-btn-text">Join Waitlist</span>
                <svg class="waitlist-btn-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M5 12h14M12 5l7 7-7 7"/>
                </svg>
            `;
        }
    });

    // Email validation
    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    // Show success message
    function showSuccess(message) {
        hideMessages();
        successMessage.querySelector('span').textContent = message;
        successMessage.style.display = 'flex';
        setTimeout(() => {
            successMessage.style.display = 'none';
        }, 5000);
    }

    // Show error message
    function showError(message) {
        hideMessages();
        errorText.textContent = message;
        errorMessage.style.display = 'flex';
        setTimeout(() => {
            errorMessage.style.display = 'none';
        }, 5000);
    }

    // Hide all messages
    function hideMessages() {
        successMessage.style.display = 'none';
        errorMessage.style.display = 'none';
    }

    // Update waitlist count with animation
    function updateWaitlistCount(newCount) {
        if (!waitlistCount) return;

        const currentCount = parseInt(waitlistCount.textContent) || 0;
        const duration = 1000; // 1 second
        const steps = 30;
        const increment = (newCount - currentCount) / steps;
        let step = 0;

        const interval = setInterval(() => {
            step++;
            const value = Math.round(currentCount + (increment * step));
            waitlistCount.textContent = value;

            if (step >= steps) {
                clearInterval(interval);
                waitlistCount.textContent = newCount;
            }
        }, duration / steps);
    }

    // Clear messages when typing
    emailInput.addEventListener('input', hideMessages);

    // Add spinning animation to SVG
    const style = document.createElement('style');
    style.textContent = `
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        .animate-spin {
            animation: spin 1s linear infinite;
        }
    `;
    document.head.appendChild(style);
});