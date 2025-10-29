/**
 * Main Application Entry Point
 * Modular architecture with clean separation of concerns
 */

// === CORE IMPORTS ===
import { api } from './modules/core/api.js';
import { appState } from './modules/core/state.js';

// === MODULE IMPORTS ===
import { conversationManager } from './modules/conversation/conversationManager.js';
import { suggestedQueries } from './modules/ui/suggestedQueries.js';
import { approvalFlow } from './modules/chat/approvalFlow.js';
import { plotHandler } from './modules/chat/plotHandler.js';

// === UTILITY IMPORTS ===
import { qs, scrollToBottom, createElement } from './utils/dom.js';
import { safeRenderMarkdown } from './utils/markdown.js';

// === GLOBAL CONFIGURATION ===
const CONFIG = {
    SUGGESTED_QUERIES_INIT_DELAY: 100,
    AUTO_SCROLL_DELAY: 100
};

// === APPLICATION CLASS ===
class SolarIntelligenceApp {
    constructor() {
        this.chatMessages = qs('#chat-messages');
        this.chatWrapper = qs('.chat-messages-wrapper');
        this.userInput = qs('#user-input');
        this.sendBtn = qs('#send-btn');
        this.agentSelect = qs('#agent-select');
        this.sidebar = qs('#sidebar');
        this.sidebarToggle = qs('#sidebar-toggle');
        this.logoutBtn = qs('#logout-btn');
    }

    /**
     * Initialize the application
     */
    async initialize() {
        console.log('🚀 Initializing Solar Intelligence App...');

        try {
            // Setup UI components immediately (no async needed)
            this.setupEventListeners();
            this.setupSidebar();
            this.setupAgentSelector();

            // Show welcome message and queries immediately
            this.updateWelcomeMessage();
            this.updateWelcomeMessageVisibility();
            suggestedQueries.initialize();

            // Show loading skeleton for conversations
            conversationManager.showLoadingSkeleton();

            // Load data in parallel for faster perceived performance
            await Promise.all([
                this.loadCurrentUser(),
                conversationManager.initialize()
            ]);

            console.log('✅ Application initialized successfully');

        } catch (error) {
            console.error('❌ Failed to initialize application:', error);
            this.showError('Failed to initialize application. Please refresh the page.');
        }
    }

