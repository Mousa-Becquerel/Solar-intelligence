// Autocompletion System with NLP-based fuzzy matching
// Query examples are now loaded from external file

class AutocompleteSystem {
    constructor() {
        this.input = document.getElementById('user-input');
        this.overlay = document.getElementById('autocomplete-overlay');
        this.currentSuggestion = '';
        this.isShowingSuggestion = false;
        
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        this.input.addEventListener('input', (e) => this.handleInput(e));
        this.input.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.input.addEventListener('focus', () => this.showSuggestion());
        this.input.addEventListener('blur', () => setTimeout(() => this.hideSuggestion(), 100));
    }
    
    handleInput(e) {
        const query = e.target.value;
        if (query.length >= 2) {
            const suggestion = this.findBestMatch(query);
            if (suggestion && suggestion.toLowerCase().startsWith(query.toLowerCase())) {
                this.showSuggestionText(query, suggestion);
            } else {
                this.hideSuggestion();
            }
        } else {
            this.hideSuggestion();
        }
    }
    
    handleKeydown(e) {
        if (e.key === 'Tab' && this.isShowingSuggestion) {
            e.preventDefault();
            this.applySuggestion();
        } else if (e.key === 'Escape') {
            this.hideSuggestion();
        }
    }
    
    // Advanced NLP-based fuzzy matching
    findBestMatch(query) {
        if (!query || query.length < 2 || !window.QUERY_EXAMPLES) return null;
        
        const normalizedQuery = this.normalizeText(query);
        const queryWords = this.extractKeywords(normalizedQuery);
        
        let bestMatch = null;
        let bestScore = 0;
        
        for (const example of window.QUERY_EXAMPLES) {
            const score = this.calculateSimilarityScore(normalizedQuery, queryWords, example);
            
            if (score > bestScore && score > 0.3) { // Minimum similarity threshold
                bestMatch = example;
                bestScore = score;
            }
        }
        
        return bestMatch;
    }
    
    normalizeText(text) {
        return text.toLowerCase()
            .replace(/[^\w\s]/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
    }
    
    extractKeywords(text) {
        const stopWords = new Set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'was', 'are', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'shall', 'about', 'what', 'how', 'when', 'where', 'why', 'show', 'me', 'my']);
        
        return text.split(' ')
            .filter(word => word.length > 2 && !stopWords.has(word))
            .slice(0, 10); // Limit to most important keywords
    }
    
    calculateSimilarityScore(query, queryWords, example) {
        const normalizedExample = this.normalizeText(example);
        const exampleWords = this.extractKeywords(normalizedExample);
        
        // 1. Prefix matching (highest weight)
        let prefixScore = 0;
        if (normalizedExample.startsWith(query)) {
            prefixScore = 1.0;
        } else {
            const words = query.split(' ');
            const exWords = normalizedExample.split(' ');
            let matchingPrefixWords = 0;
            for (let i = 0; i < Math.min(words.length, exWords.length); i++) {
                if (exWords[i].startsWith(words[i])) {
                    matchingPrefixWords++;
                } else {
                    break;
                }
            }
            prefixScore = matchingPrefixWords / words.length;
        }
        
        // 2. Keyword overlap (medium weight)
        const commonKeywords = queryWords.filter(word => 
            exampleWords.some(exWord => 
                exWord.includes(word) || word.includes(exWord) || this.levenshteinDistance(word, exWord) <= 1
            )
        );
        const keywordScore = commonKeywords.length / Math.max(queryWords.length, 1);
        
        // 3. Fuzzy string similarity (lower weight)
        const fuzzyScore = this.fuzzyMatch(query, normalizedExample);
        
        // 4. Length penalty (prefer shorter, more relevant matches)
        const lengthPenalty = Math.min(1, 100 / normalizedExample.length);
        
        // Combined weighted score
        return (prefixScore * 0.5 + keywordScore * 0.3 + fuzzyScore * 0.1 + lengthPenalty * 0.1);
    }
    
    levenshteinDistance(a, b) {
        if (a.length === 0) return b.length;
        if (b.length === 0) return a.length;
        
        const matrix = Array(b.length + 1).fill(null).map(() => Array(a.length + 1).fill(null));
        
        for (let i = 0; i <= a.length; i++) matrix[0][i] = i;
        for (let j = 0; j <= b.length; j++) matrix[j][0] = j;
        
        for (let j = 1; j <= b.length; j++) {
            for (let i = 1; i <= a.length; i++) {
                const cost = a[i - 1] === b[j - 1] ? 0 : 1;
                matrix[j][i] = Math.min(
                    matrix[j][i - 1] + 1,
                    matrix[j - 1][i] + 1,
                    matrix[j - 1][i - 1] + cost
                );
            }
        }
        
        return matrix[b.length][a.length];
    }
    
    fuzzyMatch(query, text) {
        const distance = this.levenshteinDistance(query, text.substring(0, query.length * 2));
        const maxLength = Math.max(query.length, text.length);
        return 1 - (distance / maxLength);
    }
    
    showSuggestionText(userInput, suggestion) {
        if (!suggestion || suggestion.toLowerCase() === userInput.toLowerCase()) {
            this.hideSuggestion();
            return;
        }
        
        this.currentSuggestion = suggestion;
        this.isShowingSuggestion = true;
        
        // Create the overlay text with user input + grayed suggestion
        const remainingSuggestion = suggestion.substring(userInput.length);
        this.overlay.innerHTML = `
            <span style="color: transparent;">${userInput}</span><span class="autocomplete-suggestion">${remainingSuggestion}</span>
        `;
        this.overlay.style.display = 'flex';
    }
    
    showSuggestion() {
        if (this.isShowingSuggestion) {
            this.overlay.style.display = 'flex';
        }
    }
    
    hideSuggestion() {
        this.isShowingSuggestion = false;
        this.overlay.style.display = 'none';
        this.overlay.innerHTML = '';
        this.currentSuggestion = '';
    }
    
    applySuggestion() {
        if (this.currentSuggestion) {
            this.input.value = this.currentSuggestion;
            this.hideSuggestion();
            
            // Trigger input event to update any other listeners
            const event = new Event('input', { bubbles: true });
            this.input.dispatchEvent(event);
            
            // Focus at end of input
            this.input.setSelectionRange(this.currentSuggestion.length, this.currentSuggestion.length);
        }
    }
}

