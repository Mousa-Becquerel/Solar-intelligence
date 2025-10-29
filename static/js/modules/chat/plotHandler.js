/**
 * Plot Handler Module
 * Manages D3 chart rendering and interaction
 */

import { createElement } from '../../utils/dom.js';
import { scrollToBottom } from '../../utils/dom.js';

export class PlotHandler {
    /**
     * Create and render a plot visualization
     * @param {object} eventData - Plot event data
     * @param {string} agentType - Current agent type
     * @param {HTMLElement} chatWrapper - Chat wrapper element
     * @param {HTMLElement} chatMessages - Chat messages scroll container
     * @returns {HTMLElement} - Message container
     */
    createPlot(eventData, agentType, chatWrapper, chatMessages) {
        console.log('📊 Creating plot visualization');

        const plotData = eventData.content;

        // Create message container for plot
        const messageContainer = createElement('div', {
            classes: 'message-container',
            attributes: {
                'data-msg-id': `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                'data-msg-sender': 'bot',
                'data-msg-type': 'plot'
            }
        });

        const messageDiv = createElement('div', {
            classes: ['message', 'bot-message', `${agentType}-agent`]
        });

        messageContainer.appendChild(messageDiv);
        chatWrapper.appendChild(messageContainer);

        // Create unique container ID for the plot
        const plotContainerId = `plot-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

        // Create plot card structure (matching market agent style)
        const plotCard = createElement('div', {
            classes: 'plot-card'
        });

        const plotContent = createElement('div', {
            classes: 'plot-content'
        });

        // Create container for D3 chart with larger styling
        const chartContainer = createElement('div', {
            classes: 'interactive-chart-container',
            attributes: { id: plotContainerId }
        });

        chartContainer.style.cssText = `
            width: 100%;
            height: auto;
            min-height: 600px;
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            position: relative;
        `;

        plotContent.appendChild(chartContainer);
        plotCard.appendChild(plotContent);

        // Add action buttons for interactivity
        const actions = createElement('div', {
            classes: 'plot-actions'
        });

        const resetLegendBtn = createElement('button', {
            classes: 'download-btn',
            textContent: 'Reset legend'
        });
        resetLegendBtn.onclick = () => {
            if (window.resetD3Legend) {
                window.resetD3Legend(plotContainerId);
            }
        };

        const downloadBtn = createElement('button', {
            classes: 'download-btn',
            textContent: 'Download PNG'
        });
        downloadBtn.onclick = () => {
            if (window.downloadD3Chart) {
                const title = (plotData.title || 'chart').replace(/[^a-z0-9]/gi, '_').toLowerCase();
                window.downloadD3Chart(plotContainerId, `${title}.png`);
            }
        };

        actions.appendChild(resetLegendBtn);
        actions.appendChild(downloadBtn);
        plotCard.appendChild(actions);

        // Add the plot card to message
        messageDiv.appendChild(plotCard);

        // Embed plot JSON for export
        try {
            const meta = createElement('div', {
                attributes: {
                    'data-plot-json': JSON.stringify(plotData || {})
                }
            });
            meta.style.display = 'none';
            messageDiv.appendChild(meta);
        } catch (e) {
            console.error('Failed to embed plot metadata:', e);
        }

        // Force a reflow to ensure DOM is updated
        void messageDiv.offsetHeight;

        // Render D3 chart with timeout to ensure DOM is ready
        setTimeout(() => {
            try {
                // Check if container is in DOM
                const containerElement = document.getElementById(plotContainerId);
                if (!containerElement) {
                    console.error('Chart container not found in DOM:', plotContainerId);
                    return;
                }

                if (!plotData || !plotData.data) {
                    console.error('Invalid plot data:', plotData);
                    containerElement.innerHTML = '<div class="error-message">Plot data is missing or corrupted</div>';
                    return;
                }

                // Check if renderD3Chart is available
                if (typeof window.renderD3Chart !== 'function') {
                    console.error('renderD3Chart function not found');
                    containerElement.innerHTML = '<div class="error-message">Chart rendering function not available</div>';
                    return;
                }

                console.log('🎨 Rendering D3 chart with data:', plotData);
                window.renderD3Chart(plotContainerId, plotData);

            } catch (error) {
                console.error('Error rendering D3 chart:', error);
                const containerElement = document.getElementById(plotContainerId);
                if (containerElement) {
                    containerElement.innerHTML = `<div class="error-message">Error rendering chart: ${error.message}</div>`;
                }
            }
        }, 200);

        // Auto-scroll
        scrollToBottom(chatMessages);

        return messageContainer;
    }
}

// Create singleton instance
export const plotHandler = new PlotHandler();