    /**
     * Load current user information
     */
    async loadCurrentUser() {
        try {
            const user = await api.getCurrentUser();
            appState.setCurrentUser(user);

            // Update UI with user info
            const userNameEl = qs('#user-name');
            const userRoleEl = qs('#user-role');

            if (userNameEl) userNameEl.textContent = user.full_name || user.email || user.username || 'User';
            if (userRoleEl) userRoleEl.textContent = user.role || '';

            // Show admin button if user is admin
            if (user.role === 'admin') {
                const adminBtn = qs('#admin-btn');
                if (adminBtn) adminBtn.style.display = 'flex';
            }

        } catch (error) {
            console.error('Error loading user:', error);
            // Redirect to login if not authenticated
            window.location.href = '/auth/login';
        }
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Send message on button click
        if (this.sendBtn) {
            this.sendBtn.addEventListener('click', () => this.sendMessage());
        }

        // Send message on Enter key
        if (this.userInput) {
            this.userInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        // Agent selector change
        if (this.agentSelect) {
            this.agentSelect.addEventListener('change', (e) => {
                appState.setAgentType(e.target.value);
                this.updateWelcomeMessage();
            });
        }

        // Logout button
        if (this.logoutBtn) {
            this.logoutBtn.addEventListener('click', () => {
                window.location.href = '/auth/logout';
            });
        }

        // Listen for conversation selection events
        window.addEventListener('conversationSelected', (e) => {
            this.handleConversationSelected(e.detail);
        });

        // Listen for new chat events
        window.addEventListener('newChatStarted', () => {
            this.handleNewChatStarted();
        });

        // Listen for submitting state changes to disable/enable send button
        // Note: Keep input enabled so user can type their next query while waiting
        appState.subscribe('isSubmittingMessage', (isSubmitting) => {
            if (this.sendBtn) {
                this.sendBtn.disabled = isSubmitting;
                this.sendBtn.style.opacity = isSubmitting ? '0.5' : '1';
                this.sendBtn.style.cursor = isSubmitting ? 'not-allowed' : 'pointer';
            }
            // Input field remains enabled so user can prepare next query while waiting
        });
    }

    /**
     * Setup sidebar toggle
     */
    setupSidebar() {
        if (!this.sidebar || !this.sidebarToggle) return;

        this.sidebarToggle.addEventListener('click', () => {
            const isExpanded = this.sidebar.getAttribute('data-expanded') === 'true';
            this.sidebar.setAttribute('data-expanded', !isExpanded);
            appState.setSidebarExpanded(!isExpanded);
        });
    }

    /**
     * Setup agent selector
     */
    setupAgentSelector() {
        if (!this.agentSelect) return;

        // Set initial agent type
        const initialAgent = this.agentSelect.value || 'market';
        appState.setAgentType(initialAgent);
    }

    /**
     * Send message to agent
     */
    async sendMessage() {
        const message = this.userInput?.value?.trim();

        if (!message) {
            console.log('Empty message, not sending');
            return;
        }

        // Check if already submitting
        if (appState.isSubmitting()) {
            console.log('⏸️ Already submitting, ignoring duplicate request');
            return;
        }

        console.log('💬 Sending message:', message);

        // Set submitting flag
        appState.setSubmitting(true);

        try {
            const agentType = appState.getAgentType();
            let conversationId = appState.getState('currentConversationId');

            // Add user message to UI
            this.addUserMessage(message);

            // Hide suggested queries
            suggestedQueries.hide();

            // Clear input
            if (this.userInput) this.userInput.value = '';

            // Create conversation if needed
            if (!conversationId) {
                conversationId = await conversationManager.createConversation();
            }

            // Show loading indicator
            this.showLoadingIndicator();

            // Start SSE stream
            await this.startMessageStream(conversationId, message, agentType);

        } catch (error) {
            console.error('Error sending message:', error);
            this.showError('Failed to send message. Please try again.');
        } finally {
            appState.setSubmitting(false);
        }
    }

    /**
     * Add user message to chat
     * @param {string} message - Message text
     */
    addUserMessage(message) {
        const messageContainer = createElement('div', {
            classes: 'message-container',
            attributes: {
                'data-msg-id': `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                'data-msg-sender': 'user',
                'data-msg-type': 'string'
            }
        });

        const messageDiv = createElement('div', {
            classes: 'message user-message',
            innerHTML: safeRenderMarkdown(message)
        });

        messageContainer.appendChild(messageDiv);
        this.chatWrapper.appendChild(messageContainer);

        scrollToBottom(this.chatMessages);

        // Update visibility
        suggestedQueries.updateVisibility();
        this.updateWelcomeMessageVisibility();
    }

    /**
     * Show loading indicator
     */
    showLoadingIndicator() {
        const loadingDiv = createElement('div', {
            classes: 'message-container loading-container',
            attributes: { id: 'current-loading' }
        });

        loadingDiv.innerHTML = `
            <div class="message bot-message">
                <div class="loading-spinner">
                    <div class="spinner-ring"></div>
                    <div class="spinner-ring"></div>
                    <div class="spinner-ring"></div>
                </div>
                <span class="loading-text">Analyzing data...</span>
            </div>
        `;

        this.chatWrapper.appendChild(loadingDiv);
        scrollToBottom(this.chatMessages);
    }

    /**
     * Remove loading indicator
     */
    removeLoadingIndicator() {
        const loading = qs('#current-loading');
        if (loading) loading.remove();
    }

    /**
     * Handle JSON response (for price agent)
     * @param {Response} response - Fetch response
     * @param {string} agentType - Agent type
     */
    async handleJsonResponse(response, agentType) {
        try {
            const data = await response.json();
            console.log('📦 JSON Response:', data);

            this.removeLoadingIndicator();

            // Price agent returns {response: [...]}
            const responseData = data.response || [];

            for (const item of responseData) {
                if (item.type === 'interactive_chart' && item.plot_data) {
                    // Create plot using plot handler
                    const eventData = {
                        type: 'plot',
                        content: item.plot_data
                    };
                    plotHandler.createPlot(
                        eventData,
                        agentType,
                        this.chatWrapper,
                        this.chatMessages
                    );
                } else if (item.type === 'chart' && item.artifact) {
                    // Static chart image
                    this.createImageMessage(item.value, item.artifact, agentType);
                } else if (item.type === 'table' && item.table_data) {
                    // Table data - render as HTML table
                    this.createTableMessage(item.value, item.table_data, agentType);
                } else if (item.type === 'string') {
                    // Text message only (removed || item.value to avoid catching tables)
                    this.createTextMessage(item.value || item.content || String(item), agentType);
                } else if (item.value) {
                    // Fallback for other types with value
                    this.createTextMessage(String(item.value), agentType);
                }
            }

            this.updateWelcomeMessageVisibility();
            appState.setSubmitting(false);

        } catch (error) {
            console.error('Error handling JSON response:', error);
            this.removeLoadingIndicator();
            this.showError('Failed to process response');
            appState.setSubmitting(false);
        }
    }

    /**
     * Create text message from bot
     * @param {string} text - Message text
     * @param {string} agentType - Agent type
     */
    createTextMessage(text, agentType) {
        const messageContainer = this.createBotMessageContainer(agentType);
        const messageDiv = messageContainer.querySelector('.message');
        messageDiv.innerHTML = safeRenderMarkdown(text);
        scrollToBottom(this.chatMessages);
    }

    /**
     * Create image message from bot
     * @param {string} description - Image description
     * @param {string} imageUrl - Image URL
     * @param {string} agentType - Agent type
     */
    createImageMessage(description, imageUrl, agentType) {
        const messageContainer = this.createBotMessageContainer(agentType);
        const messageDiv = messageContainer.querySelector('.message');

        const html = `
            <div class="chart-container">
                ${description ? `<p>${description}</p>` : ''}
                <img src="${imageUrl}" alt="Chart" style="max-width: 100%; height: auto;">
            </div>
        `;
        messageDiv.innerHTML = html;
        scrollToBottom(this.chatMessages);
    }

    /**
     * Create table message from bot
     * @param {string} description - Table description
     * @param {Array} tableData - Table data
     * @param {string} agentType - Agent type
     */
    createTableMessage(description, tableData, agentType) {
        const messageContainer = this.createBotMessageContainer(agentType);
        const messageDiv = messageContainer.querySelector('.message');

        if (!Array.isArray(tableData) || tableData.length === 0) {
            messageDiv.innerHTML = `<p>${description || 'No data available'}</p>`;
            return;
        }

        // Get table headers from first row
        const headers = Object.keys(tableData[0]);

        let html = description ? `<p>${description}</p>` : '';
        html += '<div class="table-container"><table class="data-table">';
        html += '<thead><tr>';
        headers.forEach(header => {
            html += `<th>${header}</th>`;
        });
        html += '</tr></thead><tbody>';

        tableData.forEach(row => {
            html += '<tr>';
            headers.forEach(header => {
                html += `<td>${row[header] !== null && row[header] !== undefined ? row[header] : ''}</td>`;
            });
            html += '</tr>';
        });

        html += '</tbody></table></div>';
        messageDiv.innerHTML = html;
        scrollToBottom(this.chatMessages);
    }

    /**
     * Start message stream via SSE
     * @param {number} conversationId - Conversation ID
     * @param {string} message - Message text
     * @param {string} agentType - Agent type
     */
    async startMessageStream(conversationId, message, agentType) {
        try {
            // Send message and get streaming response
            const response = await api.sendChatMessage(conversationId, message, agentType);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            // Check if response is JSON (for price agent) or SSE stream
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                // Handle JSON response (price agent)
                return await this.handleJsonResponse(response, agentType);
            }

            // Read the response as a stream
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            let messageContainer = null;
            let messageDiv = null;
            let fullResponse = '';

            // Process the stream
            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    console.log('✅ Stream complete');
                    this.removeLoadingIndicator();
                    this.updateWelcomeMessageVisibility();
                    appState.setSubmitting(false);
                    break;
                }

                // Decode the chunk
                const chunk = decoder.decode(value, { stream: true });

                // Split by SSE message boundaries
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6).trim();

                        if (!data) continue;

                        try {
                            const eventData = JSON.parse(data);
                            console.log('📨 SSE Event:', eventData.type, eventData);

                            // Handle different event types
                            switch (eventData.type) {
                                case 'status':
                                    this.handleStatusEvent(eventData);
                                    break;

                                case 'chunk':
                                case 'text':
                                    if (!messageContainer) {
                                        this.removeLoadingIndicator();
                                        messageContainer = this.createBotMessageContainer(agentType);
                                        messageDiv = messageContainer.querySelector('.message');
                                    }
                                    fullResponse += eventData.content || '';
                                    messageDiv.innerHTML = safeRenderMarkdown(fullResponse);
                                    scrollToBottom(this.chatMessages);
                                    break;

                                case 'plot':
                                    this.removeLoadingIndicator();
                                    messageContainer = plotHandler.createPlot(
                                        eventData,
                                        agentType,
                                        this.chatWrapper,
                                        this.chatMessages
                                    );
                                    messageDiv = messageContainer.querySelector('.message');
                                    break;

                                case 'approval_request':
                                    this.removeLoadingIndicator();
                                    approvalFlow.displayApprovalRequest(eventData);
                                    break;

                                case 'done':
                                    console.log('✅ Done event received');
                                    break;

                                case 'error':
                                    this.handleErrorEvent(eventData);
                                    throw new Error(eventData.message);
                            }

                        } catch (parseError) {
                            console.error('Error parsing SSE data:', parseError, data);
                        }
                    }
                }
            }

        } catch (error) {
            console.error('Stream error:', error);
            this.removeLoadingIndicator();
            this.showError('Failed to get response. Please try again.');
            appState.setSubmitting(false);
            throw error;
        }
    }

    /**
     * Create bot message container
     * @param {string} agentType - Agent type
     * @returns {HTMLElement}
     */
    createBotMessageContainer(agentType) {
        const messageContainer = createElement('div', {
            classes: 'message-container',
            attributes: {
                'data-msg-id': `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                'data-msg-sender': 'bot',
                'data-msg-type': 'streaming'
            }
        });

        const messageDiv = createElement('div', {
            classes: ['message', 'bot-message', `${agentType}-agent`]
        });

        messageContainer.appendChild(messageDiv);
        this.chatWrapper.appendChild(messageContainer);

        return messageContainer;
    }

    /**
     * Handle status event
     * @param {object} eventData - Event data
     */
    handleStatusEvent(eventData) {
        const loadingText = qs('#current-loading .loading-text');
        if (loadingText) {
            loadingText.textContent = eventData.message || 'Processing...';
        }
    }

    /**
     * Handle error event
     * @param {object} eventData - Event data
     */
    handleErrorEvent(eventData) {
        this.removeLoadingIndicator();
        this.showError(eventData.message || 'An error occurred');
        if (this.currentEventSource) {
            this.currentEventSource.close();
        }
        appState.setSubmitting(false);
    }

    /**
     * Show error message
     * @param {string} message - Error message
     */
    showError(message) {
        const errorDiv = createElement('div', {
            classes: 'error-message',
            textContent: message
        });

        errorDiv.style.padding = '1rem';
        errorDiv.style.backgroundColor = '#fee2e2';
        errorDiv.style.color = '#991b1b';
        errorDiv.style.borderRadius = '8px';
        errorDiv.style.margin = '1rem';

        this.chatWrapper.appendChild(errorDiv);
        scrollToBottom(this.chatMessages);

        // Auto-remove after 5 seconds
        setTimeout(() => errorDiv.remove(), 5000);
    }

    /**
     * Handle conversation selected
     * @param {object} detail - Event detail
     */
    handleConversationSelected(detail) {
        const { conversationId, messages } = detail;

        console.log(`Loading conversation ${conversationId} with ${messages.length} messages`);

        // Clear chat
        this.chatWrapper.innerHTML = '';

        // Render messages
        messages.forEach(msg => {
            this.renderMessage(msg);
        });

        // Update visibility
        suggestedQueries.updateVisibility();
        this.updateWelcomeMessageVisibility();

        scrollToBottom(this.chatMessages);
    }

    /**
     * Handle new chat started
     */
    handleNewChatStarted() {
        // Show suggested queries only if not submitting
        if (!appState.isSubmitting()) {
            console.log('📝 New chat created - showing suggested queries');
            suggestedQueries.show();
        } else {
            console.log('⏸️ New chat created during message submission - NOT showing queries');
        }

        // Update welcome message
        this.updateWelcomeMessage();
        this.updateWelcomeMessageVisibility();
    }

    /**
     * Render a single message
     * @param {object} msg - Message object
     */
    renderMessage(msg) {
        const isUser = msg.sender === 'user';
        const agentType = msg.agent_type || 'market';

        // Parse content
        let parsed = null;
        try {
            parsed = typeof msg.content === 'string' ? JSON.parse(msg.content) : msg.content;
        } catch {
            parsed = { type: 'string', value: String(msg.content) };
        }

        // Handle different message types
        if (!isUser && parsed.type === 'plot' && parsed.value) {
            // Render plot message from history
            const eventData = {
                type: 'plot',
                content: parsed.value
            };
            plotHandler.createPlot(
                eventData,
                agentType,
                this.chatWrapper,
                this.chatMessages
            );
        } else {
            // Render text message
            const messageContainer = createElement('div', {
                classes: 'message-container',
                attributes: {
                    'data-msg-id': msg.id || `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                    'data-msg-sender': msg.sender,
                    'data-msg-type': parsed.type || typeof msg.content
                }
            });

            const content = parsed.value || parsed.content || String(parsed);

            const messageDiv = createElement('div', {
                classes: ['message', isUser ? 'user-message' : 'bot-message', !isUser ? `${agentType}-agent` : ''],
                innerHTML: safeRenderMarkdown(content)
            });

            messageContainer.appendChild(messageDiv);
            this.chatWrapper.appendChild(messageContainer);
        }
    }

    /**
     * Update welcome message based on agent
     */
    updateWelcomeMessage() {
        const welcomeMessage = qs('#welcome-message');
        if (!welcomeMessage) return;

        const agentType = appState.getAgentType();
        const agentTitles = {
            market: 'PV Capacity Analysis',
            market_intel: 'Market Intelligence',
            price: 'Price Analysis',
            news: 'News & Insights',
            digitalization: 'Digitalization Expert'
        };

        const title = agentTitles[agentType] || 'Solar Intelligence';
        const titleEl = welcomeMessage.querySelector('.welcome-title');
        if (titleEl) {
            titleEl.textContent = title;
        }

        // Show welcome message with fade-in
        welcomeMessage.style.opacity = '1';
    }

    /**
     * Update welcome message visibility
     * Hide if there are messages, show if empty
     */
    updateWelcomeMessageVisibility() {
        const welcomeMessage = qs('#welcome-message');
        if (!welcomeMessage) return;

        const messageCount = this.chatWrapper ? this.chatWrapper.querySelectorAll('.message-container').length : 0;

        if (messageCount === 0) {
            welcomeMessage.style.display = 'flex';
        } else {
            welcomeMessage.style.display = 'none';
        }
    }
}

// === INITIALIZE APPLICATION ===
let app;

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🌐 DOM Content Loaded');

    try {
        // Create and initialize app
        app = new SolarIntelligenceApp();
        await app.initialize();

        // Make app globally accessible for debugging
        window.app = app;

    } catch (error) {
        console.error('Fatal error during initialization:', error);
    }
});

// === EXPORT FOR EXTERNAL ACCESS ===
export { app, appState, api, conversationManager, suggestedQueries, approvalFlow, plotHandler };