// Initialize autocompletion system when DOM is ready
let autocompleteSystem;

let lastTableSort = { col: null, asc: true };
let currentConversationId = null;
let conversations = [];
let newsCardTimeout = null;

// Authentication handling
async function loadCurrentUser() {
    try {
        const response = await fetch('/current-user');
        if (response.ok) {
            const userData = await response.json();
            document.getElementById('user-name').textContent = userData.full_name;
            document.getElementById('user-role').textContent = userData.role;
            
            // Show admin button for admin users
            const adminBtn = document.getElementById('admin-btn');
            if (adminBtn && userData.role === 'admin') {
                adminBtn.style.display = 'flex';
            }
        } else {
            // Redirect to login if not authenticated
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('Error loading user info:', error);
        window.location.href = '/login';
    }
}

function setupLogoutButton() {
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function() {
            window.location.href = '/logout';
        });
    }
}

// Sidebar logic
async function fetchConversations() {
    const res = await fetch('/conversations');
    conversations = await res.json();
    renderConversationList();
}
function renderConversationList() {
    const list = document.getElementById('conversation-list');
    const countElement = document.getElementById('conversations-count');
    
    list.innerHTML = '';
    
    // Update conversations count
    countElement.textContent = conversations.length;
    
    conversations.forEach(conv => {
        const li = document.createElement('li');
        li.className = 'conversation-item' + (conv.id === currentConversationId ? ' active' : '');
        
        // Create title span
        const titleSpan = document.createElement('span');
        titleSpan.className = 'conversation-title';
        titleSpan.textContent = conv.title || `Conversation ${conv.id}`;
        li.appendChild(titleSpan);
        
        // Add delete button
        const delBtn = document.createElement('button');
        delBtn.className = 'delete-chat-btn';
        delBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="5" y="8" width="1.5" height="6" rx="0.75" fill="currentColor"/><rect x="9.25" y="8" width="1.5" height="6" rx="0.75" fill="currentColor"/><rect x="13.5" y="8" width="1.5" height="6" rx="0.75" fill="currentColor"/><path d="M4 6.5C4 5.94772 4.44772 5.5 5 5.5H15C15.5523 5.5 16 5.94772 16 6.5V7.5C16 8.05228 15.5523 8.5 15 8.5H5C4.44772 8.5 4 8.05228 4 7.5V6.5Z" fill="currentColor"/><rect x="7.5" y="2.5" width="5" height="2" rx="1" fill="currentColor"/></svg>';
        delBtn.onclick = async (e) => {
            e.stopPropagation();
            showConfirmModal(async () => {
                await fetch(`/conversations/${conv.id}`, { method: 'DELETE' });
                await fetchConversations();
                // If deleted conversation was active, select next or start new
                if (conv.id === currentConversationId) {
                    if (conversations.length > 1) {
                        const next = conversations.find(c => c.id !== conv.id);
                        if (next) await selectConversation(next.id);
                    } else {
                        await startNewChat();
                    }
                }
            });
        };
        li.appendChild(delBtn);
        li.onclick = () => selectConversation(conv.id);
        list.appendChild(li);
    });
}
async function selectConversation(id) {
    currentConversationId = id;
    renderConversationList();
    
    try {
    const res = await fetch(`/conversations/${id}`);
        if (!res.ok) {
            throw new Error(`Failed to fetch conversation: ${res.status}`);
        }
        
    const messages = await res.json();
    const chatMessages = document.getElementById('chat-messages');
        
    // Remove only message containers, not the welcome message
    const chatWrapper = document.querySelector('.chat-messages-wrapper');
    [...chatWrapper.querySelectorAll('.message-container, .loading-container')].forEach(el => el.remove());

    // Filtering logic (same as backend)
    let filtered = [];
    let i = 0;
    while (i < messages.length) {
        let msg = messages[i];
        let content = msg.content;
            try { 
                content = JSON.parse(msg.content); 
            } catch {
                // If parsing fails, treat as plain string
                content = { type: 'string', value: msg.content };
            }
            
        let nextMsg = messages[i + 1];
        let nextContent = null;
        if (nextMsg) {
                try { 
                    nextContent = JSON.parse(nextMsg.content); 
                } catch {
                    nextContent = { type: 'string', value: nextMsg.content };
            }
                }
                
        // If this is an empty dataframe and next is a string, only keep the string
        if (
            content.type === 'dataframe' &&
            (!content.value || (Array.isArray(content.value) && content.value.length === 0)) &&
            nextContent && nextContent.type === 'string' && nextContent.value
        ) {
            filtered.push({content: nextContent, isUser: false});
            i += 2;
            continue;
        }
            
        // Fallback: filter out error messages if followed by a friendly string
        if (
            content.type === 'string' &&
            typeof content.value === 'string' &&
            content.value.trim().startsWith('Error:') &&
            nextContent && nextContent.type === 'string' &&
            !nextContent.value.trim().startsWith('Error:')
        ) {
            i += 1;
            continue;
        }
            
        // Filter out memory messages and old responses
        if (
            content.type === 'string' &&
                typeof content.value === 'string' &&
            (content.value.includes('memory') || content.value.includes('old response'))
        ) {
            i += 1;
            continue;
        }
            
        filtered.push({content, isUser: msg.sender === 'user'});
        i += 1;
    }
        
    // Replay filtered messages
    filtered.forEach(({content, isUser}, idx) => {
        const nextContent = filtered[idx + 1] ? filtered[idx + 1].content : null;
        addMessage(content, isUser, nextContent);
    });
        
        updateWelcomeMessageVisibility();
        
    } catch (error) {
        console.error('Error loading conversation:', error);
        const chatWrapper = document.querySelector('.chat-messages-wrapper');
        [...chatWrapper.querySelectorAll('.message-container, .loading-container')].forEach(el => el.remove());
        
        addMessage({
            type: 'string',
            value: 'Error loading conversation. Please try refreshing the page or starting a new chat.'
        }, false);
        
    updateWelcomeMessageVisibility();
    }
}
async function startNewChat() {
    // Always create a new conversation for a fresh start
    const newRes = await fetch('/conversations/fresh', { method: 'POST' });
    const data = await newRes.json();
    await fetchConversations();
    await selectConversation(data.id);
    updateWelcomeMessageVisibility();
}
document.getElementById('new-chat-btn').onclick = startNewChat;

