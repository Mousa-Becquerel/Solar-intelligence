/**
 * Artifact Panel Module
 * Manages the side panel for displaying dynamic content
 * Can be used for forms, maps, dashboards, visualizations, etc.
 */

export class ArtifactPanel {
    constructor() {
        this.panel = document.getElementById('artifact-panel');
        this.mainLayout = document.getElementById('main-layout');
        this.titleElement = document.getElementById('artifact-title');
        this.contentElement = document.getElementById('artifact-content');
        this.closeBtn = document.getElementById('artifact-close-btn');
        this.toggleBtn = document.getElementById('artifact-toggle-btn');

        this.isOpen = false;
        this.currentContent = null;

        this.init();
    }

    /**
     * Initialize event listeners
     */
    init() {
        if (!this.panel) {
            console.warn('Artifact panel not found in DOM');
            return;
        }

        // Close button click - toggles the panel
        this.closeBtn?.addEventListener('click', () => this.toggle());

        // Toggle button click - shows/hides the panel
        this.toggleBtn?.addEventListener('click', () => this.toggle());

        // Click on backdrop overlay (tablet/mobile only)
        if (this.mainLayout) {
            this.mainLayout.addEventListener('click', (e) => {
                // Check if click is on the backdrop (::after pseudo-element area)
                // Only works when artifact is open and on tablet/mobile
                if (this.isOpen &&
                    window.innerWidth <= 1200 &&
                    e.target === this.mainLayout) {
                    this.toggle();
                }
            });
        }

        // ESC key to toggle
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.toggle();
            }
        });
    }

    /**
     * Open the artifact panel with content
     * @param {Object} options - Configuration options
     * @param {string} options.title - Panel title
     * @param {string|HTMLElement} options.content - Content to display
     * @param {string} [options.type] - Content type (html, form, chart, etc.)
     */
    open(options = {}) {
        const { title = 'Artifact', content = '', type = 'html' } = options;

        if (!this.panel) {
            console.error('Artifact panel not available');
            return;
        }

        // Set title
        if (this.titleElement) {
            this.titleElement.textContent = title;
        }

        // Set content
        if (this.contentElement) {
            if (typeof content === 'string') {
                this.contentElement.innerHTML = content;
            } else if (content instanceof HTMLElement) {
                this.contentElement.innerHTML = '';
                this.contentElement.appendChild(content);
            }
        }

        // Add animation class
        this.contentElement?.classList.add('artifact-content-fade-enter');
        setTimeout(() => {
            this.contentElement?.classList.add('artifact-content-fade-enter-active');
        }, 10);

        // Update main layout state to open artifact
        if (this.mainLayout) {
            this.mainLayout.setAttribute('data-artifact-open', 'true');
        }

        this.isOpen = true;
        this.currentContent = { title, content, type };

        // Show the toggle button when artifact has content
        if (this.toggleBtn) {
            this.toggleBtn.style.display = 'flex';
        }

        // Focus trap - focus close button
        setTimeout(() => {
            this.closeBtn?.focus();
        }, 400);
    }

    /**
     * Toggle the artifact panel (minimize/restore)
     */
    toggle() {
        if (!this.panel) return;

        if (this.isOpen) {
            // Minimize - keep content cached
            if (this.mainLayout) {
                this.mainLayout.setAttribute('data-artifact-open', 'false');
            }
            this.isOpen = false;
            // Don't clear content - keep it cached for reopening
        } else {
            // Restore - show cached content
            if (this.currentContent) {
                if (this.mainLayout) {
                    this.mainLayout.setAttribute('data-artifact-open', 'true');
                }
                this.isOpen = true;
            }
        }
    }

    /**
     * Close the artifact panel (kept for backwards compatibility)
     */
    close() {
        this.toggle();
    }

    /**
     * Show loading state
     * @param {string} message - Loading message
     */
    showLoading(message = 'Loading...') {
        const loadingHTML = `
            <div class="artifact-loading">
                <div class="artifact-loading-spinner"></div>
                <p class="artifact-loading-text">${message}</p>
            </div>
        `;

        if (this.contentElement) {
            this.contentElement.innerHTML = loadingHTML;
        }
    }

    /**
     * Show empty state
     * @param {string} message - Empty state message
     */
    showEmpty(message = 'No content available') {
        const emptyHTML = `
            <div class="artifact-empty">
                <div class="artifact-empty-icon">📭</div>
                <p class="artifact-empty-text">${message}</p>
            </div>
        `;

        if (this.contentElement) {
            this.contentElement.innerHTML = emptyHTML;
        }
    }

    /**
     * Update panel content without closing
     * @param {string|HTMLElement} content - New content
     */
    updateContent(content) {
        if (!this.isOpen || !this.contentElement) return;

        // Fade out
        this.contentElement.style.opacity = '0';

        setTimeout(() => {
            if (typeof content === 'string') {
                this.contentElement.innerHTML = content;
            } else if (content instanceof HTMLElement) {
                this.contentElement.innerHTML = '';
                this.contentElement.appendChild(content);
            }

            // Fade in
            this.contentElement.style.opacity = '1';
        }, 150);
    }

    /**
     * Update panel title
     * @param {string} title - New title
     */
    updateTitle(title) {
        if (this.titleElement) {
            this.titleElement.textContent = title;
        }
    }

    /**
     * Check if panel is currently open
     * @returns {boolean}
     */
    isOpened() {
        return this.isOpen;
    }

    /**
     * Get current content
     * @returns {Object|null}
     */
    getCurrentContent() {
        return this.currentContent;
    }
}

// Create singleton instance
export const artifactPanel = new ArtifactPanel();
