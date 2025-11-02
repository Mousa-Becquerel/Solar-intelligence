/**
 * Conversation Manager Module
 * Manages conversation list, selection, creation, and deletion
 */

import { api } from '../core/api.js';
import { appState } from '../core/state.js';
import { createElement, qs, qsa, clearElement } from '../../utils/dom.js';

export class ConversationManager {
    constructor() {
        this.list = qs('#conversation-list');
        this.countElement = qs('#conversations-count');
        this.newChatBtn = qs('#new-chat-btn');
        this.newChatCollapsedBtn = qs('#new-chat-collapsed');
        this.confirmModal = null;

        this.setupEventListeners();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Listen for conversation list changes
        appState.subscribe('conversations', () => {
            this.render();
        });

        // Listen for current conversation changes
        appState.subscribe('currentConversationId', () => {
            this.render();
        });

        // New chat buttons
        if (this.newChatBtn) {
            this.newChatBtn.addEventListener('click', () => this.startNewChat());
        }
        if (this.newChatCollapsedBtn) {
            this.newChatCollapsedBtn.addEventListener('click', () => this.startNewChat());
        }
    }

    /**
     * Initialize - fetch and render conversations
     */
    async initialize() {
        await this.fetchConversations();
    }

    /**
     * Fetch conversations from API
     */
    async fetchConversations() {
        try {
            const data = await api.getConversations();
            appState.setConversations(data.conversations || []);
        } catch (error) {
            console.error('Error fetching conversations:', error);
            appState.setConversations([]);
        }
    }

    /**
     * Show loading skeleton while conversations are being fetched
     */
    showLoadingSkeleton() {
        if (!this.list) return;

        clearElement(this.list);

        // Create 3 skeleton items to indicate loading
        for (let i = 0; i < 3; i++) {
            const skeleton = createElement('li', {
                classes: ['conversation-item', 'skeleton'],
                innerHTML: `
                    <div class="skeleton-line" style="width: 80%; height: 14px; background: #e5e7eb; border-radius: 4px; margin-bottom: 8px;"></div>
                    <div class="skeleton-line" style="width: 60%; height: 12px; background: #e5e7eb; border-radius: 4px;"></div>
                `
            });
            skeleton.style.cssText = 'padding: 12px; opacity: 0.6; pointer-events: none;';
            this.list.appendChild(skeleton);
        }
    }

    /**
     * Render conversation list
     */
    render() {
        if (!this.list) return;

        const conversations = appState.getState('conversations');
        const currentConversationId = appState.getState('currentConversationId');

        // Clear list (including any skeleton loaders)
        clearElement(this.list);

        // Update conversation count
        if (this.countElement) {
            this.countElement.textContent = conversations.length;
        }

        // Render each conversation
        conversations.forEach(conv => {
            const li = this.createConversationItem(conv, currentConversationId);
            this.list.appendChild(li);
        });
    }