// On page load, always start with a fresh conversation
window.onload = async function() {
    await fetchConversations();
    // Always start with a new empty conversation
    await startNewChat();
};

function addMessage(content, isUser = false, nextContent = null, customHeading = null) {
    const chatMessages = document.getElementById('chat-messages');
    const messageContainer = document.createElement('div');
    messageContainer.className = 'message-container';
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;

    if (typeof content === 'object') {
        switch (content.type) {
            case 'dataframe':
                if (!content.value || !Array.isArray(content.value) || content.value.length === 0) {
                    // If nextContent is a string, show it instead
                    if (nextContent && nextContent.type === 'string' && nextContent.value) {
                        messageDiv.innerHTML += marked.parse(nextContent.value);
                    } else {
                        messageDiv.textContent = 'No data available.';
                    }
                } else {
                    // Create collapsible table structure
                    const tableContainer = document.createElement('div');
                    tableContainer.className = 'dataframe';
                    
                    // Create summary info
                    const summary = document.createElement('div');
                    summary.className = 'table-summary';
                    const rowCount = content.value.length;
                    const colCount = Object.keys(content.value[0] || {}).length;
                    summary.innerHTML = `Data table with <span class="table-row-count">${rowCount} rows</span> and <span class="table-row-count">${colCount} columns</span>`;
                    
                    // Create toggle button
                    const toggleBtn = document.createElement('button');
                    toggleBtn.className = 'table-toggle';
                    toggleBtn.innerHTML = `
                        <span>View Table</span>
                        <span class="table-toggle-icon">▼</span>
                    `;
                    
                    // Create collapsible content
                    const tableContent = document.createElement('div');
                    tableContent.className = 'table-content';
                    tableContent.appendChild(renderTable(content.value));
                    
                    // Add toggle functionality
                    toggleBtn.addEventListener('click', function() {
                        const isExpanded = tableContent.classList.contains('expanded');
                        if (isExpanded) {
                            tableContent.classList.remove('expanded');
                            toggleBtn.classList.remove('expanded');
                            toggleBtn.querySelector('span:first-child').textContent = 'View Table';
                        } else {
                            tableContent.classList.add('expanded');
                            toggleBtn.classList.add('expanded');
                            toggleBtn.querySelector('span:first-child').textContent = 'Hide Table';
                        }
                    });
                    
                    // Assemble the structure
                    tableContainer.appendChild(summary);
                    tableContainer.appendChild(toggleBtn);
                    tableContainer.appendChild(tableContent);
                    messageDiv.appendChild(tableContainer);
                }
                break;
            case 'table':
                // Handle table display with raw text response and structured table data
                if (content.value && content.value.trim()) {
                    // Display the raw text response first
                    const textDiv = document.createElement('div');
                    textDiv.className = 'table-text-response';
                    textDiv.innerHTML = marked.parse(content.value);
                    messageDiv.appendChild(textDiv);
                }
                
                if (content.table_data && Array.isArray(content.table_data) && content.table_data.length > 0) {
                    // Create collapsible table structure
                    const tableContainer = document.createElement('div');
                    tableContainer.className = 'dataframe';
                    
                    // Create summary info
                    const summary = document.createElement('div');
                    summary.className = 'table-summary';
                    const rowCount = content.table_data.length;
                    const colCount = Object.keys(content.table_data[0] || {}).length;
                    summary.innerHTML = `Interactive table with <span class="table-row-count">${rowCount} rows</span> and <span class="table-row-count">${colCount} columns</span>`;
                    
                    // Create toggle button
                    const toggleBtn = document.createElement('button');
                    toggleBtn.className = 'table-toggle';
                    toggleBtn.innerHTML = `
                        <span>View Interactive Table</span>
                        <span class="table-toggle-icon">▼</span>
                    `;
                    
                    // Create collapsible content
                    const tableContent = document.createElement('div');
                    tableContent.className = 'table-content';
                    tableContent.appendChild(renderTable(content.table_data));
                    
                    // Add toggle functionality
                    toggleBtn.addEventListener('click', function() {
                        const isExpanded = tableContent.classList.contains('expanded');
                        if (isExpanded) {
                            tableContent.classList.remove('expanded');
                            toggleBtn.classList.remove('expanded');
                            toggleBtn.querySelector('span:first-child').textContent = 'View Interactive Table';
                        } else {
                            tableContent.classList.add('expanded');
                            toggleBtn.classList.add('expanded');
                            toggleBtn.querySelector('span:first-child').textContent = 'Hide Table';
                        }
                    });
                    
                    // Create download button
                    const downloadBtn = document.createElement('button');
                    downloadBtn.className = 'table-download-btn';
                    downloadBtn.innerHTML = `
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
                        </svg>
                        Download CSV
                    `;
                    downloadBtn.onclick = () => downloadTableData(content.full_data || content.table_data, 'table_data.csv');
                    
                    // Assemble the structure
                    tableContainer.appendChild(summary);
                    tableContainer.appendChild(toggleBtn);
                    tableContainer.appendChild(downloadBtn);
                    tableContainer.appendChild(tableContent);
                    messageDiv.appendChild(tableContainer);
                }
                break;
            case 'chart':
                // Handle chart display
if (content.artifact) {
                    const card = document.createElement('div');
                    card.className = 'plot-card';
                    
                    // Add content section
                    const plotContent = document.createElement('div');
                    plotContent.className = 'plot-content';
                    
const img = document.createElement('img');
                    img.src = content.artifact;
                    img.alt = 'Chart visualization';
                    img.className = 'plot-img';
img.style.maxWidth = '100%';
img.style.height = 'auto';
                    
                    // Add error handling for broken chart links
                    img.onerror = function() {
                        // Replace broken image with a message
                        const errorDiv = document.createElement('div');
                        errorDiv.className = 'chart-error-message';
                        errorDiv.style.cssText = `
                            padding: 2rem;
                            text-align: center;
                            background: #f9fafb;
                            border: 2px dashed #d1d5db;
                            border-radius: 8px;
                            color: #6b7280;
                            font-style: italic;
                        `;
                        errorDiv.innerHTML = `
                            <div style="font-size: 2rem; margin-bottom: 0.5rem;">📊</div>
                            <div>Chart visualization is no longer available</div>
                            <div style="font-size: 0.875rem; margin-top: 0.5rem;">
                                This chart was generated in a previous session and is not persisted on this platform.
                            </div>
                        `;
                        
                        // Replace the image with the error message
                        img.parentNode.replaceChild(errorDiv, img);
                    };
                    
                    plotContent.appendChild(img);
                    card.appendChild(plotContent);
                    
                    // Add actions section with download button
                    const actions = document.createElement('div');
                    actions.className = 'plot-actions';
                    
                    const downloadBtn = document.createElement('button');
                    downloadBtn.className = 'download-btn';
                    downloadBtn.innerHTML = `
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
                        </svg>
                        Download Chart
                    `;
                    downloadBtn.onclick = () => {
                        // Handle both base64 data URIs and regular file URLs
                        if (content.artifact.startsWith('data:image/')) {
                            // For base64 data URIs, create download directly
                        const link = document.createElement('a');
                        link.href = content.artifact;
                        link.download = 'pv_analysis_chart.png';
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                        } else {
                            // For regular file URLs, try to download
                            const link = document.createElement('a');
                            link.href = content.artifact;
                            link.download = 'pv_analysis_chart.png';
                            link.target = '_blank'; // Fallback to opening in new tab if download fails
                            document.body.appendChild(link);
                            link.click();
                            document.body.removeChild(link);
                        }
                    };
                    
                    actions.appendChild(downloadBtn);
                    card.appendChild(actions);
                    messageDiv.appendChild(card);
                    
                    // Add text description if available
                    if (content.value && content.value.trim()) {
                        const textDiv = document.createElement('div');
                        textDiv.style.marginTop = '1rem';
                        textDiv.innerHTML = marked.parse(content.value);
                        messageDiv.appendChild(textDiv);
                    }
                } else {
                    messageDiv.textContent = 'Chart could not be displayed.';
                }
                break;
            case 'number':
                const numberDiv = document.createElement('div');
                numberDiv.className = 'number-result';
                numberDiv.textContent = content.value;
                messageDiv.appendChild(numberDiv);
                break;
            case 'string':
            default:
                messageDiv.innerHTML += marked.parse(content.value || content.content || '');
        }
    } else {
        messageDiv.innerHTML += marked.parse(content);
    }

    messageContainer.appendChild(messageDiv);
    const chatWrapper = document.querySelector('.chat-messages-wrapper');
    chatWrapper.appendChild(messageContainer);
    requestAnimationFrame(() => {
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.scrollTop = chatMessages.scrollHeight;
    });
}

