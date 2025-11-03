/**
 * API Module - Centralized API communication
 * Handles all fetch requests with consistent error handling and CSRF token management
 */

export class API {
    constructor() {
        this.baseUrl = '';
        this.csrfToken = this.getCSRFToken();
    }

    /**
     * Get CSRF token from meta tag or hidden input
     */
    getCSRFToken() {
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) return metaToken.getAttribute('content');

        const inputToken = document.querySelector('input[name="csrf_token"]');
        if (inputToken) return inputToken.value;

        return '';
    }

    /**
     * Generic fetch wrapper with error handling
     */
    async request(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                ...(this.csrfToken && { 'X-CSRFToken': this.csrfToken })
            },
            credentials: 'same-origin'
        };

        const finalOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };

        try {
            const response = await fetch(url, finalOptions);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));

                // Special handling for query limit (429 status)
                if (response.status === 429 && errorData.upgrade_required) {
                    const limitError = new Error(errorData.error || 'Query limit reached');
                    limitError.queryLimitData = errorData; // Attach full data for frontend
                    throw limitError;
                }

                throw new Error(errorData.error || errorData.message || `HTTP ${response.status}`);
            }

            return response;
        } catch (error) {
            console.error(`API Error [${url}]:`, error);
            throw error;
        }
    }

    /**
     * GET request
     */
    async get(url) {
        const response = await this.request(url, { method: 'GET' });
        return response.json();
    }

    /**
     * POST request
     */
    async post(url, data = {}) {
        const response = await this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
        return response.json();
    }

    /**
     * DELETE request
     */
    async delete(url) {
        const response = await this.request(url, { method: 'DELETE' });
        return response.json();
    }

    /**
     * PATCH request
     */
    async patch(url, data = {}) {
        const response = await this.request(url, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
        return response.json();
    }

    // === Conversation Endpoints ===

    /**
     * Get all conversations for current user
     */
    async getConversations() {
        return this.get('/conversations');
    }

    /**
     * Get specific conversation with messages
     */
    async getConversation(conversationId) {
        return this.get(`/conversations/${conversationId}`);
    }

    /**
     * Delete a conversation
     */
    async deleteConversation(conversationId) {
        return this.delete(`/conversations/${conversationId}`);
    }

    /**
     * Create new conversation
     */
    async createConversation() {
        return this.post('/conversations/fresh');
    }

    // === Chat Endpoints ===

    /**
     * Send message and get streaming response
     * Returns fetch Response object for SSE streaming
     */
    async sendChatMessage(conversationId, message, agentType) {
        const response = await this.request('/chat', {
            method: 'POST',
            body: JSON.stringify({
                message: message,
                conversation_id: conversationId,
                agent_type: agentType
            })
        });

        return response;
    }

    /**
     * Send approval response
     */
    async sendApprovalResponse(approved, conversationId, context) {
        return this.post('/api/approval_response', {
            approved,
            conversation_id: conversationId,
            context
        });
    }

    // === User Endpoints ===

    /**
     * Get current user info
     */
    async getCurrentUser() {
        return this.get('/auth/current-user');
    }

    /**
     * Logout current user
     */
    async logout() {
        return this.post('/auth/logout');
    }

    // === Export Endpoints ===

    /**
     * Download selected messages
     */
    async downloadMessages(messages, format = 'docx') {
        const response = await this.request('/export-messages', {
            method: 'POST',
            body: JSON.stringify({ messages, format })
        });
        return response.blob();
    }

    /**
     * Generate PowerPoint presentation
     */
    async generatePPT(messages) {
        const response = await this.request('/generate-ppt', {
            method: 'POST',
            body: JSON.stringify({ messages })
        });
        return response.blob();
    }

    // === Survey Endpoints ===

    /**
     * Submit user survey
     */
    async submitSurvey(surveyData) {
        return this.post('/submit-user-survey', surveyData);
    }

    /**
     * Submit stage 2 survey
     */
    async submitSurveyStage2(surveyData) {
        return this.post('/submit-user-survey-stage2', surveyData);
    }

    // === News Endpoints ===

    /**
     * Get random news item
     */
    async getRandomNews() {
        return this.get('/random-news');
    }
}

// Create singleton instance
export const api = new API();
