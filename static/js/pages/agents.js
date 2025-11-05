/**
 * Agent Hire Page - JavaScript Module
 * Handles agent hiring/unhiring and UI updates
 */

// ============================================
// AGENT METADATA
// ============================================
const AGENT_DATA = {
    market: {
        name: 'Alex',
        role: 'PV Capacity',
        icon: '<path fill-rule="evenodd" d="M3 3a1 1 0 000 2v8a2 2 0 002 2h2.586l-1.293 1.293a1 1 0 101.414 1.414L10 15.414l2.293 2.293a1 1 0 001.414-1.414L12.414 15H15a2 2 0 002-2V5a1 1 0 100-2H3zm11.707 4.707a1 1 0 00-1.414-1.414L10 9.586 8.707 8.293a1 1 0 00-1.414 0l-2 2a1 1 0 101.414 1.414L8 10.414l1.293 1.293a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>'
    },
    price: {
        name: 'Maya',
        role: 'Price Analysis',
        icon: '<path d="M8.433 7.418c.155-.103.346-.196.567-.267v1.698a2.305 2.305 0 01-.567-.267C8.07 8.34 8 8.114 8 8c0-.114.07-.34.433-.582zM11 12.849v-1.698c.22.071.412.164.567.267.364.243.433.468.433.582 0 .114-.07.34-.433.582a2.305 2.305 0 01-.567.267z"></path><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-13a1 1 0 10-2 0v.092a4.535 4.535 0 00-1.676.662C6.602 6.234 6 7.009 6 8c0 .99.602 1.765 1.324 2.246.48.32 1.054.545 1.676.662v1.941c-.391-.127-.68-.317-.843-.504a1 1 0 10-1.51 1.31c.562.649 1.413 1.076 2.353 1.253V15a1 1 0 102 0v-.092a4.535 4.535 0 001.676-.662C13.398 13.766 14 12.991 14 12c0-.99-.602-1.765-1.324-2.246A4.535 4.535 0 0011 9.092V7.151c.391.127.68.317.843.504a1 1 0 101.511-1.31c-.563-.649-1.413-1.076-2.354-1.253V5z" clip-rule="evenodd"></path>'
    },
    news: {
        name: 'Emma',
        role: 'News Analyst',
        icon: '<path fill-rule="evenodd" d="M2 5a2 2 0 012-2h8a2 2 0 012 2v10a2 2 0 002 2H4a2 2 0 01-2-2V5zm3 1h6v4H5V6zm6 6H5v2h6v-2z" clip-rule="evenodd"></path><path d="M15 7h1a2 2 0 012 2v5.5a1.5 1.5 0 01-3 0V7z"></path>'
    },
    digitalization: {
        name: 'Nova',
        role: 'Digitalization Expert',
        icon: '<path d="M13 7H7v6h6V7z"></path><path fill-rule="evenodd" d="M7 2a1 1 0 012 0v1h2V2a1 1 0 112 0v1h2a2 2 0 012 2v2h1a1 1 0 110 2h-1v2h1a1 1 0 110 2h-1v2a2 2 0 01-2 2h-2v1a1 1 0 11-2 0v-1H9v1a1 1 0 11-2 0v-1H5a2 2 0 01-2-2v-2H2a1 1 0 110-2h1V9H2a1 1 0 010-2h1V5a2 2 0 012-2h2V2zM5 5h10v10H5V5z" clip-rule="evenodd"></path>'
    },
    nzia_policy: {
        name: 'Aniza',
        role: 'NZIA Policy Expert',
        icon: '<path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clip-rule="evenodd"></path>'
    },
    manufacturer_financial: {
        name: 'Finn',
        role: 'Manufacturer Financial Analyst',
        icon: '<path d="M8.433 7.418c.155-.103.346-.196.567-.267v1.698a2.305 2.305 0 01-.567-.267C8.07 8.34 8 8.114 8 8c0-.114.07-.34.433-.582zM11 12.849v-1.698c.22.071.412.164.567.267.364.243.433.468.433.582 0 .114-.07.34-.433.582a2.305 2.305 0 01-.567.267z"></path><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-13a1 1 0 10-2 0v.092a4.535 4.535 0 00-1.676.662C6.602 6.234 6 7.009 6 8c0 .99.602 1.765 1.324 2.246.48.32 1.054.545 1.676.662v1.941c-.391-.127-.68-.317-.843-.504a1 1 0 10-1.51 1.31c.562.649 1.413 1.076 2.353 1.253V15a1 1 0 102 0v-.092a4.535 4.535 0 001.676-.662C13.398 13.766 14 12.991 14 12c0-.99-.602-1.765-1.324-2.246A4.535 4.535 0 0011 9.092V7.151c.391.127.68.317.843.504a1 1 0 101.511-1.31c-.563-.649-1.413-1.076-2.354-1.253V5z" clip-rule="evenodd"></path>'
    },
    nzia_market_impact: {
        name: 'Nina',
        role: 'NZIA Market Impact Expert',
        icon: '<circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>'
    },
    om: {
        name: 'Leo',
        role: 'O&M Expert',
        icon: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>'
    }
};