// Helper function to render a table from a list of dicts, with sorting
function renderTable(data) {
    const fragment = document.createDocumentFragment();
    if (!data || !Array.isArray(data) || data.length === 0) {
        const empty = document.createElement('div');
        empty.textContent = 'No data available.';
        fragment.appendChild(empty);
        return fragment;
    }
    
    // Format the data before rendering
    const formattedData = formatTableData(data);
    
    const table = document.createElement('table');
    table.className = 'min-w-full text-sm border shadow rounded-lg overflow-hidden';

    // Preferred column order
    const preferredOrder = ['date', 'base_price', 'unit', 'description', 'item', 'region'];
    const keys = Object.keys(formattedData[0]);
    // Build the column order: preferred first, then any others
    const columnOrder = preferredOrder.filter(col => keys.includes(col)).concat(keys.filter(col => !preferredOrder.includes(col)));

    // Table header
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    columnOrder.forEach((key, idx) => {
        const th = document.createElement('th');
        th.className = 'border px-2 py-2 bg-yellow-100 text-yellow-900 font-semibold sticky top-0 z-10';
        th.textContent = formatColumnName(key);
        th.onclick = () => sortTable(table, idx);
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Table body
    const tbody = document.createElement('tbody');
    formattedData.forEach((row, i) => {
        const tr = document.createElement('tr');
        tr.className = i % 2 === 0 ? 'bg-white hover:bg-yellow-50' : 'bg-yellow-50 hover:bg-yellow-100';
        columnOrder.forEach(key => {
            const td = document.createElement('td');
            td.className = 'border px-2 py-2';
            td.textContent = row[key];
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    fragment.appendChild(table);
    return fragment;
}

// Helper function to format table data
function formatTableData(data) {
    console.log('DEBUG: Raw table data:', data);
    console.log('DEBUG: First row keys:', Object.keys(data[0] || {}));
    
    return data.map(row => {
        const formattedRow = {};
        for (const [key, value] of Object.entries(row)) {
            console.log(`DEBUG: Processing ${key}: ${value} (type: ${typeof value})`);
            
            // Only format price columns (dates are now pre-formatted from backend)
            if (key.toLowerCase().includes('price') && typeof value === 'number') {
                // Format price with appropriate decimal places and dollar sign
                formattedRow[key] = '$' + value.toFixed(3);
            } else {
                // Use the value as-is (dates are already formatted as strings from backend)
                formattedRow[key] = value;
            }
        }
        console.log('DEBUG: Formatted row:', formattedRow);
        return formattedRow;
    });
}

// Helper function to format column names
function formatColumnName(columnName) {
    const nameMap = {
        'base_price': 'Price',
        'date': 'Date',
        'unit': 'Unit',
        'description': 'Description',
        'item': 'Item',
        'region': 'Region',
        'frequency': 'Frequency',
        'source': 'Source'
    };
    
    return nameMap[columnName] || columnName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

// Table sorting function
function sortTable(table, colIdx) {
    const tbody = table.tBodies[0];
    const rows = Array.from(tbody.rows);
    const asc = lastTableSort.col === colIdx ? !lastTableSort.asc : true;
    rows.sort((a, b) => {
        const aText = a.cells[colIdx].textContent;
        const bText = b.cells[colIdx].textContent;
        const aNum = parseFloat(aText);
        const bNum = parseFloat(bText);
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return asc ? aNum - bNum : bNum - aNum;
        }
        return asc ? aText.localeCompare(bText) : bText.localeCompare(aText);
    });
    rows.forEach(row => tbody.appendChild(row));
    lastTableSort = { col: colIdx, asc };
}

async function showRandomNewsCard() {
    const newsCard = document.getElementById('news-card');
    const titleEl = newsCard.querySelector('.news-card-title');
    const descEl = newsCard.querySelector('.news-card-desc');
    const linkEl = newsCard.querySelector('.news-card-link');
    const dividerEl = newsCard.querySelector('.news-card-divider');
    try {
        const res = await fetch('/random-news');
        if (!res.ok) throw new Error('No news');
        const news = await res.json();
        console.log('NEWS DEBUG:', news);
        const hasContent = news && (news.title || news.description || news.url);
        if (!hasContent) {
            titleEl.textContent = 'Demo News: Solar Market Update';
            titleEl.style.display = '';
            dividerEl.style.display = '';
            descEl.textContent = 'The global solar market saw record growth this quarter. Stay tuned for more updates!';
            descEl.style.display = '';
            linkEl.href = 'https://www.example.com';
            linkEl.textContent = 'Read more';
            linkEl.style.display = '';
        } else {
            // Set title
            if (news.title) {
                titleEl.textContent = news.title;
                titleEl.style.display = '';
                dividerEl.style.display = '';
            } else {
                titleEl.textContent = '';
                titleEl.style.display = 'none';
                dividerEl.style.display = 'none';
            }
            // Set description
            if (news.description) {
                descEl.textContent = news.description;
                descEl.style.display = '';
            } else {
                descEl.textContent = '';
                descEl.style.display = 'none';
            }
            // Set link
            if (news.url) {
                linkEl.href = news.url;
                linkEl.textContent = 'Read more';
                linkEl.style.display = '';
            } else {
                linkEl.href = '#';
                linkEl.textContent = '';
                linkEl.style.display = 'none';
            }
        }
        newsCard.classList.add('visible');
        newsCard.style.display = 'flex';
        newsCard.style.opacity = '1';
    } catch (e) {
        console.log('NEWS ERROR:', e);
        // Always show fallback demo content on error
        titleEl.textContent = 'Demo News: Solar Market Update';
        titleEl.style.display = '';
        dividerEl.style.display = '';
        descEl.textContent = 'The global solar market saw record growth this quarter. Stay tuned for more updates!';
        descEl.style.display = '';
        linkEl.href = 'https://www.example.com';
        linkEl.textContent = 'Read more';
        linkEl.style.display = '';
        newsCard.classList.add('visible');
        newsCard.style.display = 'flex';
        newsCard.style.opacity = '1';
    }
}
function hideNewsCard() {
    const newsCard = document.getElementById('news-card');
    newsCard.classList.remove('visible');
    newsCard.style.display = 'none';
    newsCard.style.opacity = '0';
}
async function sendMessage() {
    const input = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const message = input.value.trim();
    const agentType = document.getElementById('agent-select').value;
    const errorDiv = document.getElementById('error-message');
    const chatMessages = document.getElementById('chat-messages');
    
    if (!message || !currentConversationId) return;
    
    // Disable input and send button during processing
    input.disabled = true;
    sendBtn.disabled = true;
    input.placeholder = "Processing your request...";
    
    // Add user message to chat with proper content structure
    addMessage({
        type: 'string',
        value: message
    }, true);
    updateWelcomeMessageVisibility();
    input.value = '';
    errorDiv.style.display = 'none';
    
    // Create and show loading spinner
    const loadingContainer = document.createElement('div');
    loadingContainer.className = 'message-container loading-container';
    loadingContainer.id = 'current-loading';
    
    const loadingMessage = document.createElement('div');
    loadingMessage.className = 'message bot-message';
    loadingMessage.style.background = '#fff';
    loadingMessage.style.border = '1px solid #e5e7eb';
    
    const spinner = document.createElement('div');
    spinner.className = 'ellipsis-loader';
    spinner.style.margin = '0.5rem 0';
    spinner.innerHTML = '<div></div><div></div><div></div><div></div>';
    
    loadingMessage.appendChild(spinner);
    loadingContainer.appendChild(loadingMessage);
    const chatWrapper = document.querySelector('.chat-messages-wrapper');
    chatWrapper.appendChild(loadingContainer);
    
    // Scroll to bottom to show spinner
    requestAnimationFrame(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    });
    
    // Show news card
    showRandomNewsCard();
    if (newsCardTimeout) clearTimeout(newsCardTimeout);
    newsCardTimeout = setTimeout(hideNewsCard, 10000);
    
    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message,
                conversation_id: currentConversationId,
                agent_type: agentType
            }),
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('AGENT RESPONSE DEBUG:', data.response);
        
        // Remove loading spinner
        const currentLoading = document.getElementById('current-loading');
        if (currentLoading) {
            currentLoading.remove();
        }
        
        // Handle the response array from the agent
        if (Array.isArray(data.response)) {
            data.response.forEach(responseItem => {
                addMessage(responseItem, false);
            });
        } else if (data.response) {
            // Fallback for single response
            addMessage(data.response, false);
        } else {
            // Handle case where response is empty or malformed
            addMessage({
                type: 'string',
                value: 'I apologize, but I received an empty response. Please try your question again.'
            }, false);
        }
        
        updateWelcomeMessageVisibility();
        // Refresh conversation list to update titles
        await fetchConversations();
        
    } catch (error) {
        console.error('Error in sendMessage:', error);
        
        // Remove loading spinner
        const currentLoading = document.getElementById('current-loading');
        if (currentLoading) {
            currentLoading.remove();
        }
        
        hideNewsCard();
        
        // Show error message in chat
        addMessage({
            type: 'string',
            value: 'Sorry, there was an error processing your request. Please try again.'
        }, false);
        
        errorDiv.textContent = 'Connection error. Please check your internet connection and try again.';
        errorDiv.style.display = 'block';
        
    } finally {
        // Re-enable input and send button
        input.disabled = false;
        sendBtn.disabled = false;
        input.placeholder = "Ask about PV market data...";
        
        // Ensure any remaining loading indicators are removed
        const remainingLoading = document.getElementById('current-loading');
        if (remainingLoading) {
            remainingLoading.remove();
    }

        // Scroll to bottom
        requestAnimationFrame(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
    }
}

// Allow sending message with Enter key (but only if not disabled)
document.getElementById('user-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && !this.disabled) {
        sendMessage();
    }
});

function updateWelcomeMessageVisibility() {
    try {
        const chatWrapper = document.querySelector('.chat-messages-wrapper');
        const welcome = document.getElementById('welcome-message');
        const mainInputWrapper = document.querySelector('.main-input-wrapper');
        const inputWrapper = document.querySelector('.input-wrapper');
        
        // Only count actual message containers (not the welcome div)
        const messageCount = chatWrapper.querySelectorAll('.message-container').length;
        console.log('Message count:', messageCount);
        
        if (welcome) {
            if (messageCount === 0) {
                welcome.style.display = 'flex';
                // Add transparent styling when welcome is visible
                mainInputWrapper?.classList.add('welcome-visible');
                inputWrapper?.classList.add('welcome-visible');
            } else {
                welcome.style.display = 'none';
                // Remove transparent styling when welcome is hidden
                mainInputWrapper?.classList.remove('welcome-visible');
                inputWrapper?.classList.remove('welcome-visible');
            }
        }
    } catch (e) {
        // Fallback: always hide welcome message on error
        const welcome = document.getElementById('welcome-message');
        const mainInputWrapper = document.querySelector('.main-input-wrapper');
        const inputWrapper = document.querySelector('.input-wrapper');
        
        if (welcome) welcome.style.display = 'none';
        mainInputWrapper?.classList.remove('welcome-visible');
        inputWrapper?.classList.remove('welcome-visible');
        console.error('Error in updateWelcomeMessageVisibility:', e);
    }
}

// 1. Add debouncing for search/filter operations
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 2. Optimize table rendering

// 3. Add lazy loading for images
function lazyLoadImages() {
    const images = document.querySelectorAll('img[data-src]');
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
                observer.unobserve(img);
            }
        });
    });
    images.forEach(img => imageObserver.observe(img));
}

