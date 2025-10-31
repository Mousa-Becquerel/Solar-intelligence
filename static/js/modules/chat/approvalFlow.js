/**
 * Approval Flow Module
 * Handles approval requests from agents (e.g., expert contact approval)
 */

import { api } from '../core/api.js';
import { createElement, scrollToBottom } from '../../utils/dom.js';
import { safeRenderMarkdown } from '../../utils/markdown.js';
import { contactFormHandler } from '../ui/contactFormHandler.js';

export class ApprovalFlow {
    constructor() {
        this.chatMessages = document.getElementById('chat-messages');
        this.chatWrapper = document.querySelector('.chat-messages-wrapper');
    }

    /**
     * Create approval UI with Yes/No buttons
     * @param {object} data - Approval request data
     * @returns {HTMLElement} Approval container element
     */
    createApprovalUI(data) {
        const { message, approval_question, conversation_id, context } = data;

        // Create message container
        const messageContainer = createElement('div', {
            classes: 'message-container approval-container',
            attributes: {
                'data-msg-id': `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                'data-msg-sender': 'bot',
                'data-msg-type': 'approval_request',
                'data-context': context || '',
                'data-conversation-id': conversation_id || ''
            }
        });

        // Create message div
        const messageDiv = createElement('div', {
            classes: 'message bot-message market-agent',
            innerHTML: safeRenderMarkdown(message || '')
        });

        // Create approval buttons container
        const approvalButtons = createElement('div', {
            classes: 'approval-buttons'
        });

        // Create Yes button
        const yesBtn = createElement('button', {
            classes: 'approval-btn approval-yes',
            textContent: 'Yes, contact expert'
        });
        yesBtn.addEventListener('click', () => {
            this.handleApprovalResponse(true, conversation_id, context, messageContainer);
        });

        // Create No button
        const noBtn = createElement('button', {
            classes: 'approval-btn approval-no',
            textContent: 'No, thanks'
        });
        noBtn.addEventListener('click', () => {
            this.handleApprovalResponse(false, conversation_id, context, messageContainer);
        });

        // Assemble UI
        approvalButtons.appendChild(yesBtn);
        approvalButtons.appendChild(noBtn);
        messageDiv.appendChild(approvalButtons);
        messageContainer.appendChild(messageDiv);

        return messageContainer;
    }

    /**
     * Handle user's approval response
     * @param {boolean} approved - Whether user approved
     * @param {string} conversationId - Conversation ID
     * @param {string} context - Context information
     * @param {HTMLElement} messageContainer - Container element
     */
    async handleApprovalResponse(approved, conversationId, context, messageContainer) {
        // Disable buttons to prevent double-clicking
        const buttons = messageContainer.querySelectorAll('.approval-btn');
        buttons.forEach(btn => {
            btn.disabled = true;
            btn.style.opacity = '0.5';
            btn.style.cursor = 'not-allowed';
        });

        // Show loading indicator
        const loadingDiv = createElement('div', {
            classes: 'approval-loading',
            textContent: 'Processing your response...'
        });
        loadingDiv.style.marginTop = '0.5rem';
        loadingDiv.style.fontSize = '0.875rem';
        loadingDiv.style.color = '#6b7280';
        messageContainer.querySelector('.message').appendChild(loadingDiv);

        try {
            // Send approval to backend
            const result = await api.sendApprovalResponse(approved, conversationId, context);

            // Remove loading indicator
            loadingDiv.remove();

            // Remove approval buttons
            const approvalButtonsDiv = messageContainer.querySelector('.approval-buttons');
            if (approvalButtonsDiv) {
                approvalButtonsDiv.remove();
            }

            // Create bot response message
            const responseContainer = createElement('div', {
                classes: 'message-container',
                attributes: {
                    'data-msg-id': `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                    'data-msg-sender': 'bot',
                    'data-msg-type': 'string'
                }
            });

            const responseDiv = createElement('div', {
                classes: 'message bot-message market-agent',
                innerHTML: safeRenderMarkdown(result.message || '')
            });

            // If user approved and wants to contact expert, open artifact panel with contact form
            if (approved && result.redirect_to_contact) {
                // Open artifact panel with contact form after a brief delay
                setTimeout(() => {
                    contactFormHandler.showContactForm();
                }, 800);
            }

            responseContainer.appendChild(responseDiv);
            this.chatWrapper.appendChild(responseContainer);

            // Auto-scroll
            scrollToBottom(this.chatMessages);

        } catch (error) {
            console.error('Error handling approval:', error);

            // Remove loading indicator
            if (loadingDiv.parentNode) {
                loadingDiv.remove();
            }

            // Show error message
            const errorDiv = createElement('div', {
                textContent: 'Failed to process your response. Please try again.',
                classes: 'error-message'
            });
            errorDiv.style.marginTop = '0.5rem';
            errorDiv.style.padding = '0.5rem';
            errorDiv.style.backgroundColor = '#fee2e2';
            errorDiv.style.color = '#991b1b';
            errorDiv.style.borderRadius = '4px';
            errorDiv.style.fontSize = '0.875rem';
            messageContainer.querySelector('.message').appendChild(errorDiv);

            // Re-enable buttons
            buttons.forEach(btn => {
                btn.disabled = false;
                btn.style.opacity = '1';
                btn.style.cursor = 'pointer';
            });
        }
    }

    /**
     * Append approval buttons to an existing message div
     * @param {HTMLElement} messageDiv - Existing message div element
     * @param {object} data - Approval request data
     */
    appendApprovalButtons(messageDiv, data) {
        const { approval_question, conversation_id, context } = data;

        // Get the message container (parent of messageDiv)
        const messageContainer = messageDiv.closest('.message-container');
        if (messageContainer) {
            // Update container attributes for approval context
            messageContainer.setAttribute('data-msg-type', 'approval_request');
            messageContainer.setAttribute('data-context', context || '');
            messageContainer.setAttribute('data-conversation-id', conversation_id || '');
        }

        // Create approval buttons container
        const approvalButtons = createElement('div', {
            classes: 'approval-buttons'
        });

        // Create Yes button
        const yesBtn = createElement('button', {
            classes: 'approval-btn approval-yes',
            textContent: 'Yes, contact expert'
        });
        yesBtn.addEventListener('click', () => {
            this.handleApprovalResponse(true, conversation_id, context, messageContainer || messageDiv.parentElement);
        });

        // Create No button
        const noBtn = createElement('button', {
            classes: 'approval-btn approval-no',
            textContent: 'No, thanks'
        });
        noBtn.addEventListener('click', () => {
            this.handleApprovalResponse(false, conversation_id, context, messageContainer || messageDiv.parentElement);
        });

        // Assemble and append buttons to existing message
        approvalButtons.appendChild(yesBtn);
        approvalButtons.appendChild(noBtn);
        messageDiv.appendChild(approvalButtons);

        // Scroll to bottom
        scrollToBottom(this.chatMessages);
    }

    /**
     * Display approval request in chat
     * @param {object} data - Approval request data
     */
    displayApprovalRequest(data) {
        // Remove loading spinner if present
        const currentLoading = document.getElementById('current-loading');
        if (currentLoading) {
            currentLoading.remove();
        }

        // Create and append approval UI
        const approvalUI = this.createApprovalUI(data);
        this.chatWrapper.appendChild(approvalUI);

        // Scroll to bottom
        scrollToBottom(this.chatMessages);
    }
}

// Create singleton instance
export const approvalFlow = new ApprovalFlow();
