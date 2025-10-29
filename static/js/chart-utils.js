function makeEditableTitle(titleElement, plotData, containerId) {
    const currentTitle = plotData.title;
    const titleSVG = d3.select(titleElement);
    const svgElement = titleSVG.node().ownerSVGElement;
    const containerElement = svgElement.parentElement;
    
    // Get the title's position attributes
    const titleX = parseFloat(titleSVG.attr('x'));
    const titleY = parseFloat(titleSVG.attr('y'));
    
    // Get SVG and container positions
    const svgRect = svgElement.getBoundingClientRect();
    const containerRect = containerElement.getBoundingClientRect();
    
    // Calculate the input position relative to the container
    const inputLeft = svgRect.left - containerRect.left + titleX;
    const inputTop = svgRect.top - containerRect.top + titleY;
    
    // Create an input field positioned over the title
    const input = document.createElement('input');
    input.type = 'text';
    input.value = currentTitle;
    input.style.position = 'absolute';
    // Calculate width based on text length, with a minimum width
    const estimatedWidth = Math.max(200, currentTitle.length * 12 + 40);
    
    input.style.left = (inputLeft - estimatedWidth/2) + 'px'; // Center the input
    input.style.top = (inputTop - 12) + 'px'; // Center vertically (24px height / 2)
    input.style.width = estimatedWidth + 'px';
    input.style.height = '24px';
    input.style.fontSize = '18px';
    input.style.fontFamily = "'Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif";
    input.style.fontWeight = '300';
    input.style.textAlign = 'center';
    input.style.border = '2px solid #3b82f6';
    input.style.borderRadius = '4px';
    input.style.background = 'white';
    input.style.zIndex = '1000';
    input.style.outline = 'none';
    
    // Hide the original title
    titleSVG.style('opacity', '0');
    
    // Add input to container
    containerElement.style.position = 'relative';
    containerElement.appendChild(input);
    
    // Focus and select the text
    input.focus();
    input.select();
    
    // Handle saving the new title
    function saveTitle() {
        const newTitle = input.value.trim();
        if (newTitle && newTitle !== currentTitle) {
            // Update the plot data
            plotData.title = newTitle;
            
            // Update the data attribute if it exists
            const messageEl = containerElement.closest('[data-plot-json]');
            if (messageEl) {
                const updatedData = JSON.stringify(plotData);
                messageEl.setAttribute('data-plot-json', updatedData);
            }
            
            console.log(`📝 Title updated from "${currentTitle}" to "${newTitle}"`);
        }
        
        // Remove input and show updated title
        containerElement.removeChild(input);
        titleSVG.style('opacity', '0.9').text(plotData.title);
    }
    
    // Handle canceling
    function cancelEdit() {
        containerElement.removeChild(input);
        titleSVG.style('opacity', '0.9');
    }
    
    // Event listeners
    input.addEventListener('blur', saveTitle);
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            saveTitle();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            cancelEdit();
        }
    });
}

// Enhanced tooltip generation function
function createEnhancedTooltip(data, seriesName, plotData, event) {
    const date = data.date instanceof Date ? data.date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    }) : data.date;
    
    const value = typeof data.value === 'number' ? data.value.toLocaleString() : data.value;
    const unit = plotData.unit || '';
    
    // Calculate growth if we have previous value (simplified example)
    let growthHtml = '';
    if (data.previousValue && typeof data.value === 'number' && typeof data.previousValue === 'number') {
        const growth = ((data.value - data.previousValue) / data.previousValue * 100).toFixed(1);
        const trendClass = growth >= 0 ? 'positive' : 'negative';
        const trendSymbol = growth >= 0 ? '↗' : '↘';
        growthHtml = `<span class="tooltip-trend ${trendClass}">${trendSymbol} ${Math.abs(growth)}%</span>`;
    }
    
    return `
        <div class="tooltip-header">${seriesName}</div>
        <div class="tooltip-body">
            <div class="tooltip-row">
                <span class="tooltip-label">Date:</span>
                <span class="tooltip-value">${date}</span>
            </div>
            <div class="tooltip-row">
                <span class="tooltip-label">Value:</span>
                <span class="tooltip-value">${value} ${unit}</span>
                ${growthHtml}
            </div>
            ${data.category ? `<div class="tooltip-row">
                <span class="tooltip-label">Category:</span>
                <span class="tooltip-value">${data.category}</span>
            </div>` : ''}
        </div>
    `;
}

// Animation utility functions
function animateChartEntry(container) {
    container.classed('chart-enter', true);
    setTimeout(() => {
        container.classed('chart-enter', false)
                .classed('chart-enter-active', true);
        setTimeout(() => {
            container.classed('chart-enter-active', false);
        }, 300);
    }, 10);
}

function animateElementUpdate(selection, updateFn) {
    selection.classed('chart-update', true);
    updateFn();
    setTimeout(() => {
        selection.classed('chart-update', false);
    }, 500);
}

// Global chart state management
window.chartStates = new Map();
window.chartSyncGroups = new Map();

// Advanced Chart Controls System
class ChartController {
    constructor(containerId, plotData) {
        this.containerId = containerId;
        this.plotData = plotData;
        this.currentTimeRange = null;
        this.activeFilters = new Map();
        this.syncGroup = null;
        this.setupControls();
    }

    setupControls() {
        const plotType = (this.plotData.plot_type || 'line').toLowerCase();
        const controlsHTML = this.createControlsHTML();

        // Only create and insert controls div if there's actual content
        if (!controlsHTML || controlsHTML.trim() === '') {
            return; // Skip creating empty controls div
        }

        const container = document.getElementById(this.containerId);
        const controlsDiv = document.createElement('div');
        controlsDiv.className = 'chart-controls';
        controlsDiv.innerHTML = controlsHTML;

        // Insert controls before the chart
        container.parentNode.insertBefore(controlsDiv, container);
        this.bindControlEvents();
    }

    createControlsHTML() {
        const plotType = (this.plotData.plot_type || 'line').toLowerCase();
        const hasTimeData = this.plotData.data && this.plotData.data.some(d => d.date);

        // Debug logging
        console.log('🔍 Chart Controls Debug:', {
            hasData: !!this.plotData.data,
            dataLength: this.plotData.data?.length,
            firstDataPoint: this.plotData.data?.[0],
            hasTimeData: hasTimeData,
            plotType: plotType
        });

        // Don't show any top controls for cleaner interface
        return '';
    }

    bindControlEvents() {
        const container = document.getElementById(this.containerId);
        const controlsDiv = container.parentNode.querySelector('.chart-controls');
        
        // If no controls div (like for line plots), skip binding
        if (!controlsDiv) {
            return;
        }
        
        // Time range presets
        controlsDiv.querySelectorAll('.time-preset-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.setTimeRange(e.target.dataset.range));
        });
        
