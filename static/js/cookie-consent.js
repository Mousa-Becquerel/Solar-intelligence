/**
 * GDPR Cookie Consent Management System
 * Compliant with EU GDPR requirements for cookie consent
 */

class CookieConsent {
    constructor() {
        this.consentKey = 'solar_intelligence_cookie_consent';
        this.consentData = this.getStoredConsent();
        this.init();
    }

    init() {
        // Only show consent banner if no previous consent exists
        if (!this.consentData) {
            this.showConsentBanner();
        } else {
            // Apply existing consent preferences
            this.applyConsentSettings();
        }
    }

    getStoredConsent() {
        try {
            const stored = localStorage.getItem(this.consentKey);
            return stored ? JSON.parse(stored) : null;
        } catch (error) {
            console.error('Error reading consent data:', error);
            return null;
        }
    }

    storeConsent(consentData) {
        try {
            const consentRecord = {
                ...consentData,
                timestamp: new Date().toISOString(),
                version: '1.0'
            };
            localStorage.setItem(this.consentKey, JSON.stringify(consentRecord));
            this.consentData = consentRecord;
        } catch (error) {
            console.error('Error storing consent data:', error);
        }
    }

    showConsentBanner() {
        const banner = this.createConsentBanner();
        document.body.appendChild(banner);

        // Animate banner in
        setTimeout(() => {
            banner.classList.remove('translate-y-full');
            banner.classList.add('translate-y-0');
        }, 100);
    }

    createConsentBanner() {
        const banner = document.createElement('div');
        banner.className = 'fixed bottom-0 left-0 right-0 bg-white border-t-2 border-blue-500 shadow-2xl transform translate-y-full transition-transform duration-300 ease-in-out';
        banner.style.zIndex = '10500';
        banner.id = 'cookie-consent-banner';

        banner.innerHTML = `
            <div class="max-w-7xl mx-auto px-4 py-6">
                <div class="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
                    <div class="flex-1">
                        <div class="flex items-center gap-3 mb-2">
                            <svg class="w-6 h-6 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path>
                            </svg>
                            <h3 class="text-lg font-semibold text-gray-900">We Value Your Privacy</h3>
                        </div>
                        <p class="text-gray-700 text-sm leading-relaxed">
                            We use essential cookies to provide our AI analysis services and optional cookies to improve your experience.
                            You can customize your preferences or accept all cookies to continue.
                        </p>
                        <div class="mt-2">
                            <a href="/privacy-policy" class="text-blue-600 hover:text-blue-800 text-sm font-medium">Privacy Policy</a>
                            <span class="mx-2 text-gray-400">•</span>
                            <button id="customize-cookies" class="text-blue-600 hover:text-blue-800 text-sm font-medium">Customize Settings</button>
                        </div>
                    </div>
                    <div class="flex flex-col sm:flex-row gap-3">
                        <button id="accept-essential" class="px-6 py-2 bg-gray-100 hover:bg-gray-200 text-gray-800 font-medium rounded-lg transition-colors">
                            Essential Only
                        </button>
                        <button id="accept-all" class="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors">
                            Accept All Cookies
                        </button>
                    </div>
                </div>
            </div>
        `;

        // Add event listeners
        this.addBannerEventListeners(banner);
        return banner;
    }

    addBannerEventListeners(banner) {
        // Accept all cookies
        banner.querySelector('#accept-all').addEventListener('click', () => {
            this.acceptAllCookies();
            this.hideBanner(banner);
        });

        // Accept essential only
        banner.querySelector('#accept-essential').addEventListener('click', () => {
            this.acceptEssentialOnly();
            this.hideBanner(banner);
        });

        // Customize settings
        banner.querySelector('#customize-cookies').addEventListener('click', () => {
            this.showCustomizeModal();
        });
    }

    showCustomizeModal() {
        const modal = this.createCustomizeModal();
        document.body.appendChild(modal);

        // Animate modal in
        setTimeout(() => {
            modal.classList.remove('opacity-0');
            modal.classList.add('opacity-100');
            modal.querySelector('.transform').classList.remove('scale-95');
            modal.querySelector('.transform').classList.add('scale-100');
        }, 10);
    }