// ============================================
// STATE MANAGEMENT
// ============================================
class AgentManager {
    constructor(initialHiredAgents = []) {
        this.hiredAgents = initialHiredAgents;
        this.csrfToken = this.getCSRFToken();
    }

    /**
     * Get CSRF token from meta tag
     */
    getCSRFToken() {
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        return metaToken ? metaToken.getAttribute('content') : '';
    }

    /**
     * Check if agent is hired
     */
    isHired(agentType) {
        return this.hiredAgents.includes(agentType);
    }

    /**
     * Add agent to hired list
     */
    addHiredAgent(agentType) {
        if (!this.isHired(agentType)) {
            this.hiredAgents.push(agentType);
        }
    }

    /**
     * Remove agent from hired list
     */
    removeHiredAgent(agentType) {
        this.hiredAgents = this.hiredAgents.filter(type => type !== agentType);
    }

    /**
     * Get all hired agents
     */
    getHiredAgents() {
        return [...this.hiredAgents];
    }

    /**
     * Check if any agents are hired
     */
    hasHiredAgents() {
        return this.hiredAgents.length > 0;
    }
}

// ============================================
// API CALLS
// ============================================
const AgentAPI = {
    /**
     * Hire an agent
     */
    async hire(agentType, csrfToken) {
        const response = await fetch('/api/agents/hire', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ agent_type: agentType })
        });

        return response.json();
    },

    /**
     * Unhire an agent
     */
    async unhire(agentType, csrfToken) {
        const response = await fetch('/api/agents/unhire', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ agent_type: agentType })
        });

        return response.json();
    }
};

// ============================================
// UI RENDERING
// ============================================
class AgentUI {
    constructor(manager) {
        this.manager = manager;
    }

    /**
     * Update all UI elements based on current state
     */
    updateAll() {
        this.renderHiredAgents();
        this.updateAgentCards();
        this.updateStartChatButton();
    }

    /**
     * Render hired agents in sidebar
     */
    renderHiredAgents() {
        const container = document.getElementById('hired-agents-container');
        if (!container) return;

        const hiredAgents = this.manager.getHiredAgents();

        if (hiredAgents.length === 0) {
            container.innerHTML = this.getEmptyStateHTML();
            return;
        }

        container.innerHTML = hiredAgents
            .map(agentType => this.getHiredAgentHTML(agentType))
            .join('');
    }

    /**
     * Get empty state HTML
     */
    getEmptyStateHTML() {
        return `
            <div class="agents-empty-state">
                <svg fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM7 9a1 1 0 100-2 1 1 0 000 2zm7-1a1 1 0 11-2 0 1 1 0 012 0zm-7.536 5.879a1 1 0 001.415 0 3 3 0 014.242 0 1 1 0 001.415-1.415 5 5 0 00-7.072 0 1 1 0 000 1.415z" clip-rule="evenodd"></path>
                </svg>
                <p>No agents hired yet.<br>Hire agents to build your team!</p>
            </div>
        `;
    }

    /**
     * Get hired agent item HTML
     */
    getHiredAgentHTML(agentType) {
        const agent = AGENT_DATA[agentType];
        if (!agent) return '';

        return `
            <div class="agents-hired-item">
                <div class="agents-hired-item__info">
                    <div class="agents-hired-item__icon">
                        <svg fill="currentColor" viewBox="0 0 20 20">
                            ${agent.icon}
                        </svg>
                    </div>
                    <div class="agents-hired-item__details">
                        <h4>${agent.name}</h4>
                        <p>${agent.role}</p>
                    </div>
                </div>
                <button class="agents-unhire-btn" data-agent="${agentType}">Remove</button>
            </div>
        `;
    }

