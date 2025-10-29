/**
 * Suggested Queries Module
 * Manages suggested query UI and interactions
 */

import { appState } from '../core/state.js';
import { hideElement, showElement, qs } from '../../utils/dom.js';

export class SuggestedQueries {
    constructor() {
        this.container = qs('#suggested-queries-container');
        this.wrapper = qs('.suggested-queries-wrapper');
        this.userInput = qs('#user-input');
        this.queries = window.SUGGESTED_QUERIES || {};

        this.setupEventListeners();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Listen for agent type changes
        appState.subscribe('currentAgentType', (agentType) => {
            this.updateQueries(agentType);
        });

        // Listen for submitting state changes
        appState.subscribe('isSubmittingMessage', (isSubmitting) => {
            if (!isSubmitting) {
                this.updateVisibility();
            }
        });

        // Hide when user starts typing
        if (this.userInput) {
            this.userInput.addEventListener('input', (e) => {
                console.log('⌨️ Input event fired, value:', e.target.value, 'isSubmitting:', appState.isSubmitting());

                // Don't interfere if we're currently submitting a message
                if (appState.isSubmitting()) {
                    console.log('⏸️ Blocked by isSubmitting flag');
                    return;
                }

                if (e.target.value.trim().length > 0) {
                    console.log('Input has text, hiding queries');
                    this.hide();
                } else {
                    console.log('Input is empty, checking visibility');
                    this.updateVisibility();
                }
            });
        }
    }

    /**
     * Initialize suggested queries for current agent
     */
    initialize() {
        const agentType = appState.getAgentType();
        this.updateQueries(agentType);
        this.updateVisibility();
    }

    /**
     * Update suggested queries based on agent type
     * @param {string} agentType - Agent type (market, price, news, etc.)
     */
    updateQueries(agentType) {
        if (!this.wrapper || !this.queries) return;

        // Clear existing queries
        this.wrapper.innerHTML = '';

        // Get queries for this agent type
        const queries = this.queries[agentType] || this.queries.market || [];

        // Create query items
        queries.forEach((query, index) => {
            const queryItem = document.createElement('div');
            queryItem.className = 'suggested-query-item';
            queryItem.setAttribute('data-query', query.text);
            queryItem.style.animationDelay = `${index * 0.05}s`;

            queryItem.innerHTML = `
                <span class="suggested-query-icon">${query.icon}</span>
                <span class="suggested-query-text">${query.text}</span>
            `;

            // Add click handler
            queryItem.addEventListener('click', () => {
                this.handleQueryClick(query.text);
            });

            this.wrapper.appendChild(queryItem);
        });

        // Add 'loaded' class to show queries with animation
        if (this.container) {
            // Use requestAnimationFrame to ensure DOM has updated
            requestAnimationFrame(() => {
                this.container.classList.add('loaded');
            });
        }
    }

    /**
     * Handle click on a suggested query
     * @param {string} queryText - Query text
     */
    handleQueryClick(queryText) {
        if (!this.userInput) return;

        // Set the query text in the input
        this.userInput.value = queryText;

        // Focus the input
        this.userInput.focus();

        // Hide suggested queries
        this.hide();

        // Dispatch input event to trigger any listeners
        this.userInput.dispatchEvent(new Event('input', { bubbles: true }));
    }

    /**
     * Hide suggested queries
     */
    hide() {
        console.log('🔴 hideSuggestedQueries called, container:', this.container);
        if (this.container) {
            console.log('Before hiding - classes:', this.container.className);
            this.container.classList.add('hidden');
            console.log('After hiding - classes:', this.container.className);
            console.log('Display style:', window.getComputedStyle(this.container).display);
        } else {
            console.error('❌ suggested-queries-container not found!');
        }
    }

    /**
     * Show suggested queries
     */
    show() {
        console.log('🟢 showSuggestedQueries called, container:', this.container);
        if (this.container) {
            console.log('Before showing - classes:', this.container.className);
            this.container.classList.remove('hidden');
            this.container.classList.add('loaded'); // Ensure queries are visible
            console.log('After showing - classes:', this.container.className);
            console.log('Display style:', window.getComputedStyle(this.container).display);
        }
    }

    /**
     * Update visibility based on message count
     * Only show when conversation is empty
     */
    updateVisibility() {
        const chatWrapper = qs('.chat-messages-wrapper');
        const messageCount = chatWrapper ? chatWrapper.querySelectorAll('.message-container').length : 0;

        console.log('📊 updateSuggestedQueriesVisibility - messageCount:', messageCount);

        if (messageCount === 0) {
            console.log('No messages, showing queries');
            this.show();
        } else {
            console.log('Messages exist, hiding queries');
            this.hide();
        }
    }

    /**
     * Check if queries should be shown (helper for external calls)
     * @param {boolean} excludeSubmitting - Don't show if currently submitting
     * @returns {boolean}
     */
    shouldShow(excludeSubmitting = false) {
        if (excludeSubmitting && appState.isSubmitting()) {
            return false;
        }

        const chatWrapper = qs('.chat-messages-wrapper');
        const messageCount = chatWrapper ? chatWrapper.querySelectorAll('.message-container').length : 0;

        return messageCount === 0;
    }
}

// Create singleton instance
export const suggestedQueries = new SuggestedQueries();
