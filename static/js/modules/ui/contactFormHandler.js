/**
 * Contact Form Handler Module
 * Manages contact form in artifact panel: validation, submission, success state
 */

import { artifactPanel } from './artifactPanel.js';
import { generateContactFormHTML, generateSuccessHTML } from './contactFormContent.js';
import { api } from '../core/api.js';

export class ContactFormHandler {
    constructor() {
        this.form = null;
        this.submitBtn = null;
    }

    /**
     * Show contact form in artifact panel
     */
    showContactForm() {
        // Get CSRF token from page
        const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';

        // Generate form HTML
        const formHTML = generateContactFormHTML(csrfToken);

        // Open artifact panel with contact form
        artifactPanel.open({
            title: 'Contact Our Experts',
            content: formHTML,
            type: 'form'
        });

        // Setup form after panel opens
        setTimeout(() => {
            this.setupForm();
        }, 100);
    }

    /**
     * Setup form event listeners and validation
     */
    setupForm() {
        this.form = document.getElementById('artifact-contact-form');
        this.submitBtn = document.getElementById('contact-submit-btn');

        if (!this.form) {
            console.error('Contact form not found');
            return;
        }

        // Form submission
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSubmit();
        });

        // Real-time validation
        const inputs = this.form.querySelectorAll('.form-input, .form-textarea');
        inputs.forEach(input => {
            input.addEventListener('blur', () => {
                this.validateField(input);
            });

            input.addEventListener('input', () => {
                // Clear error on input
                if (input.classList.contains('error')) {
                    input.classList.remove('error');
                    const errorElement = document.getElementById(`${input.name}-error`);
                    if (errorElement) {
                        errorElement.textContent = '';
                    }
                }
            });
        });
    }

    /**
     * Validate individual field
     * @param {HTMLElement} field - Form field to validate
     * @returns {boolean} Whether field is valid
     */
    validateField(field) {
        const value = field.value.trim();
        const name = field.name;
        const errorElement = document.getElementById(`${name}-error`);

        let errorMessage = '';

        // Required field validation
        if (field.hasAttribute('required') && !value) {
            errorMessage = 'This field is required';
        }

        // Email validation
        if (name === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                errorMessage = 'Please enter a valid email address';
            }
        }

        // Update UI
        if (errorMessage) {
            field.classList.add('error');
            if (errorElement) {
                errorElement.textContent = errorMessage;
            }
            return false;
        } else {
            field.classList.remove('error');
            if (errorElement) {
                errorElement.textContent = '';
            }
            return true;
        }
    }

    /**
     * Validate entire form
     * @returns {boolean} Whether form is valid
     */
    validateForm() {
        const requiredFields = this.form.querySelectorAll('[required]');
        let isValid = true;

        requiredFields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });

        return isValid;
    }

    /**
     * Handle form submission
     */
    async handleSubmit() {
        // Validate form
        if (!this.validateForm()) {
            this.showFormMessage('Please fix the errors above', 'error');
            return;
        }

        // Get form data
        const formData = new FormData(this.form);
        const data = {
            name: formData.get('name'),
            email: formData.get('email'),
            company: formData.get('company') || '',
            phone: formData.get('phone') || '',
            message: formData.get('message'),
            csrf_token: formData.get('csrf_token')
        };

        // Disable submit button
        this.submitBtn.disabled = true;
        this.submitBtn.classList.add('loading');

        try {
            // Submit to backend
            const response = await fetch('/contact/submit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                // Show success screen
                this.showSuccess(data.name);
            } else {
                // Show error message
                const errorMsg = result.message || 'Failed to send request. Please try again.';
                this.showFormMessage(errorMsg, 'error');
                this.submitBtn.disabled = false;
                this.submitBtn.classList.remove('loading');
            }
        } catch (error) {
            console.error('Contact form submission error:', error);
            this.showFormMessage('Network error. Please check your connection and try again.', 'error');
            this.submitBtn.disabled = false;
            this.submitBtn.classList.remove('loading');
        }
    }

    /**
     * Show form message (success/error)
     * @param {string} message - Message text
     * @param {string} type - Message type (success/error)
     */
    showFormMessage(message, type) {
        const messageElement = document.getElementById('form-message');
        if (messageElement) {
            messageElement.textContent = message;
            messageElement.className = `form-message ${type}`;
            messageElement.style.display = 'block';

            // Scroll to message
            messageElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    /**
     * Show success screen
     * @param {string} name - User's name
     */
    showSuccess(name) {
        const successHTML = generateSuccessHTML(name);
        artifactPanel.updateContent(successHTML);
        artifactPanel.updateTitle('Success!');

        // Setup close button
        setTimeout(() => {
            const closeBtn = document.getElementById('close-success-btn');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    artifactPanel.close();
                });
            }
        }, 100);
    }
}

// Create singleton instance
export const contactFormHandler = new ContactFormHandler();