// 4. Add error boundary
window.onerror = function(msg, url, lineNo, columnNo, error) {
    console.error('Error: ' + msg + '\nURL: ' + url + '\nLine: ' + lineNo);
    return false;
};

document.getElementById('new-chat-collapsed').onclick = function() {
    document.getElementById('new-chat-btn').click();
};

// Conversations indicator functionality
document.getElementById('conversations-indicator').onclick = function() {
    const sidebar = document.querySelector('.sidebar');
    // Temporarily expand sidebar for 3 seconds
    sidebar.style.width = '270px';
    sidebar.style.overflowX = 'hidden';
    
    // Show conversation list and section title
    const conversationList = document.querySelector('.conversation-list');
    const sectionTitle = document.querySelector('.sidebar-section-title');
    conversationList.style.opacity = '1';
    sectionTitle.style.opacity = '1';
    
    // Auto-collapse after 3 seconds
    setTimeout(() => {
        // Only collapse if not being hovered
        if (!sidebar.matches(':hover')) {
            sidebar.style.width = '80px';
            sidebar.style.overflow = 'hidden';
            conversationList.style.opacity = '0';
            sectionTitle.style.opacity = '0';
        }
    }, 3000);
};

// App title follows sidebar width
const sidebar = document.querySelector('.sidebar');
const appTitle = document.querySelector('.app-title');
sidebar.addEventListener('mouseenter', () => {
    appTitle.style.left = '270px';
});
sidebar.addEventListener('mouseleave', () => {
    appTitle.style.left = '80px';
});

