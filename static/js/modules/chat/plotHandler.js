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

        // Add commentary text if available in description
        if (plotData.description) {
            const commentaryDiv = createElement('div', {
                classes: 'plot-commentary'
            });
            commentaryDiv.style.cssText = `
                margin-top: 1rem;
                padding: 1rem;
                background: #f9fafb;
                border-left: 3px solid #EB8F47;
                border-radius: 4px;
                font-size: 0.9rem;
                line-height: 1.6;
                color: #374151;
            `;
            commentaryDiv.textContent = plotData.description;
            plotContent.appendChild(commentaryDiv);
        }

        plotCard.appendChild(plotContent);

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
                    console.error('❌ Chart container not found in DOM:', plotContainerId);
                    return;
                }

                // Enhanced validation of plot data
                if (!plotData) {
                    console.error('❌ Plot data is null or undefined');
                    containerElement.innerHTML = '<div style="padding: 2rem; text-align: center; color: #ef4444; background: #fef2f2; border-radius: 8px;">Plot data is missing. The chart may have failed to load from history.</div>';
                    return;
                }

                console.log('🔍 Plot data structure:', {
                    hasData: !!plotData.data,
                    hasPlotType: !!plotData.plot_type,
                    hasTitle: !!plotData.title,
                    dataLength: plotData.data ? plotData.data.length : 0,
                    plotType: plotData.plot_type,
                    fullData: plotData
                });

                if (!plotData.data || !Array.isArray(plotData.data) || plotData.data.length === 0) {
                    console.error('❌ Invalid plot data - missing or empty data array:', plotData);
                    containerElement.innerHTML = '<div style="padding: 2rem; text-align: center; color: #ef4444; background: #fef2f2; border-radius: 8px;">Plot data is corrupted or incomplete. The chart cannot be rendered.</div>';
                    return;
                }

                // Check if renderD3Chart is available
                if (typeof window.renderD3Chart !== 'function') {
                    console.error('❌ renderD3Chart function not found');
                    containerElement.innerHTML = '<div style="padding: 2rem; text-align: center; color: #ef4444; background: #fef2f2; border-radius: 8px;">Chart rendering function not available. Please refresh the page.</div>';
                    return;
                }

                console.log('✅ All validations passed. Rendering D3 chart...');
                window.renderD3Chart(plotContainerId, plotData);
                console.log('✅ D3 chart render complete');

            } catch (error) {
                console.error('❌ Error rendering D3 chart:', error);
                const containerElement = document.getElementById(plotContainerId);
                if (containerElement) {
                    containerElement.innerHTML = `<div style="padding: 2rem; text-align: center; color: #ef4444; background: #fef2f2; border-radius: 8px;">Error rendering chart: ${error.message}<br><br>Check console for details.</div>`;
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