    createCustomizeModal() {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 opacity-0 transition-opacity duration-300';
        modal.style.zIndex = '10600';
        modal.id = 'cookie-customize-modal';

        modal.innerHTML = `
            <div class="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto transform scale-95 transition-transform duration-300">
                <div class="p-6 border-b border-gray-200">
                    <div class="flex justify-between items-center">
                        <h2 class="text-xl font-bold text-gray-900">Cookie Preferences</h2>
                        <button id="close-modal" class="text-gray-400 hover:text-gray-600">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                            </svg>
                        </button>
                    </div>
                </div>

                <div class="p-6 space-y-6">
                    <p class="text-gray-700">Manage your cookie preferences for Solar Intelligence. Essential cookies are required for the service to function and cannot be disabled.</p>

                    <!-- Essential Cookies -->
                    <div class="border rounded-lg p-4">
                        <div class="flex justify-between items-start">
                            <div class="flex-1">
                                <h3 class="font-semibold text-gray-900 mb-1">Essential Cookies</h3>
                                <p class="text-sm text-gray-600 mb-2">Required for user authentication, security, and core functionality.</p>
                                <div class="text-xs text-gray-500">
                                    <span class="font-medium">Examples:</span> Session tokens, CSRF protection, login state
                                </div>
                            </div>
                            <div class="ml-4">
                                <div class="bg-gray-100 px-3 py-1 rounded text-sm font-medium text-gray-600">Always Active</div>
                            </div>
                        </div>
                    </div>

                    <!-- Analytics Cookies -->
                    <div class="border rounded-lg p-4">
                        <div class="flex justify-between items-start">
                            <div class="flex-1">
                                <h3 class="font-semibold text-gray-900 mb-1">Analytics & Performance</h3>
                                <p class="text-sm text-gray-600 mb-2">Help us understand how you use our platform to improve performance and user experience.</p>
                                <div class="text-xs text-gray-500">
                                    <span class="font-medium">Examples:</span> Page views, feature usage, error tracking
                                </div>
                            </div>
                            <div class="ml-4">
                                <label class="relative inline-flex items-center cursor-pointer">
                                    <input type="checkbox" id="analytics-cookies" class="sr-only peer" checked>
                                    <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                                </label>
                            </div>
                        </div>
                    </div>

                    <!-- Preferences Cookies -->
                    <div class="border rounded-lg p-4">
                        <div class="flex justify-between items-start">
                            <div class="flex-1">
                                <h3 class="font-semibold text-gray-900 mb-1">Preferences & Functionality</h3>
                                <p class="text-sm text-gray-600 mb-2">Remember your settings and preferences to personalize your experience.</p>
                                <div class="text-xs text-gray-500">
                                    <span class="font-medium">Examples:</span> UI theme, language settings, dashboard layout
                                </div>
                            </div>
                            <div class="ml-4">
                                <label class="relative inline-flex items-center cursor-pointer">
                                    <input type="checkbox" id="preferences-cookies" class="sr-only peer" checked>
                                    <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                                </label>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="p-6 border-t border-gray-200">
                    <div class="flex flex-col sm:flex-row gap-3 justify-end">
                        <button id="save-preferences" class="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors">
                            Save Preferences
                        </button>
                        <button id="accept-all-modal" class="px-6 py-2 bg-gray-100 hover:bg-gray-200 text-gray-800 font-medium rounded-lg transition-colors">
                            Accept All
                        </button>
                    </div>
                </div>
            </div>
        `;

        this.addModalEventListeners(modal);
        return modal;
    }

    addModalEventListeners(modal) {
        // Close modal
        modal.querySelector('#close-modal').addEventListener('click', () => {
            this.hideModal(modal);
        });

        // Save custom preferences
        modal.querySelector('#save-preferences').addEventListener('click', () => {
            const analytics = modal.querySelector('#analytics-cookies').checked;
            const preferences = modal.querySelector('#preferences-cookies').checked;

            this.saveCustomPreferences(analytics, preferences);
            this.hideModal(modal);
            this.hideBanner();
        });

        // Accept all from modal
        modal.querySelector('#accept-all-modal').addEventListener('click', () => {
            this.acceptAllCookies();
            this.hideModal(modal);
            this.hideBanner();
        });

        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.hideModal(modal);
            }
        });
    }

    acceptAllCookies() {
        const consent = {
            essential: true,
            analytics: true,
            preferences: true
        };

        this.storeConsent(consent);
        this.applyConsentSettings();
        this.showConsentNotification('All cookies accepted');
    }

    acceptEssentialOnly() {
        const consent = {
            essential: true,
            analytics: false,
            preferences: false
        };

        this.storeConsent(consent);
        this.applyConsentSettings();
        this.showConsentNotification('Essential cookies only');
    }

    saveCustomPreferences(analytics, preferences) {
        const consent = {
            essential: true,
            analytics: analytics,
            preferences: preferences
        };

        this.storeConsent(consent);
        this.applyConsentSettings();
        this.showConsentNotification('Cookie preferences saved');
    }

    applyConsentSettings() {
        if (!this.consentData) return;

        // Apply analytics settings
        if (this.consentData.analytics) {
            this.enableAnalytics();
        } else {
            this.disableAnalytics();
        }

        // Apply preferences settings
        if (this.consentData.preferences) {
            this.enablePreferences();
        } else {
            this.disablePreferences();
        }
    }

    enableAnalytics() {
        // Enable analytics tracking
        console.log('Analytics cookies enabled');
        // Add your analytics initialization here
        // Example: gtag, mixpanel, etc.
    }

    disableAnalytics() {
        // Disable analytics tracking
        console.log('Analytics cookies disabled');
        // Clean up any existing analytics cookies/tracking
    }

    enablePreferences() {
        // Enable preference cookies
        console.log('Preference cookies enabled');
    }

    disablePreferences() {
        // Disable preference cookies
        console.log('Preference cookies disabled');
        // Clear any preference-related localStorage/cookies
    }

    showConsentNotification(message) {
        // Create temporary notification
        const notification = document.createElement('div');
        notification.className = 'fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg transform translate-x-full transition-transform duration-300';
        notification.style.zIndex = '10700';
        notification.textContent = message;

        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => {
            notification.classList.remove('translate-x-full');
            notification.classList.add('translate-x-0');
        }, 100);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.classList.add('translate-x-full');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    hideBanner(banner) {
        const bannerElement = banner || document.getElementById('cookie-consent-banner');
        if (bannerElement) {
            bannerElement.classList.remove('translate-y-0');
            bannerElement.classList.add('translate-y-full');
            setTimeout(() => bannerElement.remove(), 300);
        }
    }

    hideModal(modal) {
        modal.classList.remove('opacity-100');
        modal.classList.add('opacity-0');
        modal.querySelector('.transform').classList.remove('scale-100');
        modal.querySelector('.transform').classList.add('scale-95');
        setTimeout(() => modal.remove(), 300);
    }

    // Public method to revoke consent (for settings page)
    revokeConsent() {
        localStorage.removeItem(this.consentKey);
        this.consentData = null;
        this.showConsentBanner();
    }

    // Public method to get consent status
    hasConsent(type = null) {
        if (!this.consentData) return false;
        return type ? this.consentData[type] : true;
    }
}

// Initialize cookie consent when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.cookieConsent = new CookieConsent();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CookieConsent;
}