// Modal functionality
const modal = document.getElementById('guide-modal');
const helpBtn = document.getElementById('help-btn');
const closeModal = document.querySelector('.close-modal');
const guideContent = document.querySelector('.guide-content');

// Load guide content
async function loadGuideContent() {
    try {
        const response = await fetch('/guide');
        const content = await response.text();
        guideContent.innerHTML = marked.parse(content);
    } catch (error) {
        console.error('Error loading guide content:', error);
        guideContent.innerHTML = '<p>Error loading guide content. Please try again later.</p>';
    }
}

function openModal() {
    modal.style.display = 'block';
    loadGuideContent();
}

function closeModalFunc() {
    modal.style.display = 'none';
}

helpBtn.onclick = function() {
    openModal();
    document.body.classList.add('modal-open');
};
closeModal.onclick = function() {
    closeModalFunc();
    document.body.classList.remove('modal-open');
};

window.onclick = function(event) {
    if (event.target == modal) {
        closeModalFunc();
        document.body.classList.remove('modal-open');
    }
}

// Sidebar expand/collapse logic for title bar movement
sidebar.addEventListener('mouseenter', () => {
    document.body.classList.add('sidebar-expanded');
});
sidebar.addEventListener('mouseleave', () => {
    document.body.classList.remove('sidebar-expanded');
});

