/**
 * Contact Form Content Module
 * Generates the contact form HTML for the artifact panel
 */

/**
 * Generate contact form HTML
 * @param {string} csrfToken - CSRF token for form submission
 * @returns {string} HTML string for the contact form
 */
export function generateContactFormHTML(csrfToken) {
    return `
        <div class="artifact-contact-form">
            <div class="artifact-form-intro">
                <h3 class="artifact-form-title">Connect with Our Experts</h3>
                <p class="artifact-form-description">
                    Our solar market experts will reach out to you within 24-48 hours with personalized insights
                    and analysis tailored to your specific needs.
                </p>
            </div>

            <form id="artifact-contact-form" class="contact-form" novalidate>
                <input type="hidden" name="csrf_token" value="${csrfToken}">

                <!-- Full Name -->
                <div class="form-group">
                    <label for="contact-name" class="form-label">
                        Full Name <span class="required">*</span>
                    </label>
                    <input
                        type="text"
                        id="contact-name"
                        name="name"
                        class="form-input"
                        placeholder="Enter your full name"
                        required
                        autocomplete="name"
                    >
                    <span class="form-error" id="name-error"></span>
                </div>

                <!-- Email -->
                <div class="form-group">
                    <label for="contact-email" class="form-label">
                        Email Address <span class="required">*</span>
                    </label>
                    <input
                        type="email"
                        id="contact-email"
                        name="email"
                        class="form-input"
                        placeholder="your.email@example.com"
                        required
                        autocomplete="email"
                    >
                    <span class="form-error" id="email-error"></span>
                </div>

                <!-- Company (Optional) -->
                <div class="form-group">
                    <label for="contact-company" class="form-label">
                        Company
                    </label>
                    <input
                        type="text"
                        id="contact-company"
                        name="company"
                        class="form-input"
                        placeholder="Your company name (optional)"
                        autocomplete="organization"
                    >
                </div>

                <!-- Message -->
                <div class="form-group">
                    <label for="contact-message" class="form-label">
                        Your Question or Request <span class="required">*</span>
                    </label>
                    <textarea
                        id="contact-message"
                        name="message"
                        class="form-textarea"
                        rows="4"
                        placeholder="Please describe what information or insights you're looking for..."
                        required
                    ></textarea>
                    <span class="form-error" id="message-error"></span>
                </div>

                <!-- Submit Button -->
                <div class="form-actions">
                    <button type="submit" class="btn-submit" id="contact-submit-btn">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M22 2L11 13"></path>
                            <path d="M22 2L15 22L11 13L2 9L22 2Z"></path>
                        </svg>
                        <span>Send Request</span>
                    </button>
                </div>

                <!-- Success/Error Messages -->
                <div id="form-message" class="form-message" style="display: none;"></div>
            </form>
        </div>
    `;
}

/**
 * Generate success message HTML
 * @param {string} name - User's name
 * @returns {string} HTML string for success message
 */
export function generateSuccessHTML(name) {
    return `
        <div class="artifact-success">
            <div class="success-icon">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
            </div>
            <h3 class="success-title">Request Sent Successfully!</h3>
            <p class="success-message">
                Thank you, ${name}! Our experts have received your request and will reach out to you
                within 24-48 hours with personalized insights.
            </p>
            <p class="success-note">
                Please check your email (including spam folder) for our response.
            </p>
            <button class="btn-close-success" id="close-success-btn">
                Close
            </button>
        </div>
    `;
}