        // Control buttons
        controlsDiv.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleAction(e.target.dataset.action));
        });
        
        // Export options
        controlsDiv.querySelectorAll('.export-option').forEach(option => {
            option.addEventListener('click', (e) => this.exportChart(e.target.dataset.format || e.target.closest('[data-format]').dataset.format));
        });
        
        // Setup time brush if applicable
        this.setupTimeBrush();
        this.setupFilterPanel();
    }

    setupTimeBrush() {
        const hasTimeData = this.plotData.data && this.plotData.data.some(d => d.date);
        if (!hasTimeData) return;

        const container = document.getElementById(this.containerId);
        const brushSvg = container.parentNode.querySelector('.time-brush-area');
        if (!brushSvg) return;

        const parseDate = d3.timeParse('%Y-%m-%d');
        const dates = this.plotData.data.map(d => parseDate(d.date)).filter(d => d);
        const timeScale = d3.scaleTime()
            .domain(d3.extent(dates))
            .range([10, 180]);

        const brush = d3.brushX()
            .extent([[10, 5], [180, 35]])
            .on('end', (event) => {
                if (event.selection) {
                    const [x0, x1] = event.selection.map(timeScale.invert);
                    this.applyTimeFilter(x0, x1);
                }
            });

        d3.select(brushSvg)
            .attr('width', 200)
            .attr('height', 40)
            .call(brush);
    }

    setupFilterPanel() {
        const container = document.getElementById(this.containerId);
        const filterPanel = container.parentNode.querySelector('.filter-panel');
        if (!filterPanel) return;

        // Get unique series and categories
        const series = [...new Set(this.plotData.data.map(d => d.series).filter(Boolean))];
        const categories = [...new Set(this.plotData.data.map(d => d.category).filter(Boolean))];
        
        filterPanel.innerHTML = `
            <div class="filter-panel-header">Chart Filters</div>
            ${series.length > 0 ? `
            <div class="filter-section">
                <div class="filter-section-title">Series</div>
                <div class="filter-checkboxes">
                    ${series.map(s => `
                        <div class="filter-checkbox">
                            <input type="checkbox" id="series-${s}" checked data-type="series" data-value="${s}">
                            <label for="series-${s}">${s}</label>
                        </div>
                    `).join('')}
                </div>
            </div>
            ` : ''}
            ${this.plotData.data.some(d => typeof d.value === 'number') ? `
            <div class="filter-section">
                <div class="filter-section-title">Value Range</div>
                <div class="filter-range-slider">
                    <input type="range" id="value-min" min="${d3.min(this.plotData.data, d => d.value)}" max="${d3.max(this.plotData.data, d => d.value)}" value="${d3.min(this.plotData.data, d => d.value)}">
                    <input type="range" id="value-max" min="${d3.min(this.plotData.data, d => d.value)}" max="${d3.max(this.plotData.data, d => d.value)}" value="${d3.max(this.plotData.data, d => d.value)}">
                    <div class="filter-range-values">
                        <span>${d3.min(this.plotData.data, d => d.value).toLocaleString()}</span>
                        <span>${d3.max(this.plotData.data, d => d.value).toLocaleString()}</span>
                    </div>
                </div>
            </div>
            ` : ''}
        `;

        // Bind filter events
        filterPanel.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => this.applyFilters());
        });
        
        filterPanel.querySelectorAll('input[type="range"]').forEach(slider => {
            slider.addEventListener('input', () => this.applyFilters());
        });
    }

    setTimeRange(range) {
        // Update button states
        const container = document.getElementById(this.containerId);
        const controlsDiv = container.parentNode.querySelector('.chart-controls');
        
        if (controlsDiv) {
            controlsDiv.querySelectorAll('.time-preset-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.range === range);
            });
        }

        // Apply time filter
        if (range === 'All') {
            this.currentTimeRange = null;
        } else {
            // Get the latest date from the data
            const parseDate = d3.timeParse('%Y-%m-%d');
            const dates = this.plotData.data.map(d => parseDate(d.date)).filter(d => d);
            const maxDate = d3.max(dates);

            const years = parseInt(range.replace('Y', ''));
            const startDate = new Date(maxDate.getFullYear() - years, maxDate.getMonth(), maxDate.getDate());
            this.currentTimeRange = [startDate, maxDate];
        }
        
        this.updateChart();
    }

    handleAction(action) {
        switch (action) {
            case 'toggle-filters':
                this.toggleFilterPanel();
                break;
            case 'toggle-export':
                this.toggleExportMenu();
                break;
            case 'toggle-sync':
                this.toggleSync();
                break;
        }
    }


    toggleFilterPanel() {
        const container = document.getElementById(this.containerId);
        const filterPanel = container.parentNode.querySelector('.filter-panel');
        if (filterPanel) {
            const isVisible = filterPanel.style.display !== 'none';
            filterPanel.style.display = isVisible ? 'none' : 'block';
        }
    }

    toggleExportMenu() {
        const container = document.getElementById(this.containerId);
        const exportMenu = container.parentNode.querySelector('.export-menu');
        if (exportMenu) {
            const isVisible = exportMenu.style.display !== 'none';
            exportMenu.style.display = isVisible ? 'none' : 'block';
        }
    }

    applyTimeFilter(startDate, endDate) {
        this.currentTimeRange = [startDate, endDate];
        this.updateChart();
    }

    applyFilters() {
        const container = document.getElementById(this.containerId);
        const filterPanel = container.parentNode.querySelector('.filter-panel');
        
        // Collect active filters
        this.activeFilters.clear();
        
        // Series filters
        const seriesCheckboxes = filterPanel.querySelectorAll('input[data-type="series"]:checked');
        const activeSeries = Array.from(seriesCheckboxes).map(cb => cb.dataset.value);
        if (activeSeries.length > 0) {
            this.activeFilters.set('series', activeSeries);
        }
        
        // Value range filters
        const minSlider = filterPanel.querySelector('#value-min');
        const maxSlider = filterPanel.querySelector('#value-max');
        if (minSlider && maxSlider) {
            this.activeFilters.set('valueRange', [+minSlider.value, +maxSlider.value]);
        }
        
        this.updateChart();
    }

    getFilteredData() {
        let filteredData = [...this.plotData.data];
        
        // Apply time range filter
        if (this.currentTimeRange) {
            const [startDate, endDate] = this.currentTimeRange;
            const parseDate = d3.timeParse('%Y-%m-%d');
            filteredData = filteredData.filter(d => {
                if (!d.date) return true;
                const date = parseDate(d.date);
                return date >= startDate && date <= endDate;
            });
        }
        
        // Apply series filter
        if (this.activeFilters.has('series')) {
            const activeSeries = this.activeFilters.get('series');
            filteredData = filteredData.filter(d => !d.series || activeSeries.includes(d.series));
        }
        
        // Apply value range filter
        if (this.activeFilters.has('valueRange')) {
            const [min, max] = this.activeFilters.get('valueRange');
            filteredData = filteredData.filter(d => d.value >= min && d.value <= max);
        }
        
        return filteredData;
    }

    updateChart() {
        const filteredData = this.getFilteredData();
        const updatedPlotData = { ...this.plotData, data: filteredData };
        renderD3Chart(this.containerId, updatedPlotData);
        
        // Notify sync group if active
        if (this.syncGroup) {
            this.notifySyncGroup();
        }
    }

    exportChart(format) {
        switch (format) {
            case 'png':
                window.downloadD3Chart(this.containerId, `chart_${Date.now()}.png`);
                break;
            case 'svg':
                this.exportSVG();
                break;
            case 'csv':
                this.exportCSV();
                break;
            case 'interactive':
                this.exportInteractiveHTML();
                break;
        }
    }

    exportCSV() {
        const data = this.getFilteredData();
        const csv = d3.csvFormat(data);
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `chart_data_${Date.now()}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }

    exportSVG() {
        const container = document.getElementById(this.containerId);
        const svg = container.querySelector('svg');
        if (svg) {
            const serializer = new XMLSerializer();
            const svgString = serializer.serializeToString(svg);
            const blob = new Blob([svgString], { type: 'image/svg+xml' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `chart_${Date.now()}.svg`;
            a.click();
            URL.revokeObjectURL(url);
        }
    }

    toggleSync() {
        // Implementation for chart synchronization
        if (this.syncGroup) {
            this.leaveSyncGroup();
        } else {
            this.joinSyncGroup('default');
        }
    }

    joinSyncGroup(groupName) {
        this.syncGroup = groupName;
        if (!window.chartSyncGroups.has(groupName)) {
            window.chartSyncGroups.set(groupName, new Set());
        }
        window.chartSyncGroups.get(groupName).add(this);
        this.updateSyncIndicator(true);
    }

    leaveSyncGroup() {
        if (this.syncGroup) {
            const group = window.chartSyncGroups.get(this.syncGroup);
            if (group) {
                group.delete(this);
            }
            this.syncGroup = null;
            this.updateSyncIndicator(false);
        }
    }

    updateSyncIndicator(active) {
        const container = document.getElementById(this.containerId);
        let indicator = container.querySelector('.chart-sync-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'chart-sync-indicator';
            container.appendChild(indicator);
        }
        indicator.classList.toggle('active', active);
    }

    notifySyncGroup() {
        if (!this.syncGroup) return;
        
        const group = window.chartSyncGroups.get(this.syncGroup);
        if (group) {
            group.forEach(chart => {
                if (chart !== this) {
                    // Sync time range
                    chart.currentTimeRange = this.currentTimeRange;
                    chart.updateChart();
                }
            });
        }
    }
}

// Data brushing functionality
function addDataBrushing(svg, g, width, height, plotType, data, xScale, yScale, containerId) {
    // Select Mode button and brushing feature removed for cleaner interface
}

// D3 Chart Rendering Function
function renderD3Chart(containerId, plotData, preselectedVisible) {
    // Check if D3 is available
    if (typeof d3 === 'undefined') {
        console.error('D3.js is not loaded');
        const container = document.getElementById(containerId);
        container.innerHTML = '<div style="padding: 2rem; text-align: center; color: #ef4444;">D3.js library is required for interactive charts</div>';
        return;
    }
    
    const container = d3.select(`#${containerId}`);
    const containerNode = container.node();
    // Persist the original, full dataset on the container so we can re-render
    // categorical charts without spacing gaps after legend toggles
    if (!containerNode.__originalPlotData) {
        try {
            containerNode.__originalPlotData = JSON.parse(JSON.stringify(plotData));
        } catch (e) {
            // Fallback shallow copy
            containerNode.__originalPlotData = { ...plotData, data: Array.isArray(plotData.data) ? [...plotData.data] : plotData.data };
        }
    }
    
    // Preserve original chart dimensions to prevent size changes on reset
    let rect = containerNode.getBoundingClientRect();
    if (containerNode.__originalDimensions) {
        rect = containerNode.__originalDimensions;
    } else {
        // Store original dimensions on first render
        containerNode.__originalDimensions = {
            width: rect.width,
            height: rect.height
        };
    }
    
    // Get plot type early for margin calculations
    const plotType = (plotData.plot_type || 'line').toLowerCase();
    
    // Chart dimensions
    // Keep right margin small; place legend below to maximize plot width
    const margin = { top: 20, right: 20, bottom: 25, left: 80 };
    
    // Adjust top margin if there's a title
    if (plotData.title) {
        margin.top = 45;
    }
    
    // Adjust margins based on chart type
    if ((plotType === 'bar' || plotType === 'stacked') && plotData.series_info && plotData.series_info.length > 1) {
        margin.top = plotData.title ? 110 : 90; // Extra space for centered legend to prevent overlap
    } else if (plotType === 'box') {
        // Box plots with no X-axis labels need minimal bottom margin
        margin.bottom = 35; // Just enough space for the axis line and some padding
    }
    
    const width = rect.width - margin.left - margin.right;
    // Use a larger plot height for better visibility, especially for stacked charts
    let basePlotHeight = Math.max(300, Math.min(400, rect.height * 0.6)); // At least 300px, max 400px for container fit
    if (plotType === 'stacked') {
        basePlotHeight = Math.max(350, Math.min(450, rect.height * 0.7)); // Taller for stacked charts
    }
    let height = basePlotHeight;
    
    // Clear any existing chart
    container.selectAll('*').remove();
    
    // Create tooltip div if it doesn't exist
    let tooltip = d3.select('body').select('.d3-tooltip');
    if (tooltip.empty()) {
        tooltip = d3.select('body').append('div')
            .attr('class', 'd3-tooltip')
            .style('position', 'absolute')
            .style('pointer-events', 'none')
            .style('opacity', 0);
    }
    
    // Create SVG with initial height (will be adjusted later for legend)
    const buttonSpace = 40; // Space for download/reset buttons
    const totalNeededHeight = basePlotHeight + margin.top + margin.bottom + buttonSpace;
    const svgHeight = Math.min(totalNeededHeight, rect.height - 20); // Ensure it fits in container with some padding
    
    const svg = container
        .append('svg')
        .attr('width', rect.width)
        .attr('height', svgHeight);
    
    // Add entry animation
    animateChartEntry(container);
    
    // Set initial container height
    containerNode.style.height = `${svgHeight + 20}px`;
    
    // Initialize advanced chart controller if not already done
    if (!window.chartStates.has(containerId)) {
        const controller = new ChartController(containerId, plotData);
        window.chartStates.set(containerId, controller);
    }
    
    // For line plots, add a simple download button since we removed controls
    if (plotType === 'line') {
        const downloadBtn = svg.append('g')
            .attr('class', 'simple-download-btn')
            .attr('transform', `translate(${rect.width - 40}, 10)`)
            .style('cursor', 'pointer')
            .on('click', () => {
                window.downloadD3Chart(containerId, `${plotData.title || 'chart'}.png`);
            });
        
        downloadBtn.append('rect')
            .attr('width', 30)
            .attr('height', 20)
            .attr('rx', 3)
            .attr('fill', '#f3f4f6')
            .attr('stroke', '#d1d5db');
        
        downloadBtn.append('text')
            .attr('x', 15)
            .attr('y', 13)
            .attr('text-anchor', 'middle')
            .style('font-size', '10px')
            .style('font-weight', '600')
            .style('fill', '#374151')
            .text('⬇');
    }
    
    // No zoom functionality - removed for cleaner interface
    
    // Add editable title to the chart
    if (plotData.title) {
        const titleElement = svg.append('text')
            .attr('x', rect.width / 2)
            .attr('y', 20)
            .attr('text-anchor', 'middle')
            .style('font-family', "'Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif")
            .style('font-size', '18px')
            .style('font-weight', '300')
            .style('letter-spacing', '0.5px')
            .style('fill', '#1e293b')
            .style('opacity', '0.9')
            .style('cursor', 'pointer')
            .text(plotData.title);
        
        // Add editing functionality
        titleElement.on('dblclick', function(event) {
            event.stopPropagation();
            makeEditableTitle(this, plotData, containerId);
        });
        
        // Add hover effect to indicate it's editable
        titleElement.on('mouseover', function() {
            d3.select(this)
                .style('opacity', '0.7')
                .style('text-decoration', 'underline');
        });
        
        titleElement.on('mouseout', function() {
            d3.select(this)
                .style('opacity', '0.9')
                .style('text-decoration', 'none');
        });
    }
    
    const g = svg.append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);
    
    // Process data
    const data = plotData.data;
    // Data validation
    
    if (!data || data.length === 0) {
        g.append('text')
            .attr('x', width / 2)
            .attr('y', height / 2)
            .attr('text-anchor', 'middle')
            .text('No data available');
        return;
    }
    
    // Parse dates and prepare data (only when date exists)
    const parseDate = d3.timeParse('%Y-%m-%d');
    data.forEach(d => {
        if (d.date) {
            d.date = parseDate(d.date);
        }
        if (d.value !== undefined) {
            d.value = +d.value;
        }
    });
    
    // Group data by series
    const series = d3.group(data.filter(d => d.series !== undefined), d => d.series);
    
    // Scales (time for line, band for bar/box)
    let xScale;
    let yScale;
    let categories = [];
    if (plotType === 'line') {
        xScale = d3.scaleTime()
            .domain(d3.extent(data, d => d.date))
            .range([0, width]);
        yScale = d3.scaleLinear()
            .domain(d3.extent(data, d => d.value))
            .nice()
            .range([height, 0]);
    } else if (plotType === 'bar' || plotType === 'box' || plotType === 'stacked' || plotType === 'stacked_bar') {
        categories = Array.from(new Set(data.map(d => d.category || d.series)));
        // Sort categories numerically for proper year ordering
        if (plotType === 'stacked' || plotType === 'bar' || plotType === 'stacked_bar') {
            categories.sort((a, b) => +a - +b);
        }
        xScale = d3.scaleBand().domain(categories).range([0, width]).padding(0.2);

        if (plotType === 'stacked' || plotType === 'stacked_bar') {
            // For stacked charts, calculate the maximum stacked height per category using MW values
            const stackTotals = d3.rollup(data,
                values => d3.sum(values, d => d.value), // Use MW values for scale
                d => d.category
            );
            const yMax = d3.max(Array.from(stackTotals.values()));
            yScale = d3.scaleLinear().domain([0, yMax]).nice().range([height, 0]);
        } else {
            const yMax = plotType === 'box'
                ? d3.max(data, d => Math.max(d.max, d.q3, d.q2, d.q1, d.min))
                : d3.max(data, d => d.value);
            const yMin = plotType === 'box'
                ? d3.min(data, d => Math.min(d.min, d.q1, d.q2, d.q3))
                : 0; // Always start from 0 for bar charts to show small values properly
            yScale = d3.scaleLinear().domain([yMin, yMax]).nice().range([height, 0]);
        }
    } else if (plotType === 'pie') {
        // For pies, no axes, but we still compute categories for legends
        categories = Array.from(new Set(data.map(d => d.category || d.series)));
    }
    
    // Number formatter for clean Y-axis labels
    const formatYAxis = (value) => {
        const absValue = Math.abs(value);
        if (absValue >= 1e9) {
            return (value / 1e9).toFixed(1).replace(/\.0$/, '') + 'B';
        } else if (absValue >= 1e6) {
            return (value / 1e6).toFixed(1).replace(/\.0$/, '') + 'M';
        } else if (absValue >= 1e3) {
            return (value / 1e3).toFixed(1).replace(/\.0$/, '') + 'K';
        }
        return value.toString();
    };

    // Color scale - Distinct colors for better differentiation
    const becquerelColors = [
        '#EB8F47', // Persian orange (primary)
        '#000A55', // Federal blue
        '#949CFF', // Vista Blue
        '#C5C5C5', // Silver
        '#E5A342', // Hunyadi yellow
        '#f97316', // Dark orange (fallback)
        '#22c55e', // Green (fallback)
        '#e11d48', // Red (fallback)
        '#8b5cf6', // Purple (fallback)
        '#06b6d4', // Cyan (fallback)
        '#84cc16', // Lime green (fallback)
        '#ec4899'  // Pink (fallback)
    ];
    const colorScale = d3.scaleOrdinal(becquerelColors);
    
    // Line generator
    const line = d3.line()
        .x(d => xScale(d.date))
        .y(d => yScale(d.value))
        .curve(d3.curveMonotoneX);
    
    // Add axes with enhanced styling for line charts
    if (plotType === 'line') {
        // Add grid lines for better readability
        const xGridLines = g.append('g')
            .attr('class', 'grid x-grid')
            .attr('transform', `translate(0,${height})`);
        
        const yGridLines = g.append('g')
            .attr('class', 'grid y-grid');
        
        // Adaptive ticks based on timespan for better readability
        const minDate = d3.min(data, d => d.date);
        const maxDate = d3.max(data, d => d.date);
        const spanDays = (maxDate - minDate) / (1000 * 60 * 60 * 24);
        let interval, formatter, rotation = 0;
        
        if (spanDays <= 90) { // ~3 months → weekly
            interval = d3.timeWeek.every(1);
            formatter = d3.timeFormat('%b %d');
            rotation = -45;
        } else if (spanDays <= 365) { // ≤ 1 year → monthly
            interval = d3.timeMonth.every(1);
            formatter = d3.timeFormat('%Y-%m');
            rotation = -45;
        } else if (spanDays <= 1095) { // ≤ 3 years → quarterly
            interval = d3.timeMonth.every(6);
            formatter = d3.timeFormat('%Y-%m');
            rotation = -45;
        } else if (spanDays <= 2190) { // ≤ 6 years → yearly
            interval = d3.timeYear.every(1);
            formatter = d3.timeFormat('%Y');
            rotation = 0;
        } else { // very long → every 2 years
            interval = d3.timeYear.every(2);
            formatter = d3.timeFormat('%Y');
            rotation = 0;
        }
        
        // Create axes with enhanced styling and clean number formatting
        const xAxis = d3.axisBottom(xScale).ticks(interval).tickFormat(formatter);
        const yAxis = d3.axisLeft(yScale).ticks(6).tickFormat(formatYAxis);
        
        // Add grid lines first (so they appear behind the data)
        xGridLines.call(d3.axisBottom(xScale)
            .ticks(interval)
            .tickSize(-height)
            .tickFormat('')
        ).style('opacity', 0.3);
        
        yGridLines.call(d3.axisLeft(yScale)
            .ticks(6)
            .tickSize(-width)
            .tickFormat('')
        ).style('opacity', 0.1);
        
        // Add main axes
        g.append('g')
            .attr('class', 'x-axis axis')
            .attr('transform', `translate(0,${height})`)
            .call(xAxis)
            .selectAll('text')
            .attr('transform', rotation !== 0 ? `rotate(${rotation})` : 'rotate(0)')
            .style('text-anchor', rotation !== 0 ? 'end' : 'middle');
    } else if (plotType === 'box') {
        // For box charts, show only axis line without labels (legend provides all info)
        g.append('g')
            .attr('class', 'x-axis')
            .attr('transform', `translate(0,${height})`)
            .call(d3.axisBottom(xScale).tickFormat('').tickSize(0))
            .select('.domain')
            .style('stroke', '#d1d5db')
            .style('stroke-width', 1);
    } else if (plotType === 'bar' || plotType === 'stacked' || plotType === 'stacked_bar') {
        // For bar/stacked/stacked_bar charts, add year labels directly below bars (no axis line)
        const step = Math.max(1, Math.ceil(categories.length / 12));
        const tickVals = categories.filter((_, i) => i % step === 0);
        
        // Check if segment labels are hidden to make x-axis more prominent
        const shouldShowSegmentLabels = data.length > 0 ? data[0].show_segment_labels !== false : true;
        const xAxisFontSize = shouldShowSegmentLabels ? '12px' : '13px'; // Slightly larger when segment labels are hidden
        const xAxisFontWeight = shouldShowSegmentLabels ? '500' : '600'; // Bolder when segment labels are hidden
        
        g.selectAll('text.bar-year-label')
            .data(tickVals)
            .enter()
            .append('text')
            .attr('class', 'bar-year-label')
            .attr('x', d => xScale(d) + xScale.bandwidth() / 2)
            .attr('y', height + 20) // Position below the bars
            .attr('text-anchor', 'middle')
            .style('font-family', "'Inter', 'Segoe UI', 'Roboto', sans-serif")
            .style('font-size', xAxisFontSize)
            .style('font-weight', xAxisFontWeight)
            .style('fill', '#374151')
            .text(d => d);
    }

    // Determine if bar chart should show Y-axis based on number of bars
    const barCount = plotType === 'bar' ? categories.length : 0;
    const showBarYAxis = plotType === 'bar' && barCount > 8; // Show Y-axis if more than 8 bars
    const showBarValueLabels = plotType === 'bar' && barCount <= 8; // Only show value labels if 8 or fewer bars

    // Add Y axis for charts that need it
    if (plotType !== 'pie' && plotType !== 'stacked' && plotType !== 'stacked_bar') {
        if (plotType === 'line') {
            // For line charts, Y-axis with enhanced styling and clean number formatting
            g.append('g')
                .attr('class', 'y-axis axis')
                .call(d3.axisLeft(yScale).ticks(6).tickFormat(formatYAxis));
        } else if (plotType === 'bar' && showBarYAxis) {
            // For bar charts with many bars, show Y-axis instead of labels
            g.append('g')
                .attr('class', 'y-axis axis')
                .call(d3.axisLeft(yScale).ticks(6).tickFormat(formatYAxis));
        }
        // For bar charts with few bars, no Y-axis (value labels are shown instead)
    }

    // Add axis labels for charts that have y-axis displayed
    const shouldShowYAxisLabel = (() => {
        if (plotType === 'pie' || plotType === 'stacked' || plotType === 'stacked_bar') return false; // Never show for stacked charts
        if (plotType === 'bar') return showBarYAxis; // Only show Y-axis label for bar charts with many bars
        return true; // For line and other charts
    })();

    const shouldShowXAxisLabel = (() => {
        // Don't show X-axis label for line charts (ticks are self-explanatory with dates)
        if (plotType === 'line') return false;
        // Don't show X-axis label for box plots since legend provides all info
        if (plotType === 'box') return false;
        // Don't show X-axis label for stacked/stacked_bar charts (year labels below bars are sufficient)
        if (plotType === 'stacked' || plotType === 'stacked_bar') return false;
        return shouldShowYAxisLabel; // Use same logic as Y-axis for other charts
    })();
    
    if (shouldShowYAxisLabel) {
        // Enhanced Y-axis label with better typography
        g.append('text')
            .attr('transform', 'rotate(-90)')
            .attr('y', 0 - margin.left + 15)
            .attr('x', 0 - (height / 2))
            .attr('dy', '0.35em')
            .style('text-anchor', 'middle')
            .style('font-size', plotType === 'line' ? '14px' : '12px')
            .style('font-weight', plotType === 'line' ? '600' : '500')
            .style('font-family', "'Inter', 'Segoe UI', 'Roboto', sans-serif")
            .style('fill', '#374151')
            .style('letter-spacing', '0.025em')
            .text(plotData.y_axis_label);
        
        // Enhanced X-axis label with better typography and positioning (if enabled)
        if (shouldShowXAxisLabel && plotData.x_axis_label) {
            const xLabelYOffset = plotType === 'line' ? 5 : 10;
            g.append('text')
                .attr('transform', `translate(${width / 2}, ${height + margin.bottom - xLabelYOffset})`)
                .style('text-anchor', 'middle')
                .style('font-size', plotType === 'line' ? '14px' : '12px')
                .style('font-weight', plotType === 'line' ? '600' : '500')
                .style('font-family', "'Inter', 'Segoe UI', 'Roboto', sans-serif")
                .style('fill', '#374151')
                .style('letter-spacing', '0.025em')
                .text(plotData.x_axis_label);
        }
    }
    
    // Draw series by plot type
    if (plotType === 'line') {
        // Create gradient definitions for enhanced visuals
        const defs = svg.append('defs');
        
        // Create drop shadow filter
        const filter = defs.append('filter')
            .attr('id', 'line-shadow')
            .attr('x', '-20%')
            .attr('y', '-20%')
            .attr('width', '140%')
            .attr('height', '140%');
        
        filter.append('feDropShadow')
            .attr('dx', 0)
            .attr('dy', 2)
            .attr('stdDeviation', 2)
            .attr('flood-opacity', 0.15);
        
        series.forEach((values, seriesName) => {
            const sortedValues = values.sort((a, b) => a.date - b.date);
            const safe = cssSafe(seriesName);
            const baseColor = colorScale(seriesName);
            
            // Create gradient for area fill
            const gradient = defs.append('linearGradient')
                .attr('id', `area-gradient-${safe}`)
                .attr('x1', '0%')
                .attr('y1', '0%')
                .attr('x2', '0%')
                .attr('y2', '100%');
            
            gradient.append('stop')
                .attr('offset', '0%')
                .attr('stop-color', baseColor)
                .attr('stop-opacity', 0.4);
            
            gradient.append('stop')
                .attr('offset', '100%')
                .attr('stop-color', baseColor)
                .attr('stop-opacity', 0.05);
            
            // Create area fill under the line
            const area = d3.area()
                .x(d => xScale(d.date))
                .y0(yScale.range()[0]) // Bottom of chart
                .y1(d => yScale(d.value))
                .curve(d3.curveMonotoneX);
            
            // Add the area fill
            const areaPath = g.append('path')
                .datum(sortedValues)
                .attr('class', `series-area series-${safe}`)
                .attr('fill', `url(#area-gradient-${safe})`)
                .attr('d', area)
                .style('opacity', 0);
            
            // Enhanced line with improved styling
            const path = g.append('path')
                .datum(sortedValues)
                .attr('class', `series-line series-${safe}`)
                .attr('fill', 'none')
                .attr('stroke', baseColor)
                .attr('stroke-width', 3)
                .style('stroke-linejoin', 'round')
                .style('stroke-linecap', 'round')
                .style('vector-effect', 'non-scaling-stroke')
                .style('filter', 'url(#line-shadow)')
                .attr('d', line);
            
            // Animate line drawing
            const totalLength = path.node().getTotalLength();
            path
                .attr('stroke-dasharray', totalLength + ' ' + totalLength)
                .attr('stroke-dashoffset', totalLength)
                .transition()
                .duration(1500)
                .ease(d3.easeQuadInOut)
                .attr('stroke-dashoffset', 0)
                .on('end', function() {
                    // Remove dash array after animation
                    d3.select(this).attr('stroke-dasharray', null);
                });
            
            // Animate area fill after line animation starts
            areaPath.transition()
                .delay(300)
                .duration(1200)
                .ease(d3.easeQuadInOut)
                .style('opacity', 0.7);

            // Show fewer points when dense; hide completely if extremely dense
            const maxDots = 40; // target number of dots to display per series
            const total = sortedValues.length;
            const showDots = total <= 200; // hide dots if extremely dense
            const stride = Math.max(1, Math.ceil(total / maxDots));
            const dotsData = showDots ? sortedValues.filter((_, i) => i % stride === 0 || i === total - 1) : [];

            const circles = g.selectAll(`circle.series-${safe}`)
                .data(dotsData)
                .enter().append('circle')
                .attr('class', `series-dot series-${safe}`)
                .attr('cx', d => xScale(d.date))
                .attr('cy', d => yScale(d.value))
                .attr('r', 0) // Start with 0 radius
                .style('stroke', '#fff')
                .style('stroke-width', 0.5)
                .attr('fill', colorScale(seriesName))
                .style('cursor', 'pointer')
                .style('opacity', 0); // Start invisible
            
            // Animate the circles
            circles.transition()
                .delay((d, i) => 1500 + i * 50) // Start after line animation, staggered
                .duration(300)
                .ease(d3.easeBackOut)
                .attr('r', 2.5)
                .style('opacity', 1);
            
            // Add event handlers after creating the circles
            circles.on('mouseover', function(event, d) {
                    // Highlight the point
                    d3.select(this)
                        .transition()
                        .duration(100)
                        .attr('r', 4)
                        .style('stroke-width', 2);
                    
                    // Use enhanced tooltip
                    tooltip.transition()
                        .duration(200)
                        .style('opacity', 0.9);
                    
                    tooltip.html(createEnhancedTooltip(d, seriesName, plotData, event))
                        .style('left', (event.pageX + 10) + 'px')
                        .style('top', (event.pageY - 28) + 'px');
                })
                .on('mouseout', function(event, d) {
                    // Reset the point
                    d3.select(this)
                        .transition()
                        .duration(100)
                        .attr('r', 2.5)
                        .style('stroke-width', 0.5);
                    
                    // Hide tooltip
                    tooltip.transition()
                        .duration(500)
                        .style('opacity', 0);
                });
        });
        
        // Add crosshair functionality for line charts
        const crosshair = g.append('g')
            .attr('class', 'crosshair')
            .style('display', 'none');
            
        // Vertical line
        crosshair.append('line')
            .attr('class', 'crosshair-x')
            .attr('y1', 0)
            .attr('y2', height)
            .style('stroke', '#666')
            .style('stroke-width', 1)
            .style('stroke-dasharray', '3,3')
            .style('opacity', 0.7);
            
        // Horizontal line
        crosshair.append('line')
            .attr('class', 'crosshair-y')
            .attr('x1', 0)
            .attr('x2', width)
            .style('stroke', '#666')
            .style('stroke-width', 1)
            .style('stroke-dasharray', '3,3')
            .style('opacity', 0.7);
            
        // Invisible overlay for mouse tracking
        const overlay = svg.append('rect')
            .attr('class', 'overlay')
            .attr('x', margin.left)
            .attr('y', margin.top)
            .attr('width', width)
            .attr('height', height)
            .style('fill', 'none')
            .style('pointer-events', 'all')
            .on('mouseover', () => crosshair.style('display', null))
            .on('mouseout', () => {
                crosshair.style('display', 'none');
                tooltip.transition().duration(500).style('opacity', 0);
            })
            .on('mousemove', function(event) {
                const [mouseX, mouseY] = d3.pointer(event, this);
                
                // Update crosshair position
                crosshair.select('.crosshair-x')
                    .attr('x1', mouseX)
                    .attr('x2', mouseX);
                    
                crosshair.select('.crosshair-y')
                    .attr('y1', mouseY)
                    .attr('y2', mouseY);
                    
                // Find closest data point for tooltip
                const xDate = xScale.invert(mouseX);
                let closestPoint = null;
                let minDistance = Infinity;
                let closestSeries = '';
                
                series.forEach((values, seriesName) => {
                    values.forEach(d => {
                        const distance = Math.abs(d.date - xDate);
                        if (distance < minDistance) {
                            minDistance = distance;
                            closestPoint = d;
                            closestSeries = seriesName;
                        }
                    });
                });
                
                // Show tooltip for closest point
                if (closestPoint) {
                    tooltip.transition()
                        .duration(100)
                        .style('opacity', 0.9);
                    
                    tooltip.html(createEnhancedTooltip(closestPoint, closestSeries, plotData, event))
                        .style('left', (event.pageX + 10) + 'px')
                        .style('top', (event.pageY - 28) + 'px');
                }
            });

      } else if (plotType === 'stacked_bar') {
          // Stacked bar chart - segments stack on top of each other using MW values
          // Group data by category (year) and calculate cumulative positions in MW
          const stackedData = Array.from(d3.group(data, d => d.category), ([key, values]) => {
              values.sort((a, b) => a.stack.localeCompare(b.stack)); // Consistent ordering
              let cumulative = 0;
              return values.map(d => {
                  const result = {
                      ...d,
                      series: d.stack,  // Map stack to series for compatibility
                      y0: cumulative,
                      y1: cumulative + d.value  // Use MW values for stacking
                  };
                  cumulative += d.value;
                  return result;
              });
          }).flat();

          const stackedBars = g.selectAll('rect.stacked-bar')
              .data(stackedData)
              .enter()
              .append('rect')
              .attr('class', d => `stacked-bar series-${cssSafe(d.series)}`)
              .attr('x', d => xScale(d.category))
              .attr('width', xScale.bandwidth())
              .attr('y', d => yScale(d.y0)) // Start from bottom position
              .attr('height', 0) // Start with 0 height
              .attr('fill', d => {
                  // Use colors from stack_info if available
                  if (plotData.stack_info) {
                      const stackInfo = plotData.stack_info.find(s => s.name === d.stack);
                      if (stackInfo) return stackInfo.color;
                  }
                  return colorScale(d.series);
              })
              .style('cursor', 'pointer');

          // Animate stacked bars
          stackedBars.transition()
              .delay((d, i) => i * 50) // Staggered animation
              .duration(800)
              .ease(d3.easeQuadOut)
              .attr('y', d => yScale(d.y1))
              .attr('height', d => yScale(d.y0) - yScale(d.y1));

          // Add hover effects and tooltips to stacked bars
          stackedBars.on('mouseover', function(event, d) {
              // Highlight the segment
              d3.select(this)
                  .transition()
                  .duration(200)
                  .style('opacity', 0.8)
                  .style('stroke', '#333')
                  .style('stroke-width', 2);

              // Show enhanced tooltip
              tooltip.transition()
                  .duration(200)
                  .style('opacity', 0.9);

              tooltip.html(createEnhancedTooltip(d, d.series, plotData, event))
                  .style('left', (event.pageX + 10) + 'px')
                  .style('top', (event.pageY - 28) + 'px');
          })
          .on('mouseout', function(event, d) {
              // Reset the segment
              d3.select(this)
                  .transition()
                  .duration(200)
                  .style('opacity', 1)
                  .style('stroke', 'none');

              // Hide tooltip
              tooltip.transition()
                  .duration(500)
                  .style('opacity', 0);
          });

          // Calculate totals for each category and add sum labels on top
          const categoryTotals = Array.from(d3.group(data, d => d.category), ([category, values]) => {
              const total = d3.sum(values, d => d.value);
              return { category, total };
          });

          // Add total sum labels on top of stacked bars
          g.selectAll('text.stack-total-label')
              .data(categoryTotals)
              .enter()
              .append('text')
              .attr('class', 'stack-total-label')
              .attr('x', d => xScale(d.category) + xScale.bandwidth() / 2)
              .attr('y', d => yScale(d.total) - 8) // 8px above the top of the stack
              .attr('text-anchor', 'middle')
              .style('font-family', "'Inter', 'Segoe UI', 'Roboto', sans-serif")
              .style('font-size', '13px')
              .style('font-weight', '700')
              .style('fill', '#1f2937')
              .style('text-shadow', '1px 1px 2px rgba(255,255,255,0.8)')
              .text(d => {
                  // Format the total value nicely
                  const value = d.total;
                  if (value === 0 || value === 0.0) {
                      return "0";
                  } else if (value >= 1000000) {
                      return `${(value/1000000).toFixed(1)}GW`;
                  } else if (value >= 10000) {
                      const formatted = value/1000;
                      if (formatted == Math.floor(formatted)) {
                          return `${Math.floor(formatted)}k`;
                      } else {
                          return `${formatted.toFixed(1)}k`;
                      }
                  } else if (value >= 1000) {
                      return `${(value/1000).toFixed(1)}k`;
                  } else if (value >= 100) {
                      return `${Math.round(value)}`;
                  } else if (value >= 1) {
                      if (value == Math.floor(value)) {
                          return `${Math.floor(value)}`;
                      } else {
                          return `${value.toFixed(1)}`;
                      }
                  } else {
                      return `${value.toFixed(2)}`;
                  }
              });

          // Add individual segment values for larger segments (with smart visibility control)
          const shouldShowSegmentLabels = data.length > 0 ? data[0].show_segment_labels !== false : true;
          const barWidth = xScale.bandwidth();
          const filteredStackedData = shouldShowSegmentLabels
              ? stackedData.filter(d => {
                  const segmentHeight = yScale(d.y0) - yScale(d.y1);
                  // Only show labels for segments > 5% of total height AND bar is wide enough
                  return (d.y1 - d.y0) > (yScale.domain()[1] * 0.05) && barWidth >= 40 && segmentHeight >= 30;
              })
              : []; // Hide all segment labels when there are too many bars

          g.selectAll('text.segment-value-label')
              .data(filteredStackedData)
              .enter()
              .append('text')
              .attr('class', 'segment-value-label')
              .attr('x', d => xScale(d.category) + xScale.bandwidth() / 2)
              .attr('y', d => yScale((d.y0 + d.y1) / 2)) // Middle of the segment
              .attr('text-anchor', 'middle')
              .attr('dominant-baseline', 'middle')
              .style('font-family', "'Inter', 'Segoe UI', 'Roboto', sans-serif")
              .style('font-size', '10px')
              .style('font-weight', '600')
              .style('fill', '#ffffff')
              .style('text-shadow', '1px 1px 2px rgba(0,0,0,0.7)')
              .style('pointer-events', 'none')
              .text(d => {
                  // Use backend's formatted value if available
                  if (d.formatted_value) {
                      return d.formatted_value;
                  }
                  // Fallback formatting
                  const value = d.value;
                  if (value === 0 || value === 0.0) {
                      return "0";
                  } else if (value >= 1000000) {
                      return `${(value/1000000).toFixed(1)}GW`;
                  } else if (value >= 1000) {
                      return `${(value/1000).toFixed(1)}k`;
                  } else if (value >= 1) {
                      if (value == Math.floor(value)) {
                          return `${Math.floor(value)}`;
                      } else {
                          return `${value.toFixed(1)}`;
                      }
                  } else {
                      return `${value.toFixed(2)}`;
                  }
              })
              .each(function() {
                  // Clip text to fit within bar width
                  const text = d3.select(this);
                  const textWidth = this.getComputedTextLength();
                  if (textWidth > barWidth - 4) {
                      // Hide text if it's too wide for the bar
                      text.style('display', 'none');
                  }
              });

      } else if (plotType === 'bar') {
          const bars = g.selectAll('rect.series-bar')
              .data(data)
              .enter()
              .append('rect')
              .attr('class', d => `series-bar series-${cssSafe(d.series)}`)
              .attr('x', d => xScale(d.category || d.series))
              .attr('width', xScale.bandwidth())
              .attr('y', height) // Start from bottom
              .attr('height', 0) // Start with 0 height
              .attr('fill', d => colorScale(d.series))
              .style('cursor', 'pointer');
          
          // Animate the bars
          bars.transition()
              .delay((d, i) => i * 100) // Staggered animation
              .duration(800)
              .ease(d3.easeQuadOut)
              .attr('y', d => yScale(d.value))
              .attr('height', d => height - yScale(d.value));
          
          // Add event handlers after creating bars
          bars.on('mouseover', function(event, d) {
                  // Highlight the bar
                  d3.select(this)
                      .transition()
                      .duration(100)
                      .style('opacity', 0.8)
                      .style('stroke', '#333')
                      .style('stroke-width', 2);
                  
                  // Use enhanced tooltip
                  tooltip.transition()
                      .duration(200)
                      .style('opacity', 0.9);
                  
                  tooltip.html(createEnhancedTooltip(d, d.series || '', plotData, event))
                      .style('left', (event.pageX + 10) + 'px')
                      .style('top', (event.pageY - 28) + 'px');
              })
              .on('mouseout', function(event, d) {
                  // Reset the bar
                  d3.select(this)
                      .transition()
                      .duration(100)
                      .style('opacity', 1)
                      .style('stroke', 'none');
                  
                  // Hide tooltip
                  tooltip.transition()
                      .duration(500)
                      .style('opacity', 0);
              });

          // Add value labels on bars (only if there are 8 or fewer bars)
          if (showBarValueLabels) {
              g.selectAll('text.bar-value-label')
                  .data(data)
                  .enter()
                  .append('text')
                  .attr('class', 'bar-value-label')
                  .attr('x', d => xScale(d.category || d.series) + xScale.bandwidth() / 2)
                  .attr('y', d => {
                      const barHeight = height - yScale(d.value);
                      // Position label in the middle of the bar if it's tall enough, otherwise above
                      if (barHeight > 30) {
                          return yScale(d.value) + barHeight / 2;
                      } else {
                          return yScale(d.value) - 8;
                      }
                  })
                  .attr('text-anchor', 'middle')
                  .attr('dominant-baseline', d => {
                      const barHeight = height - yScale(d.value);
                      return barHeight > 30 ? 'middle' : 'auto';
                  })
                  .style('font-family', "'Inter', 'Segoe UI', 'Roboto', sans-serif")
                  .style('font-size', '12px')
                  .style('font-weight', '600')
                  .style('fill', d => {
                      const barHeight = height - yScale(d.value);
                      // White text if inside tall bars, dark text if above short bars
                      return barHeight > 30 ? '#ffffff' : '#374151';
                  })
                  .style('text-shadow', d => {
                      const barHeight = height - yScale(d.value);
                      // Add shadow for readability
                      return barHeight > 30 ? '1px 1px 2px rgba(0,0,0,0.7)' : 'none';
                  })
                  .text(d => {
                      // Use backend's formatted value if available, otherwise format here
                      if (d.formatted_value) {
                          return d.formatted_value;
                      }
                      // Fallback formatting
                      const value = d.value;
                      // Handle zero explicitly to avoid formatting issues
                      if (value === 0 || value === 0.0) {
                          return "0";
                      } else if (value >= 1000) {
                          return (value / 1000).toFixed(0) + 'k';
                      }
                      return Math.round(value).toLocaleString();
                  });
          }
    } else if (plotType === 'stacked') {
        // Stacked bar chart - segments stack on top of each other using MW values
        // Group data by category (year) and calculate cumulative positions in MW
        const stackedData = Array.from(d3.group(data, d => d.category), ([key, values]) => {
            values.sort((a, b) => a.series.localeCompare(b.series)); // Consistent ordering
            let cumulative = 0;
            return values.map(d => {
                const result = {
                    ...d,
                    y0: cumulative,
                    y1: cumulative + d.value  // Use MW values for stacking
                };
                cumulative += d.value;
                return result;
            });
        }).flat();

                  const stackedBars = g.selectAll('rect.stacked-bar')
              .data(stackedData)
              .enter()
              .append('rect')
              .attr('class', d => `stacked-bar series-${cssSafe(d.series)}`)
              .attr('x', d => xScale(d.category))
              .attr('width', xScale.bandwidth())
              .attr('y', d => yScale(d.y0)) // Start from bottom position
              .attr('height', 0) // Start with 0 height
              .attr('fill', d => colorScale(d.series))
              .style('cursor', 'pointer');
          
          // Animate stacked bars
          stackedBars.transition()
              .delay((d, i) => i * 50) // Staggered animation
              .duration(800)
              .ease(d3.easeQuadOut)
              .attr('y', d => yScale(d.y1))
              .attr('height', d => yScale(d.y0) - yScale(d.y1));
          
          // Add hover effects and tooltips to stacked bars
          stackedBars.on('mouseover', function(event, d) {
              // Highlight the segment
              d3.select(this)
                  .transition()
                  .duration(200)
                  .style('opacity', 0.8)
                  .style('stroke', '#333')
                  .style('stroke-width', 2);
              
              // Show enhanced tooltip
              tooltip.transition()
                  .duration(200)
                  .style('opacity', 0.9);
              
              tooltip.html(createEnhancedTooltip(d, d.series, plotData, event))
                  .style('left', (event.pageX + 10) + 'px')
                  .style('top', (event.pageY - 28) + 'px');
          })
          .on('mouseout', function(event, d) {
              // Reset the segment
              d3.select(this)
                  .transition()
                  .duration(200)
                  .style('opacity', 1)
                  .style('stroke', 'none');
              
              // Hide tooltip
              tooltip.transition()
                  .duration(500)
                  .style('opacity', 0);
          });
          
          // Calculate totals for each category and add sum labels on top
          const categoryTotals = Array.from(d3.group(data, d => d.category), ([category, values]) => {
              const total = d3.sum(values, d => d.value);
              return { category, total };
          });
          
          // Add total sum labels on top of stacked bars
          g.selectAll('text.stack-total-label')
              .data(categoryTotals)
              .enter()
              .append('text')
              .attr('class', 'stack-total-label')
              .attr('x', d => xScale(d.category) + xScale.bandwidth() / 2)
              .attr('y', d => yScale(d.total) - 8) // 8px above the top of the stack
              .attr('text-anchor', 'middle')
              .style('font-family', "'Inter', 'Segoe UI', 'Roboto', sans-serif")
              .style('font-size', '13px')
              .style('font-weight', '700')
              .style('fill', '#1f2937')
              .style('text-shadow', '1px 1px 2px rgba(255,255,255,0.8)')
              .text(d => {
                  // Format the total value nicely using backend's format_capacity_value logic
                  const value = d.total;
                  // Handle zero explicitly to avoid formatting issues
                  if (value === 0 || value === 0.0) {
                      return "0";
                  } else if (value >= 1000000) {
                      return `${(value/1000000).toFixed(1)}GW`;
                  } else if (value >= 10000) {
                      // For values 10k and above, show 1 decimal if meaningful
                      const formatted = value/1000;
                      if (formatted == Math.floor(formatted)) {
                          return `${Math.floor(formatted)}k`;
                      } else {
                          return `${formatted.toFixed(1)}k`;
                      }
                  } else if (value >= 1000) {
                      // For values 1k-10k, always show 1 decimal place for precision
                      return `${(value/1000).toFixed(1)}k`;
                  } else if (value >= 100) {
                      // For values 100-999, show whole numbers
                      return `${Math.round(value)}`;
                  } else if (value >= 1) {
                      // For values 1-99, show 1 decimal if meaningful
                      if (value == Math.floor(value)) {
                          return `${Math.floor(value)}`;
                      } else {
                          return `${value.toFixed(1)}`;
                      }
                  } else {
                      // For values < 1 but > 0, show 2 decimal places
                      return `${value.toFixed(2)}`;
                  }
              });
          
          // Add individual segment values for larger segments (with smart visibility control)
          const shouldShowSegmentLabels = data.length > 0 ? data[0].show_segment_labels !== false : true; // Default to true if not specified
          const barWidth = xScale.bandwidth();
          const filteredStackedData = shouldShowSegmentLabels
              ? stackedData.filter(d => {
                  // Calculate actual pixel height of the segment
                  const segmentHeight = yScale(d.y0) - yScale(d.y1);
                  // Only show label if segment is tall enough (at least 30 pixels) AND bar is wide enough (at least 40 pixels)
                  return segmentHeight >= 30 && barWidth >= 40;
              })
              : []; // Hide all segment labels when there are too many bars

          g.selectAll('text.segment-value-label')
              .data(filteredStackedData)
              .enter()
              .append('text')
              .attr('class', 'segment-value-label')
              .attr('x', d => xScale(d.category) + xScale.bandwidth() / 2)
              .attr('y', d => yScale((d.y0 + d.y1) / 2)) // Middle of the segment
              .attr('text-anchor', 'middle')
              .attr('dominant-baseline', 'middle')
              .style('font-family', "'Inter', 'Segoe UI', 'Roboto', sans-serif")
              .style('font-size', '10px')
              .style('font-weight', '600')
              .style('fill', '#ffffff')
              .style('text-shadow', '1px 1px 2px rgba(0,0,0,0.7)')
              .style('pointer-events', 'none')
              .text(d => {
                  // Use backend's formatted value if available, otherwise format here
                  if (d.formatted_value) {
                      return d.formatted_value;
                  }
                  // Fallback formatting for individual segments (more precise)
                  const value = d.value;
                  // Handle zero explicitly to avoid formatting issues
                  if (value === 0 || value === 0.0) {
                      return "0";
                  } else if (value >= 1000000) {
                      return `${(value/1000000).toFixed(1)}GW`;
                  } else if (value >= 1000) {
                      return `${(value/1000).toFixed(1)}k`;
                  } else if (value >= 1) {
                      if (value == Math.floor(value)) {
                          return `${Math.floor(value)}`;
                      } else {
                          return `${value.toFixed(1)}`;
                      }
                  } else {
                      return `${value.toFixed(2)}`;
                  }
              })
              .each(function() {
                  // Clip text to fit within bar width
                  const text = d3.select(this);
                  const textWidth = this.getComputedTextLength();
                  if (textWidth > barWidth - 4) {
                      // Hide text if it's too wide for the bar
                      text.style('display', 'none');
                  }
              });
    } else if (plotType === 'box') {
        const boxWidth = Math.max(10, xScale.bandwidth() * 0.6);
        const half = boxWidth / 2;
        const groups = d3.group(data, d => d.series);
        
        groups.forEach((values, key, index) => {
            const d = values[0];
            const cx = xScale(d.category || d.series) + xScale.bandwidth() / 2;
            const color = colorScale(d.series);
            const safe = cssSafe(d.series);
            const groupIndex = Array.from(groups.keys()).indexOf(key);
            
            // Whisker with animation
            const whisker = g.append('line')
                .attr('class', `series-${safe}`)
                .attr('x1', cx)
                .attr('x2', cx)
                .attr('y1', yScale(d.min))
                .attr('y2', yScale(d.min)) // Start collapsed
                .attr('stroke', color)
                .attr('stroke-width', 2)
                .style('opacity', 0);
            
            whisker.transition()
                .delay(groupIndex * 200)
                .duration(600)
                .ease(d3.easeQuadOut)
                .attr('y2', yScale(d.max))
                .style('opacity', 1);
            
            // Box with animation
            const box = g.append('rect')
                .attr('class', `series-${safe}`)
                .attr('x', cx - half)
                .attr('width', boxWidth)
                .attr('y', yScale(d.q2)) // Start as a line at median
                .attr('height', 0) // Start with 0 height
                .attr('fill', color)
                .attr('fill-opacity', 0.3)
                .attr('stroke', color)
                .attr('stroke-width', 2)
                .style('cursor', 'pointer')
                .style('opacity', 0);
            
            box.transition()
                .delay(groupIndex * 200 + 200)
                .duration(400)
                .ease(d3.easeBackOut)
                .attr('y', yScale(d.q3))
                .attr('height', Math.max(1, yScale(d.q1) - yScale(d.q3)))
                .style('opacity', 1);
            
            // Median line with animation
            const median = g.append('line')
                .attr('class', `series-${safe}`)
                .attr('x1', cx)
                .attr('x2', cx) // Start as a point
                .attr('y1', yScale(d.q2))
                .attr('y2', yScale(d.q2))
                .attr('stroke', color)
                .attr('stroke-width', 3)
                .style('opacity', 0);
            
            median.transition()
                .delay(groupIndex * 200 + 400)
                .duration(300)
                .ease(d3.easeElasticOut)
                .attr('x1', cx - half)
                .attr('x2', cx + half)
                .style('opacity', 1);
            
            // Add hover effects and tooltips to box
            box.on('mouseover', function(event, boxData) {
                // Highlight the box
                d3.select(this)
                    .transition()
                    .duration(200)
                    .style('opacity', 0.8)
                    .attr('stroke-width', 3);
                
                // Create custom tooltip data for box plot
                const boxTooltipData = {
                    series: d.series,
                    category: d.category,
                    min: d.min,
                    q1: d.q1,
                    q2: d.q2,
                    q3: d.q3,
                    max: d.max
                };
                
                // Show enhanced tooltip with box plot specific content
                tooltip.transition()
                    .duration(200)
                    .style('opacity', 0.9);
                
                const unit = plotData.unit || '';
                tooltip.html(`
                    <div class="tooltip-header">${d.series}</div>
                    <div class="tooltip-body">
                        <div class="tooltip-row">
                            <span class="tooltip-label">Category:</span>
                            <span class="tooltip-value">${d.category || d.series}</span>
                        </div>
                        <div class="tooltip-row">
                            <span class="tooltip-label">Max:</span>
                            <span class="tooltip-value">${d.max.toLocaleString()} ${unit}</span>
                        </div>
                        <div class="tooltip-row">
                            <span class="tooltip-label">Q3:</span>
                            <span class="tooltip-value">${d.q3.toLocaleString()} ${unit}</span>
                        </div>
                        <div class="tooltip-row">
                            <span class="tooltip-label">Median:</span>
                            <span class="tooltip-value">${d.q2.toLocaleString()} ${unit}</span>
                        </div>
                        <div class="tooltip-row">
                            <span class="tooltip-label">Q1:</span>
                            <span class="tooltip-value">${d.q1.toLocaleString()} ${unit}</span>
                        </div>
                        <div class="tooltip-row">
                            <span class="tooltip-label">Min:</span>
                            <span class="tooltip-value">${d.min.toLocaleString()} ${unit}</span>
                        </div>
                    </div>
                `)
                    .style('left', (event.pageX + 10) + 'px')
                    .style('top', (event.pageY - 28) + 'px');
            })
            .on('mouseout', function(event, boxData) {
                // Reset the box
                d3.select(this)
                    .transition()
                    .duration(200)
                    .style('opacity', 1)
                    .attr('stroke-width', 2);
                
                // Hide tooltip
                tooltip.transition()
                    .duration(500)
                    .style('opacity', 0);
            });
        });
    } else if (plotType === 'pie') {
        // Pie/donut chart using category as slice name and value as ratio (0..1)
        const radius = Math.min(width, height) / 2;
        // Center the pie in the middle of the entire container
        const centerX = rect.width / 2; // Use full container width
        const centerY = margin.top + height / 2;
        const pieG = svg.append('g')
            .attr('transform', `translate(${centerX}, ${centerY})`);
        // Exclude the synthetic 'Total' slice from actual wedges; keep for total text
        const slices = data.filter(d => (d.category || d.series) !== 'Total');
        
        const pie = d3.pie().value(d => d.value).sort(null);
        const arc = d3.arc().innerRadius(radius * 0.45).outerRadius(radius);
        const arcs = pieG.selectAll('path')
            .data(pie(slices))
            .enter().append('path')
            .attr('class', d => `series-${cssSafe(d.data.category || d.data.series)}`)
            .attr('fill', d => colorScale(d.data.category || d.data.series))
            .attr('stroke', '#fff')
            .attr('stroke-width', 2)
            .style('cursor', 'pointer')
            .style('opacity', 0); // Start invisible
        
        // Animate pie slices
        arcs.transition()
            .delay((d, i) => i * 200) // Staggered animation
            .duration(800)
            .ease(d3.easeBackOut)
            .style('opacity', 1)
            .attrTween('d', function(d) {
                const i = d3.interpolate({startAngle: 0, endAngle: 0}, d);
                return function(t) {
                    return arc(i(t));
                };
            });
        
        // Add hover effects and tooltips to pie slices
        arcs.on('mouseover', function(event, d) {
            // Highlight the slice
            d3.select(this)
                .transition()
                .duration(200)
                .style('opacity', 0.8)
                .attr('transform', 'scale(1.05)');
            
            // Show enhanced tooltip
            tooltip.transition()
                .duration(200)
                .style('opacity', 0.9);
            
            tooltip.html(createEnhancedTooltip(d.data, d.data.category || d.data.series, plotData, event))
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 28) + 'px');
        })
        .on('mouseout', function(event, d) {
            // Reset the slice
            d3.select(this)
                .transition()
                .duration(200)
                .style('opacity', 1)
                .attr('transform', 'scale(1)');
            
            // Hide tooltip
            tooltip.transition()
                .duration(500)
                .style('opacity', 0);
        });
        // Smart labeling: only show labels for slices larger than threshold
        const minSliceThreshold = 0.08; // Only label slices >= 8% (to avoid overlap)
        const largeSlices = pie(slices).filter(d => d.data.value >= minSliceThreshold);
        
        // Add percentage labels only for larger slices
        pieG.selectAll('text.percentage')
            .data(largeSlices)
            .enter().append('text')
            .attr('class', 'percentage')
            .attr('transform', d => {
                const centroid = arc.centroid(d);
                return `translate(${centroid[0]}, ${centroid[1] - 8})`;
            })
            .attr('text-anchor', 'middle')
            .style('font-size', '14px')
            .style('font-weight', 'bold')
            .style('fill', 'white')
            .style('text-shadow', '1px 1px 2px rgba(0,0,0,0.7)')
            .text(d => `${(d.data.value * 100).toFixed(1)}%`);

        // Add MW value labels below percentages only for larger slices
        pieG.selectAll('text.mw-value')
            .data(largeSlices)
            .enter().append('text')
            .attr('class', 'mw-value')
            .attr('transform', d => {
                const centroid = arc.centroid(d);
                return `translate(${centroid[0]}, ${centroid[1] + 8})`;
            })
            .attr('text-anchor', 'middle')
            .style('font-size', '12px')
            .style('font-weight', '600')
            .style('fill', 'white')
            .style('text-shadow', '1px 1px 2px rgba(0,0,0,0.7)')
            .text(d => {
                const totalInfo = (plotData.series_info && plotData.series_info[0] && plotData.series_info[0].total_mw) || null;
                const mwRaw = (totalInfo ? d.data.value * totalInfo : d.data.mw);
                const mw = (mwRaw || 0).toLocaleString(undefined, { maximumFractionDigits: 0 });
                return `${mw} MW`;
            });
        // Show total somewhere below the chart if provided
        const totalInfo = (plotData.series_info && plotData.series_info[0] && plotData.series_info[0].total_mw) || (data.find(d => (d.category||d.series)==='Total')?.mw) || null;
        if (totalInfo !== null && !isNaN(totalInfo)) {
            svg.append('text')
                .attr('x', centerX)
                .attr('y', centerY + radius + 24)
                .attr('text-anchor', 'middle')
                .style('font-size', '12px')
                .style('fill', '#374151')
                .text(`Total: ${totalInfo.toLocaleString(undefined, { maximumFractionDigits: 0 })} MW`);
        }
        
        // Add note about small slices if some slices don't have labels
        const unlabeledSlices = pie(slices).filter(d => d.data.value < minSliceThreshold);
        if (unlabeledSlices.length > 0) {
            svg.append('text')
                .attr('x', centerX)
                .attr('y', centerY + radius + (totalInfo ? 40 : 24))
                .attr('text-anchor', 'middle')
                .style('font-size', '10px')
                .style('fill', '#6b7280')
                .style('font-style', 'italic')
                .text(`Small slices (< 8%) shown in legend only`);
        }
    }
    
    // Legend positioning - top for bar/stacked charts, bottom for others
    let legendOffsetY;
    let legendOffsetX;
    
    if ((plotType === 'bar' || plotType === 'stacked') && plotData.series_info && plotData.series_info.length > 1) {
        // Top legend for bar/stacked charts
        legendOffsetY = plotData.title ? 50 : 25; // Below title or at top
        legendOffsetX = 0; // Will be centered after legend width calculation
    } else if (plotType === 'pie') {
        // Center legend for pie charts - will be adjusted after width calculation
        legendOffsetY = margin.top + height + margin.bottom + 20; // after axis label
        legendOffsetX = width / 2; // Start at center, will be adjusted for actual legend width
    } else {
        // Bottom legend for other charts - ensure it's within SVG bounds
        if (plotType === 'line') {
            // For line charts, position legend with better spacing
            legendOffsetY = margin.top + height + margin.bottom + 40; // More space from axis
            legendOffsetX = width / 2; // Center horizontally initially
        } else {
            // For box plots and other charts, add extra spacing from X-axis
            const extraSpacing = plotType === 'box' ? 40 : 20; // More space for box plots
            legendOffsetY = margin.top + height + margin.bottom + extraSpacing;
            legendOffsetX = margin.left;
        }
    }
    
    // Ensure legend doesn't start outside SVG bounds (except for charts that will be centered)
    if (plotType !== 'pie' && plotType !== 'stacked' && plotType !== 'line') {
        legendOffsetX = Math.max(legendOffsetX, 10); // Minimum 10px from left edge
    }
    
    const legend = svg.append('g')
        .attr('class', 'legend')
        .attr('transform', `translate(${legendOffsetX}, ${legendOffsetY})`);

    // For bar/stacked charts, legend should represent series, not categories (years)
    // For pie charts, exclude 'Total' from legend
    // For stacked_bar charts, use stack names from data
    const legendItems = (plotType === 'line' || plotType === 'bar' || plotType === 'stacked')
      ? Array.from(series.keys())
      : plotType === 'stacked_bar'
        ? Array.from(new Set(data.map(d => d.stack)))
      : plotType === 'pie'
        ? categories.filter(cat => cat !== 'Total')
        : categories;
    let xCursor = 0;
    let yCursor = 0;
    const rowHeight = 20;
    // Calculate available width for legend, ensuring it doesn't exceed container bounds
    const availableWidth = rect.width - margin.left - margin.right - 80; // More padding for safety
    const maxLegendWidth = Math.min(Math.max(200, availableWidth), rect.width - 100); // Ensure it never exceeds container
    
    // For very long legends, use a more compact layout
    const isLongLegend = legendItems.length > 15;
    const compactSpacing = isLongLegend ? 15 : 20;
    
    // Debug legend width calculation
    if (legendItems.length > 10) {
        console.log('📏 Legend Debug:', {
            containerWidth: rect.width,
            availableWidth,
            maxLegendWidth,
            legendItemsCount: legendItems.length,
            margin: { left: margin.left, right: margin.right }
        });
    }
    
    // For bar/stacked charts, use horizontal layout with better spacing
    const itemSpacing = (plotType === 'bar' || plotType === 'stacked') ? 30 : compactSpacing;

    // Track visibility state
    const visibility = new Map(legendItems.map(n => [n, true]));
    if (Array.isArray(preselectedVisible) && preselectedVisible.length > 0) {
        legendItems.forEach(n => {
            visibility.set(n, preselectedVisible.includes(n));
        });
    }

    legendItems.forEach((name) => {
        const group = legend.append('g')
            .attr('class', 'legend-item')
            .attr('transform', `translate(${xCursor}, ${yCursor})`);

        let text; // Declare text variable in the outer scope

        // Enhanced styling for bar/stacked charts
        if (plotType === 'bar' || plotType === 'stacked' || plotType === 'stacked_bar') {
            // Rounded rectangle for modern look
            // For stacked_bar, get color from stack_info if available
            let fillColor = colorScale(name);
            if (plotType === 'stacked_bar' && plotData.stack_info) {
                const stackInfo = plotData.stack_info.find(s => s.name === name);
                if (stackInfo) fillColor = stackInfo.color;
            }

            const swatch = group.append('rect')
                .attr('width', 12)
                .attr('height', 12)
                .attr('rx', 2) // Rounded corners
                .attr('ry', 2)
                .attr('fill', fillColor)
                .style('stroke', 'rgba(255,255,255,0.3)')
                .style('stroke-width', '1px');

            text = group.append('text')
                .attr('x', 18)
                .attr('y', 6)
                .attr('dy', '0.35em')
                .style('font-family', "'Inter', 'Segoe UI', 'Roboto', sans-serif")
                .style('font-size', '11px')
                .style('font-weight', '500')
                .style('fill', '#374151')
                .text(name);
        } else {
            // Default styling for other charts
            const swatch = group.append('rect')
                .attr('width', 14)
                .attr('height', 14)
                .attr('fill', colorScale(name));

            text = group.append('text')
                .attr('x', 20)
                .attr('y', 7)
                .attr('dy', '0.35em')
                .style('font-size', '12px')
                .text(name);
        }

        // Add hover highlighting functionality
        group.style('cursor', 'pointer')
            .on('mouseover', function() {
                const safe = cssSafe(name);
                // Highlight current series
                d3.select(this).style('opacity', 1);
                g.selectAll(`.series-${safe}`)
                    .style('opacity', 1)
                    .style('stroke-width', function() {
                        const currentWidth = d3.select(this).style('stroke-width');
                        return plotType === 'line' ? '3px' : currentWidth;
                    });
                
                // Dim other series
                legendItems.forEach(otherName => {
                    if (otherName !== name) {
                        const otherSafe = cssSafe(otherName);
                        g.selectAll(`.series-${otherSafe}`)
                            .style('opacity', 0.3);
                    }
                });
            })
            .on('mouseout', function() {
                // Reset all series to normal opacity and stroke width
                legendItems.forEach(otherName => {
                    const otherSafe = cssSafe(otherName);
                    g.selectAll(`.series-${otherSafe}`)
                        .style('opacity', visibility.get(otherName) ? 1 : 0)
                        .style('stroke-width', function() {
                            return plotType === 'line' ? '2px' : d3.select(this).style('stroke-width');
                        });
                });
            })
            .on('click', () => {
            const isVisible = visibility.get(name);
            visibility.set(name, !isVisible);
            const safe = cssSafe(name);
            if (plotType === 'line') {
              // For line charts, keep simple toggle without re-render
              group.style('display', isVisible ? 'none' : null);
              g.selectAll(`.series-${safe}`).style('display', isVisible ? 'none' : null);
              reflowLegend();
            } else {
              // For categorical charts, rebuild the chart with only visible series to remove gaps
              const base = containerNode.__originalPlotData || plotData;
              const visibleList = legendItems.filter(n => visibility.get(n));
              const filtered = (base.data || []).filter(d => {
                const key = (plotType === 'bar' || plotType === 'stacked') ? d.series
                          : plotType === 'stacked_bar' ? d.stack
                          : (d.category || d.series);
                return visibleList.includes(key);
              });
              // Re-render with filtered data and keep current visibility
              return renderD3Chart(containerId, { ...base, data: filtered }, visibleList);
            }
        });

        // Estimate width for wrapping
        const textWidth = text.node() ? text.node().getComputedTextLength() : name.length * 8; // Fallback if text node not ready
        const itemWidth = (plotType === 'bar' || plotType === 'stacked' || plotType === 'stacked_bar')
            ? 18 + textWidth + itemSpacing  // Smaller swatch + spacing for bar charts
            : 20 + textWidth + 16;           // Default for other charts
        
        // Check if this item would exceed the max width
        if (xCursor + itemWidth > maxLegendWidth) {
            xCursor = 0;
            yCursor += rowHeight;
        }
        
        // Ensure item doesn't exceed container bounds
        const finalX = Math.min(xCursor, maxLegendWidth - itemWidth);
        
        // Position the item
        group.attr('transform', `translate(${finalX}, ${yCursor})`);
        xCursor += itemWidth;
    });

    // After initial layout, compute proper container height
    // Also apply preselected visibility (for categorical re-renders)
    if (Array.isArray(preselectedVisible) && preselectedVisible.length > 0) {
        legend.selectAll('g.legend-item').each(function(_, i){
            const name = legendItems[i];
            const on = visibility.get(name);
            const safe = cssSafe(name);
            d3.select(this).style('display', on ? null : 'none');
            g.selectAll(`.series-${safe}`).style('display', on ? null : 'none');
        });
    }
    reflowLegend();
    
    // Add data brushing functionality only for bar and stacked charts (not line charts due to zoom conflict)
    if (plotType === 'bar' || plotType === 'stacked' || plotType === 'stacked_bar') {
        addDataBrushing(svg, g, width, height, plotType, data, xScale, yScale, containerId);
    }

    // Center the entire legend for pie charts, stacked bar charts, and line charts after layout is complete
    if (plotType === 'pie' || plotType === 'stacked' || plotType === 'stacked_bar' || plotType === 'line') {
        setTimeout(() => {
            try {
                const legendBBox = legend.node().getBBox();
                const containerWidth = rect.width;
                const legendWidth = legendBBox.width;
                const centerOffset = (containerWidth - legendWidth) / 2;
                
                // Update the legend transform to center it
                legend.attr('transform', `translate(${Math.max(20, centerOffset)}, ${legendOffsetY})`);
            } catch (e) {
                console.log('Legend centering failed:', e);
            }
        }, 50); // Small delay to ensure layout is complete
    }

    // Zoom disabled for now (can be re-enabled by uncommenting below)
    const gx = g.append('g').attr('transform', `translate(0,${height})`);
    // const zoom = d3.zoom()
    //   .scaleExtent([0.8, 10])
    //   .translateExtent([[0, 0], [width, height]])
    //   .extent([[0, 0], [width, height]])
    //   .on('zoom', (event) => {
    //     const t = event.transform;
    //     const zx = t.rescaleX(xScale);
    //     gx.call(d3.axisBottom(zx).ticks(d3.timeMonth.every(2)).tickFormat(d3.timeFormat('%Y-%m')));
    //     g.selectAll('path.series-line').attr('d', d => line.x(d2 => zx(d2.date))(d));
    //     g.selectAll('circle.series-dot').attr('cx', d => zx(d.date));
    //   });
    // svg.call(zoom);

    // Helpers to tag elements for toggling & zoom redraw
    function cssSafe(name) {
      return name.replace(/[^a-zA-Z0-9]/g, '_');
    }

    // Reflow legend items horizontally with wrapping and adjust SVG/container height
    function reflowLegend() {
      let x = 0;
      let y = 0;
      // Only consider visible legend items
      const visible = legend.selectAll('g.legend-item').filter(function() {
        const disp = this.style.display;
        return disp !== 'none';
      });
      
      // Note: Pie chart centering is now handled after reflowLegend() completes
      
      // Calculate legend layout with proper bounds checking
      visible.each(function() {
        const node = d3.select(this);
        const bbox = this.getBBox();
        const itemWidth = Math.ceil(bbox.width) + 16; // swatch+text + spacing
        
        // Check if this item would exceed the max width
        if (x + itemWidth > maxLegendWidth) {
          x = 0;
          y += rowHeight;
        }
        
        // Ensure item doesn't exceed container bounds
        const finalX = Math.min(x, maxLegendWidth - itemWidth);
        
        // Position the item (pie chart centering handled separately)
        node.attr('transform', `translate(${finalX}, ${y})`);
        x += itemWidth;
      });
      const legendHeight = y + rowHeight;
      // Add extra space for download/reset buttons at the bottom
      const buttonSpace = 80; // Space for the RESET LEGEND and DOWNLOAD PNG buttons
      
      // Calculate total height with proper components
      
      // Ensure total height includes the actual chart height, not just legend position
      const chartHeight = height + margin.top + margin.bottom; // Actual chart content height
      
      let totalHeight;
      if ((plotType === 'bar' || plotType === 'stacked') && legendOffsetY < 100) {
        // For top legend (bar/stacked charts), height = chart + legend + buttons
        totalHeight = chartHeight + legendHeight + buttonSpace + 10; // Extra padding for legend
      } else {
        // For bottom legend, ensure proper spacing
        totalHeight = Math.max(chartHeight + legendHeight + buttonSpace + 10, legendOffsetY + legendHeight + 10 + buttonSpace);
      }
      
      // Ensure minimum total height for readability
      totalHeight = Math.max(totalHeight, 450);
      
      svg.attr('height', totalHeight);
      containerNode.style.height = `${totalHeight}px`;
      
      // Debug logging for complex legends
      if (legendItems.length > 6) {
        console.log('📏 Legend Layout:', {
          legendItems: legendItems.length,
          legendHeight,
          legendRows: Math.ceil(y / rowHeight) + 1,
          totalHeight,
          chartHeight
        });
      }
      
      // Also ensure the container has proper padding/margin
      containerNode.style.paddingBottom = '0px';
      containerNode.style.marginBottom = '0px';
    }

    // Tagging after draw
    series.forEach((values, seriesName) => {
      const safe = cssSafe(seriesName);
      g.selectAll('path').filter(function() { return this.__data__ === values; })
        .classed('series-line', true)
        .classed(`series-${safe}`, true);
      g.selectAll('circle').filter(function() { return d3.select(this).datum() && d3.select(this).datum().series === seriesName; })
        .classed('series-dot', true)
        .classed(`series-${safe}`, true);
    });
}