    /**
     * Update agent card states
     */
    updateAgentCards() {
        const cards = document.querySelectorAll('[data-agent-card]');
        const buttons = document.querySelectorAll('[data-hire-btn]');

        // Reset all cards
        cards.forEach(card => card.classList.remove('agent-card--hired'));
        buttons.forEach(button => {
            button.classList.remove('agent-card__btn--hired');
            button.innerHTML = this.getHireButtonHTML(false);
        });

        // Update hired agents
        this.manager.getHiredAgents().forEach(agentType => {
            const card = document.querySelector(`[data-agent-card="${agentType}"]`);
            const button = document.querySelector(`[data-hire-btn="${agentType}"]`);

            if (card) card.classList.add('agent-card--hired');
            if (button) {
                button.classList.add('agent-card__btn--hired');
                button.innerHTML = this.getHireButtonHTML(true);
            }
        });
    }

    /**
     * Get hire button HTML
     */
    getHireButtonHTML(isHired) {
        if (isHired) {
            return `
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                Hired
            `;
        }

        return `
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
            </svg>
            Hire Agent
        `;
    }

    /**
     * Update start chat button state
     */
    updateStartChatButton() {
        const btn = document.getElementById('start-chat-btn');
        if (!btn) return;

        if (this.manager.hasHiredAgents()) {
            btn.disabled = false;
            btn.style.opacity = '1';
            btn.style.cursor = 'pointer';
            btn.onclick = null;
        } else {
            btn.disabled = true;
            btn.style.opacity = '0.5';
            btn.style.cursor = 'not-allowed';
            btn.onclick = (e) => {
                e.preventDefault();
                showNotification('Please hire at least one agent first', 'error');
            };
        }
    }
}

// ============================================
// NOTIFICATION SYSTEM
// ============================================
function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    if (!notification) return;

    notification.textContent = message;
    notification.className = `agents-notification agents-notification--${type}`;
    notification.style.display = 'block';

    setTimeout(() => {
        notification.style.display = 'none';
    }, 3000);
}

// ============================================
// EVENT HANDLERS
// ============================================
async function handleHireToggle(agentType) {
    const isHired = agentManager.isHired(agentType);

    if (isHired) {
        await handleUnhire(agentType);
    } else {
        await handleHire(agentType);
    }
}

async function handleHire(agentType) {
    try {
        const data = await AgentAPI.hire(agentType, agentManager.csrfToken);

        if (data.success) {
            agentManager.addHiredAgent(agentType);
            ui.updateAll();
            const agentName = AGENT_DATA[agentType]?.name || 'Agent';
            showNotification(`${agentName} has joined your team!`, 'success');
        } else {
            showNotification(data.message || 'Failed to hire agent', 'error');
        }
    } catch (error) {
        console.error('Error hiring agent:', error);
        showNotification('Failed to hire agent', 'error');
    }
}

async function handleUnhire(agentType) {
    try {
        const data = await AgentAPI.unhire(agentType, agentManager.csrfToken);

        if (data.success) {
            agentManager.removeHiredAgent(agentType);
            ui.updateAll();
            const agentName = AGENT_DATA[agentType]?.name || 'Agent';
            showNotification(`${agentName} has been removed from your team`, 'success');
        } else {
            showNotification(data.message || 'Failed to remove agent', 'error');
        }
    } catch (error) {
        console.error('Error unhiring agent:', error);
        showNotification('Failed to remove agent', 'error');
    }
}

// ============================================
// INITIALIZATION
// ============================================
let agentManager;
let ui;

function initializeAgentsPage(initialHiredAgents = []) {
    // Initialize state management
    agentManager = new AgentManager(initialHiredAgents);
    ui = new AgentUI(agentManager);

    // Initial render
    ui.updateAll();

    // Attach event listeners using event delegation
    document.addEventListener('click', (e) => {
        // Handle hire button clicks
        const hireBtn = e.target.closest('[data-hire-btn]');
        if (hireBtn) {
            const agentType = hireBtn.getAttribute('data-hire-btn');
            handleHireToggle(agentType);
            return;
        }

        // Handle unhire button clicks
        const unhireBtn = e.target.closest('.agents-unhire-btn');
        if (unhireBtn) {
            const agentType = unhireBtn.getAttribute('data-agent');
            handleUnhire(agentType);
            return;
        }
    });
}

// Export for global access (will be called from HTML)
window.initializeAgentsPage = initializeAgentsPage;
window.handleHireToggle = handleHireToggle;