    /**
     * Create conversation list item
     * @param {object} conv - Conversation object
     * @param {number} currentConversationId - Currently selected conversation ID
     * @returns {HTMLElement}
     */
    createConversationItem(conv, currentConversationId) {
        const classes = ['conversation-item'];
        if (conv.id === currentConversationId) {
            classes.push('active');
        }

        const li = createElement('li', { classes });

        // Create title span
        const titleSpan = createElement('span', {
            classes: 'conversation-title',
            textContent: conv.preview || conv.title || `Conversation ${conv.id}`,
            attributes: {
                title: conv.preview || conv.title || `Conversation ${conv.id}`
            }
        });

        // Create delete button
        const delBtn = createElement('button', {
            classes: 'delete-chat-btn',
            attributes: {
                'aria-label': 'Delete conversation'
            },
            innerHTML: `<svg width="18" height="18" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <rect x="5" y="8" width="1.5" height="6" rx="0.75" fill="currentColor"/>
                <rect x="9.25" y="8" width="1.5" height="6" rx="0.75" fill="currentColor"/>
                <rect x="13.5" y="8" width="1.5" height="6" rx="0.75" fill="currentColor"/>
                <path d="M4 6.5C4 5.94772 4.44772 5.5 5 5.5H15C15.5523 5.5 16 5.94772 16 6.5V7.5C16 8.05228 15.5523 8.5 15 8.5H5C4.44772 8.5 4 8.05228 4 7.5V6.5Z" fill="currentColor"/>
                <rect x="7.5" y="2.5" width="5" height="2" rx="1" fill="currentColor"/>
            </svg>`
        });

        delBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            await this.confirmDelete(conv.id);
        });

        // Click to select conversation
        li.addEventListener('click', () => this.selectConversation(conv.id));

        li.appendChild(titleSpan);
        li.appendChild(delBtn);

        return li;
    }

    /**
     * Confirm and delete conversation
     * @param {number} convId - Conversation ID
     */
    async confirmDelete(convId) {
        console.log('Delete button clicked for conversation:', convId);

        // Show custom confirmation modal
        const shouldDelete = await this.showConfirmModal(
            'Delete Conversation?',
            'Are you sure you want to delete this conversation? This action cannot be undone and all messages will be permanently removed.',
            'Delete',
            'Cancel'
        );

        if (shouldDelete) {
            await this.deleteConversation(convId);
        }
    }

    /**
     * Show custom confirmation modal
     * @param {string} title - Modal title
     * @param {string} message - Modal message
     * @param {string} confirmText - Confirm button text
     * @param {string} cancelText - Cancel button text
     * @returns {Promise<boolean>} - User's choice
     */
    async showConfirmModal(title, message, confirmText = 'Confirm', cancelText = 'Cancel') {
        return new Promise((resolve) => {
            // Create modal HTML
            const modalHTML = `
                <div class="confirm-modal" id="delete-confirm-modal">
                    <div class="confirm-modal-content">
                        <div class="confirm-modal-header">
                            <div class="confirm-modal-icon">⚠️</div>
                            <h3 class="confirm-modal-title">${title}</h3>
                        </div>
                        <div class="confirm-modal-body">
                            ${message}
                        </div>
                        <div class="confirm-modal-actions">
                            <button class="confirm-modal-btn confirm-modal-btn-cancel" data-action="cancel">
                                ${cancelText}
                            </button>
                            <button class="confirm-modal-btn confirm-modal-btn-confirm" data-action="confirm">
                                ${confirmText}
                            </button>
                        </div>
                    </div>
                </div>
            `;

            // Add to DOM
            document.body.insertAdjacentHTML('beforeend', modalHTML);

            const modal = document.getElementById('delete-confirm-modal');

            // Show modal with animation
            requestAnimationFrame(() => {
                modal.classList.add('show');
            });

            // Handle button clicks
            const handleClick = (e) => {
                const action = e.target.dataset.action;
                if (action) {
                    // Hide modal
                    modal.classList.remove('show');

                    // Remove from DOM after animation
                    setTimeout(() => {
                        modal.remove();
                    }, 300);

                    // Resolve promise
                    resolve(action === 'confirm');
                }
            };

            modal.addEventListener('click', (e) => {
                // Close on backdrop click
                if (e.target === modal) {
                    handleClick({ target: { dataset: { action: 'cancel' } } });
                }
            });

            modal.querySelectorAll('[data-action]').forEach(btn => {
                btn.addEventListener('click', handleClick);
            });

            // Handle ESC key
            const handleEscape = (e) => {
                if (e.key === 'Escape') {
                    handleClick({ target: { dataset: { action: 'cancel' } } });
                    document.removeEventListener('keydown', handleEscape);
                }
            };
            document.addEventListener('keydown', handleEscape);
        });
    }

    /**
     * Show error modal
     * @param {string} title - Modal title
     * @param {string} message - Error message
     */
    async showErrorModal(title, message) {
        return new Promise((resolve) => {
            // Create modal HTML
            const modalHTML = `
                <div class="confirm-modal" id="error-modal">
                    <div class="confirm-modal-content">
                        <div class="confirm-modal-header">
                            <div class="confirm-modal-icon" style="background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);">❌</div>
                            <h3 class="confirm-modal-title">${title}</h3>
                        </div>
                        <div class="confirm-modal-body">
                            ${message}
                        </div>
                        <div class="confirm-modal-actions">
                            <button class="confirm-modal-btn confirm-modal-btn-cancel" data-action="ok">
                                OK
                            </button>
                        </div>
                    </div>
                </div>
            `;

            // Add to DOM
            document.body.insertAdjacentHTML('beforeend', modalHTML);

            const modal = document.getElementById('error-modal');

            // Show modal with animation
            requestAnimationFrame(() => {
                modal.classList.add('show');
            });

            // Handle button clicks
            const handleClick = () => {
                // Hide modal
                modal.classList.remove('show');

                // Remove from DOM after animation
                setTimeout(() => {
                    modal.remove();
                }, 300);

                resolve();
            };

            modal.addEventListener('click', (e) => {
                // Close on backdrop click
                if (e.target === modal) {
                    handleClick();
                }
            });

            modal.querySelector('[data-action="ok"]').addEventListener('click', handleClick);

            // Handle ESC key
            const handleEscape = (e) => {
                if (e.key === 'Escape') {
                    handleClick();
                    document.removeEventListener('keydown', handleEscape);
                }
            };
            document.addEventListener('keydown', handleEscape);
        });
    }

    /**
     * Delete conversation
     * @param {number} convId - Conversation ID
     */
    async deleteConversation(convId) {
        try {
            console.log('Attempting to delete conversation:', convId);

            await api.deleteConversation(convId);

            console.log('Conversation deleted successfully');

            // Remove from state
            appState.removeConversation(convId);

            // Refresh list
            await this.fetchConversations();

            // If deleted conversation was active, select next or start new
            if (convId === appState.getState('currentConversationId')) {
                const conversations = appState.getState('conversations');
                if (conversations.length > 0) {
                    await this.selectConversation(conversations[0].id);
                } else {
                    await this.startNewChat();
                }
            }

        } catch (error) {
            console.error('Error deleting conversation:', error);

            // Check if it's a "not found" error - conversation already deleted
            if (error.message && error.message.includes('not found')) {
                console.log('Conversation already deleted, refreshing list');

                // Remove from state
                appState.removeConversation(convId);

                // Refresh list silently
                await this.fetchConversations();

                // If deleted conversation was active, select next or start new
                if (convId === appState.getState('currentConversationId')) {
                    const conversations = appState.getState('conversations');
                    if (conversations.length > 0) {
                        await this.selectConversation(conversations[0].id);
                    } else {
                        await this.startNewChat();
                    }
                }
            } else {
                // Show error only for real errors, not "not found"
                await this.showErrorModal(
                    'Delete Failed',
                    'Failed to delete conversation. Please try again.'
                );
            }
        }
    }

    /**
     * Select conversation and load messages
     * @param {number} id - Conversation ID
     */
    async selectConversation(id) {
        if (!id) {
            console.error('No conversation ID provided');
            return;
        }

        console.log('Selecting conversation:', id);

        try {
            // Set as current conversation
            appState.setCurrentConversation(id);

            // Fetch conversation data
            const data = await api.getConversation(id);

            console.log('Conversation data received:', data);

            // Handle both old format (array) and new format (object with messages array)
            const messages = Array.isArray(data) ? data : (data.messages || []);
            console.log('Number of messages:', messages.length);

            if (data.total_count && data.returned_count) {
                console.log(`Loaded ${data.returned_count} of ${data.total_count} total messages`);
            }

            // Store in history
            appState.addConversationToHistory(id, messages);

            // Dispatch event for message renderer to handle
            window.dispatchEvent(new CustomEvent('conversationSelected', {
                detail: { conversationId: id, messages }
            }));

        } catch (error) {
            console.error('Error loading conversation:', error);
            alert('Failed to load conversation. Please try again.');
        }
    }

    /**
     * Start new chat
     */
    async startNewChat() {
        console.log('🆕 Starting new chat...');

        try {
            const agentType = appState.getAgentType();

            // Clear current conversation
            appState.setCurrentConversation(null);

            // Clear messages
            const chatWrapper = qs('.chat-messages-wrapper');
            if (chatWrapper) {
                clearElement(chatWrapper);
            }

            // Update UI
            this.render();

            // Dispatch event for other modules
            window.dispatchEvent(new CustomEvent('newChatStarted', {
                detail: { agentType }
            }));

            console.log('✅ New chat started');

        } catch (error) {
            console.error('Error starting new chat:', error);

            // Show error message
            const chatWrapper = qs('.chat-messages-wrapper');
            if (chatWrapper) {
                const errorMsg = createElement('div', {
                    classes: 'error-message',
                    textContent: 'Failed to start new chat. Please refresh the page.',
                    attributes: {
                        style: 'color: red; padding: 1rem; text-align: center;'
                    }
                });
                chatWrapper.appendChild(errorMsg);
            }
        }
    }

    /**
     * Create new conversation (when sending first message)
     * @returns {number} New conversation ID
     */
    async createConversation() {
        try {
            const data = await api.createConversation();
            const newConvId = data.id;

            if (!newConvId) {
                throw new Error('No conversation ID received from server');
            }

            console.log('Created new conversation:', newConvId);

            // Set as current
            appState.setCurrentConversation(newConvId);

            // Refresh list in background
            this.fetchConversations();

            return newConvId;

        } catch (error) {
            console.error('Error creating conversation:', error);
            throw error;
        }
    }

}

// Create singleton instance
export const conversationManager = new ConversationManager();
