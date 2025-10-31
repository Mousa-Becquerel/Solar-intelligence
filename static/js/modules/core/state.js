/**
 * State Management Module
 * Centralized application state with pub-sub pattern for reactive updates
 */

export class AppState {
    constructor() {
        this.state = {
            // User state
            currentUser: null,

            // Conversation state
            currentConversationId: null,
            conversations: [],
            conversationHistory: {},

            // UI state
            isSubmittingMessage: false,
            exportMode: false,
            sidebarExpanded: true,

            // Agent state
            currentAgentType: 'market',
            hiredAgents: window.hiredAgents || [],

            // Survey state
            surveysCompleted: {
                stage1: false,
                stage2: false
            }
        };

        // Listeners for state changes
        this.listeners = {};
    }

    /**
     * Subscribe to state changes for a specific key
     * @param {string} key - State key to watch
     * @param {function} callback - Callback function (receives new value)
     * @returns {function} Unsubscribe function
     */
    subscribe(key, callback) {
        if (!this.listeners[key]) {
            this.listeners[key] = [];
        }
        this.listeners[key].push(callback);

        // Return unsubscribe function
        return () => {
            this.listeners[key] = this.listeners[key].filter(cb => cb !== callback);
        };
    }

    /**
     * Update state and notify listeners
     * @param {string} key - State key to update
     * @param {*} value - New value
     */
    setState(key, value) {
        const oldValue = this.state[key];
        this.state[key] = value;

        // Only notify if value actually changed
        if (oldValue !== value && this.listeners[key]) {
            this.listeners[key].forEach(callback => {
                try {
                    callback(value, oldValue);
                } catch (error) {
                    console.error(`Error in state listener for "${key}":`, error);
                }
            });
        }
    }

    /**
     * Update multiple state keys at once
     * @param {object} updates - Object with key-value pairs to update
     */
    setMultipleStates(updates) {
        Object.entries(updates).forEach(([key, value]) => {
            this.setState(key, value);
        });
    }

    /**
     * Get current state value
     * @param {string} key - State key
     * @returns {*} Current value
     */
    getState(key) {
        return this.state[key];
    }

    /**
     * Get entire state object (read-only)
     * @returns {object} State object
     */
    getAllState() {
        return { ...this.state };
    }

    // === Convenience Methods ===

    /**
     * Set current conversation
     */
    setCurrentConversation(conversationId) {
        this.setState('currentConversationId', conversationId);
    }

    /**
     * Add conversation to history
     */
    addConversationToHistory(conversationId, messages) {
        const history = { ...this.state.conversationHistory };
        history[conversationId] = messages;
        this.setState('conversationHistory', history);
    }

    /**
     * Get conversation from history
     */
    getConversationHistory(conversationId) {
        return this.state.conversationHistory[conversationId] || [];
    }

    /**
     * Set submitting flag
     */
    setSubmitting(isSubmitting) {
        this.setState('isSubmittingMessage', isSubmitting);
    }

    /**
     * Check if currently submitting
     */
    isSubmitting() {
        return this.state.isSubmittingMessage;
    }

    /**
     * Set current user
     */
    setCurrentUser(user) {
        this.setState('currentUser', user);
    }

    /**
     * Get current user
     */
    getCurrentUser() {
        return this.state.currentUser;
    }

    /**
     * Set conversations list
     */
    setConversations(conversations) {
        this.setState('conversations', conversations);
    }

    /**
     * Add new conversation to list
     */
    addConversation(conversation) {
        const conversations = [...this.state.conversations];
        conversations.unshift(conversation);
        this.setState('conversations', conversations);
    }

    /**
     * Remove conversation from list
     */
    removeConversation(conversationId) {
        const conversations = this.state.conversations.filter(
            conv => conv.id !== conversationId
        );
        this.setState('conversations', conversations);

        // Also remove from history
        const history = { ...this.state.conversationHistory };
        delete history[conversationId];
        this.setState('conversationHistory', history);
    }

    /**
     * Set current agent type
     */
    setAgentType(agentType) {
        this.setState('currentAgentType', agentType);
    }

    /**
     * Get current agent type
     */
    getAgentType() {
        return this.state.currentAgentType;
    }

    /**
     * Toggle export mode
     */
    toggleExportMode() {
        this.setState('exportMode', !this.state.exportMode);
    }

    /**
     * Set export mode
     */
    setExportMode(enabled) {
        this.setState('exportMode', enabled);
    }

    /**
     * Toggle sidebar
     */
    toggleSidebar() {
        this.setState('sidebarExpanded', !this.state.sidebarExpanded);
    }

    /**
     * Set sidebar expanded state
     */
    setSidebarExpanded(expanded) {
        this.setState('sidebarExpanded', expanded);
    }

    /**
     * Mark survey as completed
     */
    markSurveyCompleted(stage) {
        const surveys = { ...this.state.surveysCompleted };
        surveys[stage] = true;
        this.setState('surveysCompleted', surveys);
    }

    /**
     * Check if survey is completed
     */
    isSurveyCompleted(stage) {
        return this.state.surveysCompleted[stage] || false;
    }

    /**
     * Reset state (for testing or cleanup)
     */
    reset() {
        this.state = {
            currentUser: null,
            currentConversationId: null,
            conversations: [],
            conversationHistory: {},
            isSubmittingMessage: false,
            exportMode: false,
            sidebarExpanded: true,
            currentAgentType: 'market',
            hiredAgents: window.hiredAgents || [],
            surveysCompleted: {
                stage1: false,
                stage2: false
            }
        };
        this.listeners = {};
    }
}

// Create singleton instance
export const appState = new AppState();