// Expose reset and download helpers
window.resetD3Zoom = function(containerId) {
  // Zoom functionality removed
}

window.downloadD3Chart = function(containerId, filename) {
  return new Promise((resolve, reject) => {
    const container = document.getElementById(containerId);
    const svg = container.querySelector('svg');
    if (!svg) {
      resolve(false);
      return;
    }
    
    try {
      const serializer = new XMLSerializer();
      const source = serializer.serializeToString(svg);
      const svgBlob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' });
      const url = URL.createObjectURL(svgBlob);
      const img = new Image();
      
      img.onload = function() {
        try {
          const canvas = document.createElement('canvas');
          canvas.width = svg.viewBox.baseVal.width || svg.getBoundingClientRect().width;
          canvas.height = svg.viewBox.baseVal.height || svg.getBoundingClientRect().height;
          const ctx = canvas.getContext('2d');
          ctx.fillStyle = '#ffffff';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.drawImage(img, 0, 0);
          
          canvas.toBlob((blob) => {
            if (blob) {
              const a = document.createElement('a');
              a.href = URL.createObjectURL(blob);
              a.download = filename || 'chart.png';
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
              URL.revokeObjectURL(a.href);
              URL.revokeObjectURL(url);
              resolve(true);
            } else {
              resolve(false);
            }
          });
        } catch (error) {
          URL.revokeObjectURL(url);
          resolve(false);
        }
      };
      
      img.onerror = function() {
        URL.revokeObjectURL(url);
        resolve(false);
      };
      
      img.src = url;
    } catch (error) {
      resolve(false);
    }
  });
}

