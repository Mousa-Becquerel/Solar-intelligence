/**
 * Expert Cards Module
 * Manages expert selection cards in contact form
 */

/**
 * Expert profiles data
 */
export const EXPERTS = [
    {
        id: 'senior-analyst',
        title: 'Senior Analyst',
        description: 'Expert in PV market and price. Works with Alex and Maya',
        icon: 'chart',
        color: 'navy'
    },
    {
        id: 'technology-expert',
        title: 'Senior Technology Expert',
        description: 'Expert in PV technology',
        icon: 'solar',
        color: 'gold'
    },
    {
        id: 'ai-expert',
        title: 'Senior AI Expert',
        description: 'Discuss about AI solutions and needs for your company. Works with Nova',
        icon: 'ai',
        color: 'navy-light'
    },
    {
        id: 'marketing-sales',
        title: 'Marketing and Sales Rep',
        description: 'Discuss about Becquerel Institute services and products',
        icon: 'briefcase',
        color: 'gold-dark'
    }
];

/**
 * Get SVG icon for expert type
 * @param {string} iconType - Type of icon
 * @returns {string} SVG markup
 */
function getExpertIcon(iconType) {
    const icons = {
        chart: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="20" x2="12" y2="10"></line>
            <line x1="18" y1="20" x2="18" y2="4"></line>
            <line x1="6" y1="20" x2="6" y2="16"></line>
        </svg>`,
        solar: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="4"></circle>
            <path d="M12 2v2"></path>
            <path d="M12 20v2"></path>
            <path d="m4.93 4.93 1.41 1.41"></path>
            <path d="m17.66 17.66 1.41 1.41"></path>
            <path d="M2 12h2"></path>
            <path d="M20 12h2"></path>
            <path d="m6.34 17.66-1.41 1.41"></path>
            <path d="m19.07 4.93-1.41 1.41"></path>
        </svg>`,
        ai: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
            <path d="M16 3l-4 4-4-4"></path>
            <circle cx="8" cy="14" r="1"></circle>
            <circle cx="16" cy="14" r="1"></circle>
            <path d="M9 17h6"></path>
        </svg>`,
        briefcase: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
            <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
        </svg>`
    };
    return icons[iconType] || icons.chart;
}

/**
 * Generate expert selection cards HTML
 * @returns {string} HTML string for expert cards
 */
export function generateExpertCardsHTML() {
    const cardsHTML = EXPERTS.map(expert => `
        <div class="expert-card" data-expert-id="${expert.id}" data-color="${expert.color}">
            <div class="expert-card-icon">${getExpertIcon(expert.icon)}</div>
            <div class="expert-card-content">
                <h4 class="expert-card-title">${expert.title}</h4>
                <p class="expert-card-description">${expert.description}</p>
            </div>
            <div class="expert-card-check">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
            </div>
        </div>
    `).join('');

    return `
        <div class="expert-selection-section">
            <h3 class="expert-section-title">Contact Our Experts</h3>
            <label class="expert-selection-label">
                Select Expert(s) <span class="optional-text">(optional)</span>
            </label>
            <p class="expert-selection-hint">Choose one or more experts who can best help with your inquiry</p>
            <div class="expert-cards-grid">
                ${cardsHTML}
            </div>
        </div>
    `;
}

/**
 * Setup expert card selection
 * @returns {Array<string>} Selected expert IDs
 */
export function setupExpertCards() {
    const cards = document.querySelectorAll('.expert-card');
    const selectedExperts = new Set();

    cards.forEach(card => {
        card.addEventListener('click', () => {
            const expertId = card.dataset.expertId;

            if (card.classList.contains('selected')) {
                // Deselect
                card.classList.remove('selected');
                selectedExperts.delete(expertId);
            } else {
                // Select
                card.classList.add('selected');
                selectedExperts.add(expertId);
            }
        });
    });

    // Return function to get selected experts
    return () => Array.from(selectedExperts);
}

/**
 * Get selected expert titles
 * @param {Array<string>} expertIds - Array of expert IDs
 * @returns {Array<string>} Array of expert titles
 */
export function getExpertTitles(expertIds) {
    return expertIds
        .map(id => EXPERTS.find(expert => expert.id === id)?.title)
        .filter(Boolean);
}