// Function to update welcome message based on selected agent
function updateWelcomeMessage(agentType) {
    const welcomeTitle = document.querySelector('.welcome-title');
    const welcomeSubtitle = document.querySelector('.welcome-subtitle');
    const userInput = document.getElementById('user-input');
    
    // Add subtle fade effect during content change
    welcomeTitle.style.opacity = '0.7';
    welcomeSubtitle.style.opacity = '0.7';
    
    setTimeout(() => {
        if (agentType === 'price') {
            welcomeTitle.textContent = 'PV Module Prices Intelligence';
            welcomeSubtitle.textContent = 'Analyze solar component pricing trends and market dynamics with AI-powered insights';
            userInput.placeholder = 'Ask about solar module prices...';
        } else {
            welcomeTitle.textContent = 'PV Market Intelligence';
            welcomeSubtitle.textContent = 'Unlock comprehensive insights into photovoltaic markets worldwide with AI-powered analysis';
            userInput.placeholder = 'Ask about PV market data...';
        }
        
        // Restore opacity
        welcomeTitle.style.opacity = '1';
        welcomeSubtitle.style.opacity = '1';
    }, 200);
}

// Add agent selection handling
document.getElementById('agent-select').addEventListener('change', function(e) {
    const agentType = e.target.value;
    const selectedOption = e.target.selectedOptions[0];
    
    // Check if the selected option is disabled
    if (selectedOption && selectedOption.disabled) {
        // Show a notification
        alert('This agent is coming soon! Please stay tuned.');
        
        // Reset to the previous valid selection (market as default)
        e.target.value = 'market';
        updateWelcomeMessage('market');
        return;
    }
    
    // Update welcome message
    updateWelcomeMessage(agentType);
    
    // Update the current conversation's agent type
    if (currentConversationId) {
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: '',
                conversation_id: currentConversationId,
                agent_type: agentType
            })
        });
    }
});