// Reset legend: show all legend entries and series
window.resetD3Legend = function(containerId) {
  const container = document.getElementById(containerId);
  const svg = container.querySelector('svg');
  if (!svg) return;
  // If we previously re-rendered with a filtered dataset, rebuild the chart
  // using the original full dataset stored on the container
  if (container.__originalPlotData) {
    try {
      // Deep clone to avoid accidental mutations
      const original = JSON.parse(JSON.stringify(container.__originalPlotData));
      return renderD3Chart(containerId, original);
    } catch (e) {
      return renderD3Chart(containerId, container.__originalPlotData);
    }
  }
  const legendGroup = svg.querySelector('g.legend');
  // Show all legend items
  (legendGroup ? legendGroup.querySelectorAll('g.legend-item') : svg.querySelectorAll('g.legend-item'))
    .forEach(g => { g.style.display = ''; });
  // Show all series of any type (lines, dots, bars, box shapes)
  svg.querySelectorAll('[class*="series-"]').forEach(el => {
    const isLegend = el.closest('g.legend-item');
    if (!isLegend) el.style.display = '';
  });
  // Reflow legend and adjust heights if d3 is available
  // Add notes section if notes are provided
  let notesHeight = 0;
  if (plotData.notes && plotData.notes.length > 0) {
    const notesContainer = container.append('div')
      .attr('class', 'chart-notes')
      .style('margin-top', '10px')
      .style('padding', '8px')
      .style('background-color', '#f8f9fa')
      .style('border-left', '3px solid #6366f1')
      .style('border-radius', '4px')
      .style('font-size', '12px')
      .style('color', '#6b7280');
    
    // Add toggle button for notes
    const notesHeader = notesContainer.append('div')
      .style('display', 'flex')
      .style('align-items', 'center')
      .style('margin-bottom', '4px');
    
    const toggleButton = notesHeader.append('button')
      .attr('class', 'notes-toggle')
      .style('background', 'none')
      .style('border', 'none')
      .style('color', '#6366f1')
      .style('cursor', 'pointer')
      .style('font-size', '12px')
      .style('font-weight', '600')
      .style('margin-right', '8px')
      .text('ℹ️ Chart Notes (click to toggle)');
    
    const notesList = notesContainer.append('div')
      .attr('class', 'notes-content')
      .style('display', 'none'); // Initially hidden
    
    // Add each note as a bullet point
    plotData.notes.forEach(note => {
      notesList.append('div')
        .style('margin-bottom', '2px')
        .html(`• ${note}`);
    });
    
    // Toggle functionality
    let notesVisible = false;
    toggleButton.on('click', () => {
      notesVisible = !notesVisible;
      notesList.style('display', notesVisible ? 'block' : 'none');
      toggleButton.text(notesVisible ? '▼ Chart Notes (click to hide)' : 'ℹ️ Chart Notes (click to show)');
    });
    
    // Calculate notes height for layout
    notesHeight = 40; // Base height for the toggle button
  }

  if (typeof d3 !== 'undefined' && legendGroup) {
    const legend = d3.select(legendGroup);
    const margin = { top: 20, right: 20, bottom: 80, left: 80 };
    const maxLegendWidth = Math.max(200, svg.getBoundingClientRect().width - margin.left - margin.right);
    const rowHeight = 20;
    
    // For pie charts, calculate total row widths first to center them
    const isPieChart = plotData && plotData.plot_type === 'pie';
    let totalRowWidths = [];
    let currentRowWidth = 0;
    let x = 0, y = 0;
    
    if (isPieChart) {
      // First pass: calculate row widths
      legend.selectAll('g.legend-item').filter(function() { return this.style.display !== 'none'; })
        .each(function() {
          const bbox = this.getBBox();
          const itemWidth = Math.ceil(bbox.width) + 16;
          if (x + itemWidth > maxLegendWidth) {
            totalRowWidths.push(currentRowWidth);
            currentRowWidth = itemWidth;
            x = 0;
            y += rowHeight;
          } else {
            currentRowWidth += itemWidth;
          }
          x += itemWidth;
        });
      totalRowWidths.push(currentRowWidth);
      
      // Reset for actual positioning
      x = 0; y = 0;
      let currentRow = 0;
    }
    
    // Position legend items with centering for pie charts
    legend.selectAll('g.legend-item').filter(function() { return this.style.display !== 'none'; })
      .each(function() {
        const node = d3.select(this);
        const bbox = this.getBBox();
        const itemWidth = Math.ceil(bbox.width) + 16;
        if (x + itemWidth > maxLegendWidth) { 
          x = 0; 
          y += rowHeight; 
          if (isPieChart) currentRow++;
        }
        
        let finalX = x;
        if (isPieChart && totalRowWidths[currentRow]) {
          const availableWidth = svg.getBoundingClientRect().width - 40; // Use actual SVG width
          const rowCenterOffset = (availableWidth - totalRowWidths[currentRow]) / 2;
          finalX = x + Math.max(0, rowCenterOffset);
        }
        
        node.attr('transform', `translate(${finalX}, ${y})`);
        x += itemWidth;
      });
      
    const bbox = legend.node().getBBox();
    const m = legendGroup.getAttribute('transform').match(/,\s*([\d\.]+)/);
    const legendOffsetY = m ? parseFloat(m[1]) : 0;
    const totalHeight = legendOffsetY + bbox.height + 30 + notesHeight;
    d3.select(svg).attr('height', totalHeight);
    container.style.height = `${totalHeight + notesHeight}px`;
  }
}