// Custom confirmation modal functionality
let confirmCallback = null;
const confirmModal = document.getElementById('confirm-modal');
const confirmDeleteBtn = document.getElementById('confirm-delete');
const confirmCancelBtn = document.getElementById('confirm-cancel');

function showConfirmModal(callback) {
    confirmCallback = callback;
    confirmModal.style.display = 'block';
    document.body.classList.add('modal-open');
}

function hideConfirmModal() {
    confirmModal.style.display = 'none';
    document.body.classList.remove('modal-open');
    confirmCallback = null;
}

confirmDeleteBtn.onclick = async function() {
    if (confirmCallback) {
        await confirmCallback();
    }
    hideConfirmModal();
};

confirmCancelBtn.onclick = function() {
    hideConfirmModal();
};

// Close confirmation modal when clicking outside
confirmModal.onclick = function(event) {
    if (event.target === confirmModal) {
        hideConfirmModal();
    }
};

// Close confirmation modal with Escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape' && confirmModal.style.display === 'block') {
        hideConfirmModal();
    }
});

// Initialize welcome message on page load
document.addEventListener('DOMContentLoaded', function() {
    const agentSelect = document.getElementById('agent-select');
    updateWelcomeMessage(agentSelect.value);
    
    // Initialize authentication
    loadCurrentUser();
    setupLogoutButton();
});

// Initialize autocompletion system
document.addEventListener('DOMContentLoaded', function() {
    autocompleteSystem = new AutocompleteSystem();
});

// Function to download table data as CSV
async function downloadTableData(tableData, filename = 'table_data.csv') {
    try {
        const response = await fetch('/download-table-data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                table_data: tableData,
                filename: filename
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to generate CSV');
        }
        
        // Create download link
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        
    } catch (error) {
        console.error('Error downloading CSV:', error);
        alert('Failed to download CSV file. Please try again.');
    }
}