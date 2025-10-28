// ===== SIDEBAR TOGGLE FUNCTIONALITY =====
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('sidebar-toggle');

    if (sidebar && toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            const isExpanded = sidebar.dataset.expanded === 'true';
            sidebar.dataset.expanded = !isExpanded;

            // Store preference in localStorage
            localStorage.setItem('sidebarExpanded', !isExpanded);

            console.log(`Sidebar ${!isExpanded ? 'expanded' : 'collapsed'}`);
        });

        // Restore sidebar state from localStorage
        const savedState = localStorage.getItem('sidebarExpanded');
        if (savedState === 'true') {
            sidebar.dataset.expanded = 'true';
        }
    }
});

// ===== CONSTANTS =====
const CONFIG = {
    // Autocomplete
    MIN_AUTOCOMPLETE_QUERY_LENGTH: 2,
    MIN_SIMILARITY_THRESHOLD: 0.3,
    AUTOCOMPLETE_BLUR_DELAY: 100,

    // Query reminders
    REMINDER_QUERY_INTERVAL: 4,
    NEWS_CARD_DISPLAY_DELAY: 10000,
    NEWS_CARD_AUTO_HIDE_DELAY: 30000,

    // Suggested queries initialization
    SUGGESTED_QUERIES_INIT_DELAY: 100,

    // Chart dimensions
    CHART_MARGIN: { top: 20, right: 20, bottom: 25, left: 80 },
    CHART_MARGIN_WITH_TITLE: 45,
    CHART_MARGIN_WITH_LEGEND: 110,
    CHART_MARGIN_WITH_LEGEND_NO_TITLE: 90,

    // Animation
    CHART_ANIMATION_DELAY_BASE: 1500,
    CHART_ANIMATION_DELAY_INCREMENT: 50,
    CHART_ANIMATION_DURATION: 300,

    // Timeouts
    SIDEBAR_AUTO_COLLAPSE_DELAY: 300
};

// ===== SECURITY: HTML SANITIZATION =====
/**
 * Safely render markdown content with XSS protection
 * @param {string} markdownText - The markdown text to render
 * @returns {string} Sanitized HTML string safe for innerHTML
 */
function safeRenderMarkdown(markdownText) {
    if (!markdownText) return '';
    const rawHtml = marked.parse(markdownText);
    return DOMPurify.sanitize(rawHtml, {
        ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                       'ul', 'ol', 'li', 'a', 'code', 'pre', 'blockquote', 'table', 'thead',
                       'tbody', 'tr', 'th', 'td', 'hr', 'span', 'div'],
        ALLOWED_ATTR: ['href', 'target', 'rel', 'class', 'id'],
        ALLOW_DATA_ATTR: false
    });
}

// Autocompletion System with NLP-based fuzzy matching
// Query examples are now loaded from external file

class AutocompleteSystem {
    constructor() {
        this.input = document.getElementById('user-input');
        this.overlay = document.getElementById('autocomplete-overlay');
        this.currentSuggestion = '';
        this.isShowingSuggestion = false;

        // Only setup if required elements exist
        if (this.input && this.overlay) {
            this.setupEventListeners();
        }
    }

    setupEventListeners() {
        if (!this.input) return;

        this.input.addEventListener('input', (e) => this.handleInput(e));
        this.input.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.input.addEventListener('focus', () => this.showSuggestion());
        this.input.addEventListener('blur', () => setTimeout(() => this.hideSuggestion(), CONFIG.AUTOCOMPLETE_BLUR_DELAY));
    }

    handleInput(e) {
        const query = e.target.value;
        if (query.length >= CONFIG.MIN_AUTOCOMPLETE_QUERY_LENGTH) {
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


            if (score > bestScore && score > CONFIG.MIN_SIMILARITY_THRESHOLD) {
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
        if (!this.overlay || !suggestion || suggestion.toLowerCase() === userInput.toLowerCase()) {
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
        if (!this.overlay) return;

        if (this.isShowingSuggestion) {
            this.overlay.style.display = 'flex';
        }
    }

    hideSuggestion() {
        if (!this.overlay) return;

        this.isShowingSuggestion = false;
        this.overlay.style.display = 'none';
        this.overlay.innerHTML = '';
        this.currentSuggestion = '';
    }

    applySuggestion() {
        if (!this.input || !this.currentSuggestion) return;

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
  let exportMode = false;
  let selectedMessageIds = new Set();

// Authentication handling
async function loadCurrentUser() {
    try {
        const response = await fetch('/current-user');
        if (response.ok) {
            const userData = await response.json();
            const userNameEl = document.getElementById('user-name');
            const userRoleEl = document.getElementById('user-role');

            if (userNameEl) userNameEl.textContent = userData.full_name;
            if (userRoleEl) userRoleEl.textContent = userData.role;

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

    if (!list) return;

    list.innerHTML = '';

    // Update conversations count
    if (countElement) {
        countElement.textContent = conversations.length;
    }
    
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
        delBtn.setAttribute('aria-label', 'Delete conversation');
        delBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><rect x="5" y="8" width="1.5" height="6" rx="0.75" fill="currentColor"/><rect x="9.25" y="8" width="1.5" height="6" rx="0.75" fill="currentColor"/><rect x="13.5" y="8" width="1.5" height="6" rx="0.75" fill="currentColor"/><path d="M4 6.5C4 5.94772 4.44772 5.5 5 5.5H15C15.5523 5.5 16 5.94772 16 6.5V7.5C16 8.05228 15.5523 8.5 15 8.5H5C4.44772 8.5 4 8.05228 4 7.5V6.5Z" fill="currentColor"/><rect x="7.5" y="2.5" width="5" height="2" rx="1" fill="currentColor"/></svg>';
        delBtn.onclick = async (e) => {
            e.stopPropagation();
            console.log('Delete button clicked for conversation:', conv.id);
            
            // Try to show confirmation modal, fallback to browser confirm
            if (confirmModal && confirmModal.style.display !== 'block') {
                showConfirmModal(async () => {
                    await deleteConversation(conv.id);
                });
            } else {
                // Fallback to browser confirm
                if (confirm('Are you sure you want to delete this conversation? This action cannot be undone.')) {
                    await deleteConversation(conv.id);
                }
            }
        };
        
        // Helper function to delete conversation
        async function deleteConversation(convId) {
            try {
                console.log('Attempting to delete conversation:', convId);
                
                const response = await fetch(`/conversations/${convId}`, { 
                    method: 'DELETE'
                });
                
                console.log('Delete response status:', response.status);
                
                if (!response.ok) {
                    const errorText = await response.text();
                    console.error('Delete failed:', response.status, errorText);
                    alert(`Failed to delete conversation: ${response.status}`);
                    return;
                }
                
                console.log('Conversation deleted successfully');
                await fetchConversations();
                
                // If deleted conversation was active, select next or start new
                if (convId === currentConversationId) {
                    if (conversations.length > 1) {
                        const next = conversations.find(c => c.id !== convId);
                        if (next) await selectConversation(next.id);
                    } else {
                        await startNewChat();
                    }
                }
            } catch (error) {
                console.error('Error deleting conversation:', error);
                alert('Failed to delete conversation. Please try again.');
            }
        
        };
        li.appendChild(delBtn);
        li.onclick = () => selectConversation(conv.id);
        list.appendChild(li);
    });
}
async function selectConversation(id) {
    if (!id) {
        console.error('No conversation ID provided');
        return;
    }
    
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

        // Update suggested queries visibility
        if (typeof updateSuggestedQueriesVisibility === 'function') {
            updateSuggestedQueriesVisibility();
        }

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
    try {
        // Get CSRF token with fallback
        let csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';
        
        // If no CSRF token found, try to refresh the page
        if (!csrfToken) {
            console.warn('CSRF token not found, refreshing page...');
            window.location.reload();
            return;
        }
        
        // Always create a new conversation for a fresh start
        const newRes = await fetch('/conversations/fresh', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        });
        
        if (!newRes.ok) {
            throw new Error(`Failed to create new conversation: ${newRes.status}`);
        }
        
        const data = await newRes.json();
        
        if (!data.id) {
            throw new Error('No conversation ID received from server');
        }
        
        await fetchConversations();
        await selectConversation(data.id);
        updateWelcomeMessageVisibility();

        // Show suggested queries for new chat
        if (typeof showSuggestedQueries === 'function') {
            showSuggestedQueries();
        }
    } catch (error) {
        console.error('Error starting new chat:', error);
        // Show error message to user
        const chatWrapper = document.querySelector('.chat-messages-wrapper');
        [...chatWrapper.querySelectorAll('.message-container, .loading-container')].forEach(el => el.remove());
        
        addMessage({
            type: 'string',
            value: 'Error starting new chat. Please refresh the page and try again.'
        }, false);
    }
}

// Export mode UI and logic
function setupExportMode() {
  const toggleBtn = document.getElementById('export-toggle-btn');
  const downloadBtn = document.getElementById('export-download-btn');
  const pptBtn = document.getElementById('export-ppt-btn');
  if (!toggleBtn || !downloadBtn || !pptBtn) return;
  
  toggleBtn.addEventListener('click', () => {
    exportMode = !exportMode;
    selectedMessageIds.clear();
    document.body.classList.toggle('export-mode', exportMode);
    toggleBtn.classList.toggle('active', exportMode);
    downloadBtn.style.display = exportMode ? 'flex' : 'none';
    pptBtn.style.display = exportMode ? 'flex' : 'none';
    refreshMessageSelectionUI();
  });
  
  downloadBtn.addEventListener('click', showTitleCustomizationModal);
  pptBtn.addEventListener('click', generatePPT);
}

function refreshMessageSelectionUI() {
  const container = document.querySelector('.chat-messages-wrapper');
  if (!container) return;
  container.querySelectorAll('[data-msg-id]').forEach(el => {
    const id = el.getAttribute('data-msg-id');
    el.classList.toggle('selectable', exportMode);
    el.classList.toggle('selected', exportMode && selectedMessageIds.has(id));
    if (exportMode) {
      el.onclick = (e) => {
        // Avoid interfering with links/buttons inside messages
        if (e.target.closest('button, a, svg')) return;
        const isSelected = selectedMessageIds.has(id);
        if (isSelected) selectedMessageIds.delete(id); else selectedMessageIds.add(id);
        el.classList.toggle('selected', !isSelected);
      };
    } else {
      el.onclick = null;
    }
  });
}

async function collectSelectedMessages() {
  const container = document.querySelector('.chat-messages-wrapper');
  const items = [];

  for (const el of container.querySelectorAll('[data-msg-id]')) {
    const id = el.getAttribute('data-msg-id');
    if (!selectedMessageIds.has(id)) continue;
    
    const type = el.getAttribute('data-msg-type') || 'text';
    const sender = el.getAttribute('data-msg-sender') || 'user';
    let payload = null;
    let downloadedFiles = [];
    
    if (type === 'plot') {
      try {
        // Get plot JSON data
        const dataEl = el.querySelector('[data-plot-json]');
        if (dataEl) {
          payload = JSON.parse(dataEl.getAttribute('data-plot-json'));
          
          // Apply custom title if available
          const customTitle = customTitles.get(id);
          if (customTitle) {
            // Update the plot with custom title for download
            const chartContainer = el.querySelector('.interactive-chart-container');
            if (chartContainer) {
              // Create a modified payload with the custom title
              const modifiedPayload = { ...payload, title: customTitle };
              
              // Re-render the chart with the custom title
              renderD3Chart(chartContainer.id, modifiedPayload);
              
              // Wait for re-render to complete
              await new Promise(resolve => setTimeout(resolve, 200));
              
              // Update the payload for JSON export
              payload.title = customTitle;
            }
          }
          
          // Find and download the plot as PNG
          const chartContainer = el.querySelector('.interactive-chart-container');
          if (chartContainer && chartContainer.id) {
            const plotTitle = payload.title || 'chart';
            const fileName = `${plotTitle.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_${id}.png`;
            
            try {
              // Add small delay to avoid browser blocking multiple downloads
              await new Promise(resolve => setTimeout(resolve, 100));
              
              // Download the chart as PNG
              const success = await window.downloadD3Chart(chartContainer.id, fileName);
              if (success) {
                downloadedFiles.push({
                  type: 'png',
                  filename: fileName,
                  description: 'Plot exported as PNG image'
                });
              }
            } catch (error) {
              console.warn('Failed to download plot:', error);
            }
          }
        }
      } catch (error) {
        console.warn('Error processing plot data:', error);
      }
    } else {
      payload = el.innerText || el.textContent || '';
    }
    
    const item = { id, type, sender, payload };
    if (downloadedFiles.length > 0) {
      item.downloaded_files = downloadedFiles;
    }
    items.push(item);
  }
  
  return items;
}

async function downloadSelectedMessages() {
  const downloadBtn = document.getElementById('export-download-btn');
  const originalText = downloadBtn.innerHTML;
  
  try {
    // Show loading state
    downloadBtn.innerHTML = '<span>Processing...</span>';
    downloadBtn.disabled = true;
    
    const items = await collectSelectedMessages();
    if (items.length === 0) {
      alert('Please select some messages to export');
      return;
    }
    
    // Count total downloaded files
    const totalDownloads = items.reduce((sum, item) => 
      sum + (item.downloaded_files ? item.downloaded_files.length : 0), 0);
    
    const conversationData = {
      conversation_id: currentConversationId,
      export_timestamp: new Date().toISOString(),
      total_messages: items.length,
      total_downloaded_files: totalDownloads,
      export_note: totalDownloads > 0 ? 
        `${totalDownloads} plot(s) were automatically downloaded as PNG files` : 
        'No plots were included in this export',
      items: items
    };
    
    const blob = new Blob([JSON.stringify(conversationData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conversation_${currentConversationId || 'export'}_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    
    // Success - no alert needed, files are automatically downloaded
    
  } catch (error) {
    console.error('Export failed:', error);
    alert('Export failed. If your browser blocked multiple downloads, please allow them and try again.');
  } finally {
    // Restore button state
    downloadBtn.innerHTML = originalText;
    downloadBtn.disabled = false;
  }
}

async function collectSelectedMessagesForPPT() {
  const container = document.querySelector('.chat-messages-wrapper');
  const items = [];

  for (const el of container.querySelectorAll('[data-msg-id]')) {
    const id = el.getAttribute('data-msg-id');
    if (!selectedMessageIds.has(id)) continue;
    
    const type = el.getAttribute('data-msg-type') || 'text';
    const sender = el.getAttribute('data-msg-sender') || 'user';
    let payload = null;
    
    if (type === 'plot') {
      try {
        // Get plot JSON data (no PNG download for PPT)
        const dataEl = el.querySelector('[data-plot-json]');
        if (dataEl) {
          payload = JSON.parse(dataEl.getAttribute('data-plot-json'));
          
          // Apply custom title if available
          const customTitle = customTitles.get(id);
          if (customTitle) {
            payload.title = customTitle;
          }
        }
      } catch (error) {
        console.warn(`Failed to parse plot data for message ${id}:`, error);
        continue;
      }
    } else if (type === 'text') {
      payload = { content: el.querySelector('.message-content')?.textContent || '' };
    }
    
    if (payload) {
      items.push({
        id: id,
        type: type,
        sender: sender,
        payload: payload,
        timestamp: el.getAttribute('data-msg-timestamp') || new Date().toISOString()
      });
    }
  }
  
  return items;
}

async function generatePPT() {
  const pptBtn = document.getElementById('export-ppt-btn');
  const originalText = pptBtn.innerHTML;
  
  try {
    // Show loading state
    pptBtn.innerHTML = '<span>Generating PPT...</span>';
    pptBtn.disabled = true;
    
    const items = await collectSelectedMessagesForPPT();
    if (items.length === 0) {
      alert('Please select some messages to generate PPT');
      return;
    }
    
    // Check if there are plot messages
    const plotItems = items.filter(item => item.type === 'plot');
    if (plotItems.length === 0) {
      alert('No plots found in selected messages. Please select messages containing charts/plots.');
      return;
    }
    
    const conversationData = {
      conversation_id: currentConversationId,
      export_timestamp: new Date().toISOString(),
      total_messages: items.length,
      total_downloaded_files: 0,
      export_note: `${plotItems.length} plot(s) selected for PPT generation`,
      items: items
    };
    
    // Call the PPT generation endpoint
    const response = await fetch('/generate-ppt', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('meta[name=csrf-token]')?.getAttribute('content') || ''
      },
      body: JSON.stringify(conversationData)
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to generate PPT');
    }
    
    // Handle the file download
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `presentation_${currentConversationId || 'export'}_${new Date().toISOString().split('T')[0]}.pptx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    
    // Success: silently finish without showing a blocking browser alert
    
  } catch (error) {
    console.error('PPT generation failed:', error);
    alert(`PPT generation failed: ${error.message}`);
  } finally {
    // Restore button state
    pptBtn.innerHTML = originalText;
    pptBtn.disabled = false;
  }
}

document.getElementById('new-chat-btn').onclick = startNewChat;

// On page load, always start with a fresh conversation
window.onload = async function() {
    try {
        await fetchConversations();
        // Always start with a new empty conversation
        await startNewChat();
        setupExportMode();
    } catch (error) {
        console.error('Error during page load:', error);
        // Show error message to user
        const chatWrapper = document.querySelector('.chat-messages-wrapper');
        if (chatWrapper) {
            [...chatWrapper.querySelectorAll('.message-container, .loading-container')].forEach(el => el.remove());
            
            addMessage({
                type: 'string',
                value: 'Error loading the application. Please refresh the page and try again.'
            }, false);
        }
    }
};

function addMessage(content, isUser = false, nextContent = null, customHeading = null) {
    const messageContainer = document.createElement('div');
    messageContainer.className = 'message-container';

    // Tag with IDs/types for export mode
    messageContainer.setAttribute('data-msg-id', `${Date.now()}-${Math.random().toString(36).slice(2,8)}`);
    messageContainer.setAttribute('data-msg-sender', isUser ? 'user' : 'bot');

    const messageDiv = document.createElement('div');
    let messageClass = `message ${isUser ? 'user-message' : 'bot-message'}`;

    // Add agent-specific class for bot messages
    if (!isUser) {
        const agentSelect = document.getElementById('agent-select');
        const agentType = agentSelect ? agentSelect.value : 'market';
        messageClass += ` ${agentType}-agent`;
    }

    messageDiv.className = messageClass;

    if (typeof content === 'object') {
        switch (content.type) {
            case 'dataframe':
                messageContainer.setAttribute('data-msg-type', 'dataframe');
                if (!content.value || !Array.isArray(content.value) || content.value.length === 0) {
                    // If nextContent is a string, show it instead
                    if (nextContent && nextContent.type === 'string' && nextContent.value) {
                        messageDiv.innerHTML += safeRenderMarkdown(nextContent.value);
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
                    toggleBtn.setAttribute('aria-label', 'Toggle table visibility');
                    toggleBtn.setAttribute('aria-expanded', 'false');
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
                    textDiv.innerHTML = safeRenderMarkdown(content.value);
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
                    toggleBtn.setAttribute('aria-label', 'Toggle interactive table visibility');
                    toggleBtn.setAttribute('aria-expanded', 'false');
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

                    // Assemble the structure
                    tableContainer.appendChild(summary);
                    tableContainer.appendChild(toggleBtn);
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
                        textDiv.innerHTML = safeRenderMarkdown(content.value);
                        messageDiv.appendChild(textDiv);
                    }
                } else {
                    messageDiv.textContent = 'Chart could not be displayed.';
                }
                break;
            case 'interactive_chart':
                // Handle D3 interactive chart display
                if (content.plot_data) {
                    // Mark as plot type for export
                    messageContainer.setAttribute('data-msg-type', 'plot');
                    // Remove chat bubble styling for full-width chart display
                    messageDiv.classList.add('no-bubble');
                    messageDiv.style.background = 'transparent';
                    messageDiv.style.boxShadow = 'none';
                    messageDiv.style.border = '0';
                    messageDiv.style.padding = '0';

                    const card = document.createElement('div');
                    card.className = 'plot-card';
                    
                    // Add content section
                    const plotContent = document.createElement('div');
                    plotContent.className = 'plot-content';
                    
            // Create container for D3 chart
                    const chartContainer = document.createElement('div');
                    chartContainer.className = 'interactive-chart-container';
                    chartContainer.id = `chart-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
                    chartContainer.style.cssText = `
                        width: 100%;
                        height: auto;
                        min-height: 350px;
                        background: white;
                        border: 1px solid #e5e7eb;
                        border-radius: 8px;
                        position: relative;
                    `;
                    
            plotContent.appendChild(chartContainer);
                    card.appendChild(plotContent);
                    
                    // Add title if available
                    if (content.value && content.value.trim()) {
                        const titleDiv = document.createElement('div');
                        titleDiv.style.cssText = `
                            padding: 1rem;
                            font-weight: 600;
                            border-bottom: 1px solid #e5e7eb;
                            background: #f9fafb;
                        `;
                        titleDiv.textContent = content.value;
                        card.insertBefore(titleDiv, plotContent);
                    }
                    
            // Add action buttons for interactivity
            const actions = document.createElement('div');
            actions.className = 'plot-actions';
            const resetLegendBtn = document.createElement('button');
            resetLegendBtn.className = 'download-btn';
            resetLegendBtn.textContent = 'Reset legend';
            resetLegendBtn.onclick = () => window.resetD3Legend(chartContainer.id);
            const dlBtn = document.createElement('button');
            dlBtn.className = 'download-btn';
            dlBtn.textContent = 'Download PNG';
            dlBtn.onclick = () => window.downloadD3Chart(chartContainer.id, (content.value || 'chart') + '.png');
            actions.appendChild(resetLegendBtn);
            actions.appendChild(dlBtn);
            card.appendChild(actions);

            messageDiv.appendChild(card);
                    
                    // Embed plot JSON for export
                    try {
                        const meta = document.createElement('div');
                        meta.setAttribute('data-plot-json', JSON.stringify(content.plot_data || {}));
                        meta.style.display = 'none';
                        messageDiv.appendChild(meta);
                    } catch {}

                    // Render the D3 chart once the element is in the DOM
            setTimeout(() => {
                try {
                    console.log('Rendering D3 chart for container:', chartContainer.id);
                    console.log('Plot data:', content.plot_data);
                    
                    // Check if container is in DOM
                    const containerElement = document.getElementById(chartContainer.id);
                    if (!containerElement) {
                        console.error('Chart container not found in DOM:', chartContainer.id);
                        return;
                    }
                    
                    if (!content.plot_data || !content.plot_data.data) {
                        console.error('Invalid plot data:', content.plot_data);
                        containerElement.innerHTML = '<div class="error-message">Plot data is missing or corrupted</div>';
                        return;
                    }
                    
                    renderD3Chart(chartContainer.id, content.plot_data);
                    refreshMessageSelectionUI();
                } catch (error) {
                    console.error('Error rendering D3 chart:', error);
                    const containerElement = document.getElementById(chartContainer.id);
                    if (containerElement) {
                        containerElement.innerHTML = '<div class="error-message">Error rendering chart: ' + error.message + '</div>';
                    }
                }
            }, 100);
                    
                } else {
                    messageDiv.textContent = 'Interactive chart data could not be loaded.';
                }
                break;
            case 'number':
                messageContainer.setAttribute('data-msg-type', 'number');
                const numberDiv = document.createElement('div');
                numberDiv.className = 'number-result';
                numberDiv.textContent = content.value;
                messageDiv.appendChild(numberDiv);
                break;
            case 'upgrade_required':
                messageContainer.setAttribute('data-msg-type', 'upgrade');
                const upgradeDiv = document.createElement('div');
                upgradeDiv.className = 'upgrade-message';

                // Show loading state initially
                upgradeDiv.innerHTML = `
                    <div class="upgrade-icon">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                        </svg>
                    </div>
                    <div class="upgrade-content">
                        <h3>Query Limit Reached</h3>
                        <p>Loading options...</p>
                    </div>
                `;

                // Append immediately so it shows
                messageDiv.appendChild(upgradeDiv);

                // Get CSRF token
                const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';

                // Check survey status to determine which button to show
                fetch('/check-survey-status', {
                    method: 'GET',
                    headers: {
                        'X-CSRFToken': csrfToken
                    }
                })
                .then(response => response.json())
                .then(surveyStatus => {
                    let primaryButton = '';
                    let message = '';

                    if (!surveyStatus.stage1_completed) {
                        // Stage 1 not completed - offer FIRST survey (User Profiling - SIMPLE)
                        message = '<p><strong>Good news!</strong> Answer a quick 2-minute survey to unlock <strong>5 extra queries</strong> and help us tailor insights for your sector.</p>';
                        primaryButton = `<button onclick="showSurveyModal()" class="upgrade-btn primary">Get 5 Extra Queries</button>`;
                    } else if (!surveyStatus.stage2_completed) {
                        // Stage 1 done, Stage 2 not done - offer SECOND survey (Market Activity - ADVANCED)
                        message = '<p><strong>More bonus queries available!</strong> Complete a quick follow-up survey to unlock <strong>5 more queries</strong>.</p>';
                        primaryButton = `<button onclick="showSurveyStage2Modal()" class="upgrade-btn primary">Get 5 More Queries</button>`;
                    } else {
                        // Both surveys completed - only show upgrade option
                        message = '<p style="margin-top: 0.75rem;">Thank you for completing both surveys! To continue accessing solar market intelligence with unlimited queries, upgrade to Premium.</p>';
                        primaryButton = '';
                    }

                    upgradeDiv.innerHTML = `
                        <div class="upgrade-icon">
                            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                            </svg>
                        </div>
                        <div class="upgrade-content">
                            <h3>Query Limit Reached</h3>
                            <p>You've used all <strong>${content.query_limit}</strong> of your ${surveyStatus.stage1_completed && surveyStatus.stage2_completed ? 'available' : 'free monthly'} queries.</p>
                            ${message}
                            <div class="upgrade-actions">
                                ${primaryButton}
                                <a href="/profile" class="upgrade-btn ${primaryButton ? 'secondary' : 'primary'}">
                                    Upgrade to Premium
                                </a>
                            </div>
                        </div>
                    `;
                })
                .catch(error => {
                    console.error('Error checking survey status:', error);
                    // Fallback to default message with survey option
                    upgradeDiv.innerHTML = `
                        <div class="upgrade-icon">
                            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                            </svg>
                        </div>
                        <div class="upgrade-content">
                            <h3>Query Limit Reached</h3>
                            <p>You've used all <strong>${content.query_limit}</strong> of your free monthly queries.</p>
                            <p><strong>Good news!</strong> Answer a quick 2-minute survey to unlock <strong>5 extra queries</strong>.</p>
                            <div class="upgrade-actions">
                                <button onclick="showSurveyModal()" class="upgrade-btn primary">Get 5 Extra Queries</button>
                                <a href="/profile" class="upgrade-btn secondary">
                                    Upgrade Plan
                                </a>
                            </div>
                        </div>
                    `;
                });
                break;
            case 'string':
            default:
                messageContainer.setAttribute('data-msg-type', 'text');
                messageDiv.innerHTML += safeRenderMarkdown(content.value || content.content || '');
        }
    } else {
        messageContainer.setAttribute('data-msg-type', isUser ? 'user' : 'text');
        messageDiv.innerHTML += safeRenderMarkdown(content);
        
        // Enhance links after markdown parsing
        enhanceLinks(messageDiv);
    }

    messageContainer.appendChild(messageDiv);
    const chatWrapper = document.querySelector('.chat-messages-wrapper');
    chatWrapper.appendChild(messageContainer);

    // Hide welcome message when first message is added
    const welcomeMessage = document.getElementById('welcome-message');
    if (welcomeMessage && !welcomeMessage.classList.contains('hidden')) {
        welcomeMessage.classList.add('hidden');
    }

    requestAnimationFrame(() => {
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.scrollTop = chatMessages.scrollHeight;
        refreshMessageSelectionUI();

        // Update suggested queries visibility
        if (typeof updateSuggestedQueriesVisibility === 'function') {
            updateSuggestedQueriesVisibility();
        }
    });
}

// Function to enhance links with better styling and functionality
function enhanceLinks(container) {
    const links = container.querySelectorAll('a');
    
    links.forEach(link => {
        // Add click-here-link class for special styling
        const linkText = link.textContent.toLowerCase();
        if (linkText.includes('click here') || linkText.includes('read more') || linkText.includes('learn more')) {
            link.classList.add('click-here-link');
        }
        
        // Add target="_blank" for external links
        if (link.href && (link.href.startsWith('http://') || link.href.startsWith('https://'))) {
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
        }
        
        // Add title attribute for better accessibility
        if (!link.title) {
            link.title = `Visit ${link.textContent}`;
        }
        
        // Add click tracking for analytics (optional)
        link.addEventListener('click', function(e) {
            console.log(`Link clicked: ${this.href}`);
            // You can add analytics tracking here if needed
        });
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

    // Preferred column order for different data types
    const priceAgentOrder = ['date', 'base_price', 'unit', 'description', 'item', 'region'];
    const marketAgentOrder = ['country', 'year', 'scenario', 'duration', 'connection', 'segment', 'applications', 'type', 'capacity', 'estimation_status', 'install_action'];

    // Columns to exclude from market agent tables
    const marketAgentExcludeColumns = ['source', 'comments'];

    const keys = Object.keys(formattedData[0]);

    // Determine which preferred order to use based on available columns
    let preferredOrder;
    let excludeColumns = [];
    if (keys.includes('country') || keys.includes('capacity')) {
        // Market agent data
        preferredOrder = marketAgentOrder;
        excludeColumns = marketAgentExcludeColumns;
    } else if (keys.includes('date') || keys.includes('base_price')) {
        // Price agent data
        preferredOrder = priceAgentOrder;
    } else {
        // Unknown - use keys as-is (preserves backend order)
        preferredOrder = [];
    }

    // Build the column order: preferred first, then any others, excluding specified columns
    const columnOrder = preferredOrder
        .filter(col => keys.includes(col) && !excludeColumns.includes(col))
        .concat(keys.filter(col => !preferredOrder.includes(col) && !excludeColumns.includes(col)));

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
function showReminderCard() {
    console.log('📢 Showing reminder card');
    const newsCard = document.getElementById('news-card');

    if (!newsCard) {
        console.error('News card element not found');
        return;
    }

    // First hide the card to reset it
    newsCard.classList.remove('visible');
    newsCard.style.display = 'none';

    const badgeEl = newsCard.querySelector('.news-badge');
    const titleEl = newsCard.querySelector('.news-card-title');
    const dividerEl = newsCard.querySelector('.news-card-divider');
    const descEl = newsCard.querySelector('.news-card-desc');
    const linkEl = newsCard.querySelector('.news-card-link');

    console.log('Elements found:', { badgeEl, titleEl, dividerEl, descEl, linkEl });

    // Clear and update badge style and text for reminder
    if (badgeEl) {
        badgeEl.innerHTML = '💡 REMINDER';
        badgeEl.style.background = 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)';
    }

    // Clear and set reminder content - use textContent to ensure proper clearing
    if (titleEl) {
        titleEl.textContent = '';  // Clear first
        titleEl.textContent = 'Expert-Validated Insights';
        titleEl.style.display = 'block';
    }
    if (dividerEl) {
        dividerEl.style.display = 'block';
    }
    if (descEl) {
        descEl.textContent = '';  // Clear first
        descEl.textContent = 'The agent provides answers only from expert-validated data, designed to support you with accurate insights in its specific area of expertise.';
        descEl.style.display = 'block';
    }

    // Hide the link for reminder
    if (linkEl) {
        linkEl.style.display = 'none';
        linkEl.href = '#';
        linkEl.textContent = '';
    }

    // Show the card with a small delay to ensure content is updated
    setTimeout(() => {
        newsCard.classList.add('visible');
        newsCard.style.display = 'flex';
        newsCard.style.opacity = '1';
        console.log('✅ Reminder card displayed');
    }, 50);
}

function hideNewsCard() {
    const newsCard = document.getElementById('news-card');
    newsCard.classList.remove('visible');
    newsCard.style.display = 'none';
    newsCard.style.opacity = '0';

    // Reset badge style for next news card
    const badgeEl = newsCard.querySelector('.news-badge');
    badgeEl.style.background = '';
}
async function sendMessage() {
    const input = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const message = input.value.trim();
    const agentType = document.getElementById('agent-select').value;
    const errorDiv = document.getElementById('error-message');
    const chatMessages = document.getElementById('chat-messages');

    if (!message) return;

    // Check if conversation ID exists
    if (!currentConversationId) {
        console.error('No conversation ID - attempting to create one');
        try {
            await startNewChat();
            if (!currentConversationId) {
                errorDiv.textContent = 'Failed to initialize conversation. Please refresh the page.';
                errorDiv.style.display = 'block';
                return;
            }
        } catch (error) {
            console.error('Failed to create conversation:', error);
            errorDiv.textContent = 'Failed to initialize conversation. Please refresh the page.';
            errorDiv.style.display = 'block';
            return;
        }
    }
    
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

    // Hide suggested queries after user sends message
    if (typeof updateSuggestedQueriesVisibility === 'function') {
        updateSuggestedQueriesVisibility();
    }

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
    
    // Track query count and show news/reminder alternately
    if (!window.queryCount) window.queryCount = 0;
    window.queryCount++;

    console.log(`📊 Query count: ${window.queryCount}`);

    // Show reminder at configured interval
    if (window.queryCount % CONFIG.REMINDER_QUERY_INTERVAL === 0) {
        console.log(`🔔 Showing reminder at query ${window.queryCount}`);
        try {
            showReminderCard();
            if (newsCardTimeout) clearTimeout(newsCardTimeout);
            newsCardTimeout = setTimeout(hideNewsCard, CONFIG.NEWS_CARD_DISPLAY_DELAY);
        } catch (e) {
            console.error('Error showing reminder card:', e);
        }
    }
    // Every other query (but not 4th): show news
    else if (window.queryCount % 2 === 0) {
        console.log('📰 Even query (not 4th) - showing news');
        try {
            showRandomNewsCard();
            if (newsCardTimeout) clearTimeout(newsCardTimeout);
            newsCardTimeout = setTimeout(hideNewsCard, 10000);
        } catch (e) {
            console.error('Error showing news card:', e);
        }
    } else {
        console.log('⏭️ Odd query - no card shown');
    }

    // Removed: feedback modal after 6 queries
    // Now showing user profiling survey after 10 queries (when limit is reached)

    try {
        // Get CSRF token with fallback
        let csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';

        // If no CSRF token found, try to refresh the page
        if (!csrfToken) {
            console.warn('CSRF token not found, refreshing page...');
            window.location.reload();
            return;
        }

        // Handle streaming for digitalization, news, and market agents
        if (agentType === 'digitalization' || agentType === 'news' || agentType === 'market') {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    message,
                    conversation_id: currentConversationId,
                    agent_type: agentType
                }),
            });

            // Check for errors before streaming
            if (!response.ok) {
                // Handle query limit exceeded (429 status)
                if (response.status === 429) {
                    try {
                        const errorData = await response.json();

                        // Remove loading spinner
                        const currentLoading = document.getElementById('current-loading');
                        if (currentLoading) {
                            currentLoading.remove();
                        }

                        hideNewsCard();

                        // Show professional upgrade message
                        const upgradeMessage = {
                            type: 'upgrade_required',
                            plan_type: errorData.plan_type || 'free',
                            queries_used: errorData.queries_used || 10,
                            query_limit: errorData.query_limit || 10
                        };

                        addMessage(upgradeMessage, false);

                        // Re-enable input
                        input.disabled = false;
                        sendBtn.disabled = false;
                        input.placeholder = "Ask about PV market data...";

                        return;
                    } catch (parseError) {
                        console.error('Error parsing 429 response:', parseError);

                        // Fallback: still show upgrade message even if parsing fails
                        const currentLoading = document.getElementById('current-loading');
                        if (currentLoading) {
                            currentLoading.remove();
                        }

                        hideNewsCard();

                        addMessage({
                            type: 'upgrade_required',
                            plan_type: 'free',
                            queries_used: 10,
                            query_limit: 10
                        }, false);

                        input.disabled = false;
                        sendBtn.disabled = false;
                        input.placeholder = "Ask about PV market data...";

                        return;
                    }
                }

                throw new Error(`HTTP error! status: ${response.status}`);
            }

            // Will create message container when first content arrives
            let messageContainer = null;
            let contentDiv = null;
            let fullResponse = '';
            let hasStarted = false;

            // Read SSE stream with timeout protection
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            // Stream timeout configuration - Increased for plot generation
            const STREAM_TIMEOUT = 300000; // 5 minutes max (gpt-5 reasoning can take time)
            const STREAM_IDLE_TIMEOUT = 150000; // 150 seconds idle (gpt-5 plot generation with reasoning)
            let lastActivityTime = Date.now();
            let idleTimeoutId = null;

            // Overall timeout
            const overallTimeout = setTimeout(() => {
                console.error('Stream timeout: No response for 3 minutes');
                reader.cancel().catch(() => {});
                throw new Error('Request timeout - The query took too long to process. Please try a simpler query or narrower time range.');
            }, STREAM_TIMEOUT);

            try {
                while (true) {
                    // Reset idle timeout on each iteration
                    if (idleTimeoutId) clearTimeout(idleTimeoutId);
                    idleTimeoutId = setTimeout(() => {
                        console.error('Stream idle timeout: No data for 90 seconds');
                        reader.cancel().catch(() => {});
                        throw new Error('Connection timeout - No data received for 90 seconds. The query may be too complex.');
                    }, STREAM_IDLE_TIMEOUT);

                    const {value, done} = await reader.read();
                    lastActivityTime = Date.now();

                    if (done) {
                        console.log('Stream completed successfully');
                        break;
                    }

                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\n');

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const eventData = JSON.parse(line.substring(6));

                            if (eventData.type === 'chunk') {
                                // Create message container on first chunk
                                if (!hasStarted) {
                                    const currentLoading = document.getElementById('current-loading');
                                    if (currentLoading) {
                                        currentLoading.remove();
                                    }

                                    // Create message container
                                    messageContainer = document.createElement('div');
                                    messageContainer.className = 'message-container';
                                    messageContainer.setAttribute('data-msg-id', `${Date.now()}-${Math.random().toString(36).slice(2,8)}`);
                                    messageContainer.setAttribute('data-msg-sender', 'bot');
                                    messageContainer.setAttribute('data-msg-type', 'string');

                                    const messageDiv = document.createElement('div');
                                    messageDiv.className = `message bot-message ${agentType}-agent`;

                                    messageContainer.appendChild(messageDiv);

                                    const chatWrapper = document.querySelector('.chat-messages-wrapper');
                                    chatWrapper.appendChild(messageContainer);

                                    contentDiv = messageDiv;
                                    hasStarted = true;
                                }

                                fullResponse += eventData.content;

                                // Render markdown with proper formatting
                                const rendered = marked.parse(fullResponse, {
                                    breaks: true,  // Convert \n to <br>
                                    gfm: true      // GitHub Flavored Markdown
                                });
                                contentDiv.innerHTML = DOMPurify.sanitize(rendered, {
                                    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                                                   'ul', 'ol', 'li', 'a', 'code', 'pre', 'blockquote', 'table', 'thead',
                                                   'tbody', 'tr', 'th', 'td', 'hr', 'span', 'div'],
                                    ALLOWED_ATTR: ['href', 'target', 'rel', 'class', 'id'],
                                    ALLOW_DATA_ATTR: false
                                });

                                // Auto-scroll
                                chatMessages.scrollTop = chatMessages.scrollHeight;
                            } else if (eventData.type === 'plot') {
                                // Handle plot data - render D3 chart
                                // Remove loading spinner and create message container
                                const currentLoading = document.getElementById('current-loading');
                                if (currentLoading) {
                                    currentLoading.remove();
                                }

                                // Create message container for plot
                                messageContainer = document.createElement('div');
                                messageContainer.className = 'message-container';
                                messageContainer.setAttribute('data-msg-id', `${Date.now()}-${Math.random().toString(36).slice(2,8)}`);
                                messageContainer.setAttribute('data-msg-sender', 'bot');
                                messageContainer.setAttribute('data-msg-type', 'plot');

                                const messageDiv = document.createElement('div');
                                messageDiv.className = `message bot-message ${agentType}-agent`;

                                messageContainer.appendChild(messageDiv);

                                const chatWrapper = document.querySelector('.chat-messages-wrapper');
                                chatWrapper.appendChild(messageContainer);

                                contentDiv = messageDiv;
                                hasStarted = true;

                                const plotData = eventData.content;

                                // Create unique container ID for the plot
                                const plotContainerId = `plot-${Date.now()}-${Math.random().toString(36).slice(2,8)}`;

                                // Create plot card structure (matching market agent style)
                                const plotCard = document.createElement('div');
                                plotCard.className = 'plot-card';

                                // Title is rendered inside the SVG chart itself, no need for outer title div

                                const plotContent = document.createElement('div');
                                plotContent.className = 'plot-content';

                                // Create container for D3 chart with larger styling
                                const chartContainer = document.createElement('div');
                                chartContainer.className = 'interactive-chart-container';
                                chartContainer.id = plotContainerId;
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
                                const actions = document.createElement('div');
                                actions.className = 'plot-actions';

                                const resetLegendBtn = document.createElement('button');
                                resetLegendBtn.className = 'download-btn';
                                resetLegendBtn.textContent = 'Reset legend';
                                resetLegendBtn.onclick = () => window.resetD3Legend(plotContainerId);

                                const downloadBtn = document.createElement('button');
                                downloadBtn.className = 'download-btn';
                                downloadBtn.textContent = 'Download PNG';
                                downloadBtn.onclick = () => window.downloadD3Chart(plotContainerId, (plotData.title || 'chart') + '.png');

                                actions.appendChild(resetLegendBtn);
                                actions.appendChild(downloadBtn);
                                plotCard.appendChild(actions);

                                // Clear and add the plot card
                                contentDiv.innerHTML = '';
                                contentDiv.appendChild(plotCard);

                                // Embed plot JSON for export
                                try {
                                    const meta = document.createElement('div');
                                    meta.setAttribute('data-plot-json', JSON.stringify(plotData || {}));
                                    meta.style.display = 'none';
                                    contentDiv.appendChild(meta);
                                } catch (e) {
                                    console.error('Failed to embed plot metadata:', e);
                                }

                                // Force a reflow to ensure DOM is updated
                                void contentDiv.offsetHeight;

                                // Render D3 chart with longer timeout to ensure DOM is ready
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

                                        renderD3Chart(plotContainerId, plotData);
                                    } catch (error) {
                                        console.error('Error rendering D3 chart:', error);
                                        const containerElement = document.getElementById(plotContainerId);
                                        if (containerElement) {
                                            containerElement.innerHTML = '<div class="error-message">Error rendering chart: ' + error.message + '</div>';
                                        }
                                    }
                                }, 200);

                                // Auto-scroll
                                chatMessages.scrollTop = chatMessages.scrollHeight;
                            } else if (eventData.type === 'done') {
                                console.log('Streaming complete');

                                // Only render text if we haven't rendered a plot
                                if (fullResponse && !contentDiv.querySelector('.d3-chart-container')) {
                                    // Final render with all markdown features
                                    const finalRendered = marked.parse(fullResponse, {
                                        breaks: true,
                                        gfm: true,
                                        headerIds: false,
                                        mangle: false
                                    });
                                    contentDiv.innerHTML = DOMPurify.sanitize(finalRendered, {
                                        ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                                                       'ul', 'ol', 'li', 'a', 'code', 'pre', 'blockquote', 'table', 'thead',
                                                       'tbody', 'tr', 'th', 'td', 'hr', 'span', 'div'],
                                        ALLOWED_ATTR: ['href', 'target', 'rel', 'class', 'id'],
                                        ALLOW_DATA_ATTR: false
                                    });
                                }
                            } else if (eventData.type === 'error') {
                                const errorMsg = eventData.message || eventData.content || 'An error occurred';
                                // Use textContent for error messages to prevent XSS
                                contentDiv.innerHTML = '';
                                const errorP = document.createElement('p');
                                errorP.style.color = 'red';
                                errorP.textContent = `Error: ${errorMsg}`;
                                contentDiv.appendChild(errorP);
                            }
                        } catch (e) {
                            console.warn('Failed to parse SSE event:', line, e);
                            // Continue processing other lines
                        }
                    }
                }
            }
        } catch (streamError) {
            console.error('Stream reading error:', streamError);

            // Check if it's a network/protocol error
            if (streamError.name === 'TypeError' && streamError.message.includes('network')) {
                throw new Error('Network error - Connection lost. This may be due to request size or timeout limits. Please try a simpler query.');
            }

            throw streamError;
        } finally {
            // Cleanup timeouts
            clearTimeout(overallTimeout);
            if (idleTimeoutId) clearTimeout(idleTimeoutId);

            // Release reader lock
            try {
                reader.releaseLock();
            } catch (e) {
                console.warn('Reader already released');
            }
        }

        } else {
            // Non-streaming agents (price, om)
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    message,
                    conversation_id: currentConversationId,
                    agent_type: agentType
                }),
            });

            if (!response.ok) {
                // Handle query limit exceeded (429 status)
                if (response.status === 429) {
                    try {
                        const errorData = await response.json();

                        // Remove loading spinner
                        const currentLoading = document.getElementById('current-loading');
                        if (currentLoading) {
                            currentLoading.remove();
                        }

                        hideNewsCard();

                        // Show professional upgrade message
                        const upgradeMessage = {
                            type: 'upgrade_required',
                            plan_type: errorData.plan_type || 'free',
                            queries_used: errorData.queries_used || 10,
                            query_limit: errorData.query_limit || 10
                        };

                        addMessage(upgradeMessage, false);

                        // Re-enable input
                        input.disabled = false;
                        sendBtn.disabled = false;
                        input.placeholder = "Ask about PV market data...";

                        return;
                    } catch (parseError) {
                        console.error('Error parsing 429 response:', parseError);

                        // Fallback: still show upgrade message even if parsing fails
                        const currentLoading = document.getElementById('current-loading');
                        if (currentLoading) {
                            currentLoading.remove();
                        }

                        hideNewsCard();

                        addMessage({
                            type: 'upgrade_required',
                            plan_type: 'free',
                            queries_used: 10,
                            query_limit: 10
                        }, false);

                        input.disabled = false;
                        sendBtn.disabled = false;
                        input.placeholder = "Ask about PV market data...";

                        return;
                    }
                }

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

        // Determine error message based on error type
        let errorMessage = 'Sorry, there was an error processing your request. Please try again.';
        let errorBoxMessage = 'Connection error. Please check your internet connection and try again.';

        // Check if it's a 504 Gateway Timeout error
        if (error.message && error.message.includes('504')) {
            errorMessage = 'Your query is taking longer than expected to process. This usually happens with complex market analysis requests. Please try:\n\n• Breaking down your query into smaller, more specific questions\n• Asking about a narrower time range or fewer countries\n• Simplifying the data analysis requested\n\nIf the issue persists, please contact support.';
            errorBoxMessage = 'Query timeout - The request took too long to process. Please try a simpler query.';
        }

        // Show error message in chat
        addMessage({
            type: 'string',
            value: errorMessage
        }, false);

        errorDiv.textContent = errorBoxMessage;
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
    const welcomeMessage = document.getElementById('welcome-message');
    const chatWrapper = document.querySelector('.chat-messages-wrapper');

    if (!welcomeMessage) return;

    // Show welcome message if no messages in chat, hide otherwise
    const messageCount = chatWrapper ? chatWrapper.querySelectorAll('.message-container').length : 0;
    const hasMessages = messageCount > 0;

    if (hasMessages) {
        welcomeMessage.classList.add('hidden');
    } else {
        welcomeMessage.classList.remove('hidden');
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
    // Welcome message removed - only update input placeholder
    const userInput = document.getElementById('user-input');

    if (userInput) {
        if (agentType === 'price') {
            userInput.placeholder = 'Ask about solar prices...';
        } else if (agentType === 'news') {
            userInput.placeholder = 'Ask about solar industry news...';
        } else if (agentType === 'digitalization') {
            userInput.placeholder = 'Ask about Industry 4.0 in solar...';
        } else if (agentType === 'market_intel') {
            userInput.placeholder = 'Ask Titan to analyze market data...';
        } else {
            userInput.placeholder = 'Ask about PV market data...';
        }
    }
}

// Add agent selection handling (consolidated single listener)
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

    // Update suggested queries for the new agent type
    updateSuggestedQueries(agentType);
    updateSuggestedQueriesVisibility();

    // Update the current conversation's agent type
    if (currentConversationId) {
        // Get CSRF token with fallback
        let csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';

        // If no CSRF token found, try to refresh the page
        if (!csrfToken) {
            console.warn('CSRF token not found during agent switch, refreshing page...');
            window.location.reload();
            return;
        }

        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                message: '',
                conversation_id: currentConversationId,
                agent_type: agentType
            })
        });
    }
});

// ========================================
// Suggested Queries Functionality
// ========================================

/**
 * Initialize suggested queries for the current agent
 */
function initializeSuggestedQueries() {
    const agentSelect = document.getElementById('agent-select');
    const agentType = agentSelect ? agentSelect.value : 'market';
    updateSuggestedQueries(agentType);
}

/**
 * Update suggested queries based on agent type
 */
function updateSuggestedQueries(agentType) {
    const container = document.querySelector('.suggested-queries-wrapper');
    if (!container || !window.SUGGESTED_QUERIES) return;

    // Clear existing queries
    container.innerHTML = '';

    // Get queries for this agent type
    const queries = window.SUGGESTED_QUERIES[agentType] || window.SUGGESTED_QUERIES.market;

    // Create query items
    queries.forEach((query, index) => {
        const queryItem = document.createElement('div');
        queryItem.className = 'suggested-query-item';
        queryItem.setAttribute('data-query', query.text);
        queryItem.style.animationDelay = `${index * 0.05}s`;

        queryItem.innerHTML = `
            <span class="suggested-query-icon">${query.icon}</span>
            <span class="suggested-query-text">${query.text}</span>
        `;

        // Add click handler
        queryItem.addEventListener('click', function() {
            handleSuggestedQueryClick(query.text);
        });

        container.appendChild(queryItem);
    });
}

/**
 * Handle click on a suggested query
 */
function handleSuggestedQueryClick(queryText) {
    const userInput = document.getElementById('user-input');
    if (!userInput) return;

    // Set the query text in the input
    userInput.value = queryText;

    // Focus the input
    userInput.focus();

    // Hide suggested queries
    hideSuggestedQueries();

    // Optionally auto-send the message
    // sendMessage();
}

/**
 * Hide suggested queries
 */
function hideSuggestedQueries() {
    const container = document.getElementById('suggested-queries-container');
    if (container) {
        container.classList.add('hidden');
    }
}

/**
 * Show suggested queries
 */
function showSuggestedQueries() {
    const container = document.getElementById('suggested-queries-container');
    if (container) {
        container.classList.remove('hidden');
    }
}

/**
 * Check if we should show suggested queries
 * (only show when conversation is empty)
 */
function updateSuggestedQueriesVisibility() {
    const chatWrapper = document.querySelector('.chat-messages-wrapper');
    const messageCount = chatWrapper ? chatWrapper.querySelectorAll('.message-container').length : 0;

    if (messageCount === 0) {
        showSuggestedQueries();
    } else {
        hideSuggestedQueries();
    }
}

// Initialize suggested queries on page load
document.addEventListener('DOMContentLoaded', function() {
    // Wait for SUGGESTED_QUERIES to be loaded
    setTimeout(function() {
        initializeSuggestedQueries();
        updateSuggestedQueriesVisibility();
    }, CONFIG.SUGGESTED_QUERIES_INIT_DELAY);
});

// Hide suggested queries when user starts typing
document.getElementById('user-input').addEventListener('input', function() {
    if (this.value.trim().length > 0) {
        hideSuggestedQueries();
    } else {
        updateSuggestedQueriesVisibility();
    }
});

// Custom confirmation modal functionality
let confirmCallback = null;
let confirmModal = null;
let confirmDeleteBtn = null;
let confirmCancelBtn = null;

function initializeConfirmModal() {
    confirmModal = document.getElementById('confirm-modal');
    confirmDeleteBtn = document.getElementById('confirm-delete');
    confirmCancelBtn = document.getElementById('confirm-cancel');
    
    if (!confirmModal || !confirmDeleteBtn || !confirmCancelBtn) {
        console.error('Confirmation modal elements not found');
        return false;
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
    
    console.log('Confirmation modal initialized successfully');
    return true;
}

function showConfirmModal(callback) {
    if (!confirmModal) {
        console.error('Confirmation modal not initialized');
        alert('Error: Confirmation modal not available');
        return;
    }
    
    confirmCallback = callback;
    confirmModal.style.display = 'block';
    document.body.classList.add('modal-open');
    console.log('Confirmation modal shown');
}

function hideConfirmModal() {
    if (confirmModal) {
        confirmModal.style.display = 'none';
        document.body.classList.remove('modal-open');
        confirmCallback = null;
        console.log('Confirmation modal hidden');
    }
}

// Title customization modal functionality
let titleModal = null;
let titleConfirmBtn = null;
let titleCancelBtn = null;
let customTitles = new Map();

function initializeTitleModal() {
    titleModal = document.getElementById('title-customization-modal');
    titleConfirmBtn = document.getElementById('title-confirm');
    titleCancelBtn = document.getElementById('title-cancel');
    
    if (!titleModal || !titleConfirmBtn || !titleCancelBtn) {
        console.error('Title customization modal elements not found');
        return false;
    }
    
    titleConfirmBtn.onclick = function() {
        // Collect all custom titles
        const titleInputs = titleModal.querySelectorAll('.title-item-input');
        titleInputs.forEach(input => {
            const plotId = input.dataset.plotId;
            const title = input.value.trim();
            if (title) {
                customTitles.set(plotId, title);
            } else {
                customTitles.delete(plotId);
            }
        });
        
        hideTitleModal();
        downloadSelectedMessages();
    };

    titleCancelBtn.onclick = function() {
        hideTitleModal();
    };

    // Close modal when clicking outside (but not on inputs)
    titleModal.onclick = function(event) {
        if (event.target === titleModal) {
            hideTitleModal();
        }
    };
    
    // Prevent modal from closing when clicking on modal content
    titleModal.addEventListener('click', function(event) {
        if (event.target.closest('.confirm-modal-content')) {
            event.stopPropagation();
        }
    });
    
    return true;
}

function showTitleCustomizationModal() {
    console.log('🎯 showTitleCustomizationModal called');
    console.log('Selected message IDs:', Array.from(selectedMessageIds));
    
    if (!titleModal && !initializeTitleModal()) {
        console.log('❌ Failed to initialize title modal');
        // Fallback to direct export if modal fails
        downloadSelectedMessages();
        return;
    }
    
    // Collect selected plot messages
    const container = document.querySelector('.chat-messages-wrapper');
    const selectedPlots = [];

    for (const el of container.querySelectorAll('[data-msg-id]')) {
        const id = el.getAttribute('data-msg-id');
        if (!selectedMessageIds.has(id)) continue;
        
        const msgType = el.getAttribute('data-msg-type');
        if (msgType === 'plot') {
            const plotDataAttr = el.getAttribute('data-plot-json');
            if (plotDataAttr) {
                try {
                    const plotData = JSON.parse(plotDataAttr);
                    selectedPlots.push({
                        id: id,
                        title: plotData.title || 'Untitled Plot',
                        plotType: plotData.plot_type || 'chart'
                    });
                } catch (error) {
                    console.warn('Error parsing plot data:', error);
                }
            }
        }
    }
    
    console.log('📊 Found plots:', selectedPlots);
    
    if (selectedPlots.length === 0) {
        console.log('⚠️ No plots selected, proceeding with direct export');
        // No plots selected, proceed with direct export
        downloadSelectedMessages();
        return;
    }
    
    // Populate the modal with plot title inputs
    const titleList = document.getElementById('title-customization-list');
    titleList.innerHTML = '';
    
    selectedPlots.forEach(plot => {
        const item = document.createElement('div');
        item.className = 'title-item';
        
        // Create label
        const label = document.createElement('div');
        label.className = 'title-item-label';
        label.textContent = `${plot.plotType.charAt(0).toUpperCase() + plot.plotType.slice(1)} Chart`;
        
        // Create input using DOM (not innerHTML)
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'title-item-input';
        input.setAttribute('data-plot-id', plot.id);
        input.value = customTitles.get(plot.id) || plot.title;
        input.placeholder = 'Enter custom title (optional)';
        input.spellcheck = false;
        input.autocomplete = 'off';
        input.readOnly = false;
        input.disabled = false;
        
        // Add immediate event listeners
        input.addEventListener('click', function(e) {
            e.stopPropagation();
            console.log('Input clicked!');
            this.focus();
        });
        
        input.addEventListener('focus', function() {
            console.log('Input focused!');
            this.style.backgroundColor = '#e0f2fe';
        });
        
        input.addEventListener('blur', function() {
            this.style.backgroundColor = 'white';
        });
        
        input.addEventListener('input', function() {
            console.log('Input changed to:', this.value);
        });
        
        // Create preview
        const preview = document.createElement('div');
        preview.className = 'title-item-preview';
        preview.textContent = `Original: ${plot.title}`;
        
        // Assemble the item
        item.appendChild(label);
        item.appendChild(input);
        item.appendChild(preview);
        
        titleList.appendChild(item);
    });
    
    // Show modal
    console.log('📝 Showing title customization modal');
    titleModal.style.display = 'block';
    document.body.classList.add('modal-open');
    
    // Focus on first input after modal is shown and enable all inputs
    setTimeout(() => {
        const allInputs = titleModal.querySelectorAll('.title-item-input');
        allInputs.forEach((input, index) => {
            // Ensure the input is enabled and interactive
            input.removeAttribute('readonly');
            input.removeAttribute('disabled');
            input.style.pointerEvents = 'auto';
            input.style.userSelect = 'text';
            
            // Add explicit click handler
            input.onclick = function(e) {
                e.stopPropagation();
                this.focus();
            };
            
            // Add focus handler for debugging
            input.onfocus = function() {
                console.log(`Title input ${index + 1} focused`);
            };
        });
        
        const firstInput = allInputs[0];
        if (firstInput) {
            firstInput.focus();
            firstInput.select();
            console.log('Focused and selected first title input');
        }
    }, 100);
}

function hideTitleModal() {
    if (titleModal) {
        titleModal.style.display = 'none';
        document.body.classList.remove('modal-open');
    }
}

// Initialize welcome message on page load
document.addEventListener('DOMContentLoaded', function() {
    const agentSelect = document.getElementById('agent-select');
    updateWelcomeMessage(agentSelect.value);
    
    // Initialize authentication
    loadCurrentUser();
    setupLogoutButton();
    
    // Initialize confirmation modal
    if (!initializeConfirmModal()) {
        console.error('Failed to initialize confirmation modal');
    }
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

// Function to make title editable inline
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

// Agent Selection Logic
document.addEventListener('DOMContentLoaded', function() {
    // Check if we have a selected agent from the agents page
    const selectedAgent = sessionStorage.getItem('selectedAgent');
    if (selectedAgent) {
        // Set the agent selector to the selected agent
        const agentSelect = document.getElementById('agent-select');
        if (agentSelect) {
            agentSelect.value = selectedAgent;
        }
        // Clear the selection from session storage
        sessionStorage.removeItem('selectedAgent');
    }
});

// User Profiling Survey Modal Functions - Multi-Step
let currentSurveyStep = 1;
const totalSurveySteps = 5;

function showSurveyModal() {
    const modal = document.getElementById('survey-modal');
    modal.style.display = 'flex';

    // Reset form and step
    document.getElementById('user-survey-form').reset();
    document.querySelector('input[name="role_other"]').style.display = 'none';
    currentSurveyStep = 1;
    showSurveyStep(1);
    updateSurveyProgress();
}

function closeSurveyModal() {
    const modal = document.getElementById('survey-modal');
    modal.style.display = 'none';
    currentSurveyStep = 1;
}

function showSurveyStep(stepNumber) {
    // Hide all steps
    document.querySelectorAll('.survey-step').forEach(step => {
        step.style.display = 'none';
    });

    // Show current step
    const currentStep = document.querySelector(`.survey-step[data-step="${stepNumber}"]`);
    if (currentStep) {
        currentStep.style.display = 'block';
    }

    // Update button visibility
    const prevBtn = document.getElementById('survey-prev-btn');
    const nextBtn = document.getElementById('survey-next-btn');
    const submitBtn = document.getElementById('survey-submit-btn');

    prevBtn.style.display = stepNumber === 1 ? 'none' : 'block';
    nextBtn.style.display = stepNumber === totalSurveySteps ? 'none' : 'block';
    submitBtn.style.display = stepNumber === totalSurveySteps ? 'block' : 'none';
}

// Helper function to show error in survey modal
function showSurveyError(message, surveyId = 'survey-error') {
    const errorDiv = document.getElementById(surveyId);
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.classList.add('show');

        // Auto-hide after 5 seconds
        setTimeout(() => {
            errorDiv.classList.remove('show');
        }, 5000);

        // Scroll to top of form to show error
        errorDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function validateCurrentStep() {
    const currentStep = document.querySelector(`.survey-step[data-step="${currentSurveyStep}"]`);

    if (currentSurveyStep === 1) {
        // Validate role selection
        const role = document.querySelector('select[name="role"]').value;
        if (!role) {
            showSurveyError('Please select your role');
            return false;
        }
        if (role === 'other') {
            const roleOther = document.querySelector('input[name="role_other"]').value.trim();
            if (!roleOther) {
                showSurveyError('Please specify your role');
                return false;
            }
        }
    } else if (currentSurveyStep === 2) {
        // Validate at least one region
        const regions = document.querySelectorAll('input[name="region"]:checked');
        if (regions.length === 0) {
            showSurveyError('Please select at least one region');
            return false;
        }
    } else if (currentSurveyStep === 3) {
        // Validate familiarity level
        const familiarity = document.querySelector('select[name="familiarity"]').value;
        if (!familiarity) {
            showSurveyError('Please select your familiarity level');
            return false;
        }
    } else if (currentSurveyStep === 4) {
        // Validate at least one insight type
        const insights = document.querySelectorAll('input[name="insights"]:checked');
        if (insights.length === 0) {
            showSurveyError('Please select at least one type of insight');
            return false;
        }
    }

    return true;
}

function nextSurveyStep() {
    if (!validateCurrentStep()) {
        return;
    }

    if (currentSurveyStep < totalSurveySteps) {
        currentSurveyStep++;
        showSurveyStep(currentSurveyStep);
        updateSurveyProgress();
    }
}

function prevSurveyStep() {
    if (currentSurveyStep > 1) {
        currentSurveyStep--;
        showSurveyStep(currentSurveyStep);
        updateSurveyProgress();
    }
}

function updateSurveyProgress() {
    const progressFill = document.getElementById('survey-progress-fill');
    const currentStepSpan = document.getElementById('survey-current-step');

    const progressPercent = (currentSurveyStep / totalSurveySteps) * 100;
    progressFill.style.width = `${progressPercent}%`;
    currentStepSpan.textContent = currentSurveyStep;
}

async function submitSurvey(event) {
    event.preventDefault();

    const form = document.getElementById('user-survey-form');
    const formData = new FormData(form);

    // Validate at least one region is selected
    const regions = formData.getAll('region');
    if (regions.length === 0) {
        showSurveyError('Please select at least one region of interest');
        return;
    }

    // Validate at least one insight type is selected
    const insights = formData.getAll('insights');
    if (insights.length === 0) {
        showSurveyError('Please select at least one type of insight');
        return;
    }

    // Prepare data
    const surveyData = {
        role: formData.get('role'),
        role_other: formData.get('role') === 'other' ? formData.get('role_other') : null,
        regions: regions,
        familiarity: formData.get('familiarity'),
        insights: insights,
        tailored: formData.get('tailored')
    };

    try {
        // Get CSRF token
        const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';

        const response = await fetch('/submit-user-survey', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(surveyData)
        });

        const data = await response.json();

        if (response.ok && data.success) {
            closeSurveyModal();

            // Show success message in chat
            addMessage({
                type: 'string',
                value: `🎉 **Thank you for completing the survey!**\n\nYou've unlocked **5 more queries**. You now have ${data.new_query_count} queries available.\n\nReloading to activate your bonus queries...`
            }, false);

            // Reload page after 2 seconds to refresh session with new query limit
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else {
            showSurveyError(data.message || 'Failed to submit survey. Please try again.');
        }
    } catch (error) {
        console.error('Error submitting survey:', error);
        showSurveyError('Failed to submit survey. Please try again.');
    }
}

// Event listeners for survey modal
document.addEventListener('DOMContentLoaded', function() {
    // Handle role "Other" selection
    const roleSelect = document.querySelector('select[name="role"]');
    const roleOtherInput = document.querySelector('input[name="role_other"]');

    roleSelect?.addEventListener('change', function() {
        if (this.value === 'other') {
            roleOtherInput.style.display = 'block';
            roleOtherInput.required = true;
        } else {
            roleOtherInput.style.display = 'none';
            roleOtherInput.required = false;
        }
    });

    // Form submission
    document.getElementById('user-survey-form')?.addEventListener('submit', submitSurvey);

    // Close on outside click
    document.getElementById('survey-modal')?.addEventListener('click', function(e) {
        if (e.target === this) {
            closeSurveyModal();
        }
    });

    // ============================================
    // STAGE 2 SURVEY EVENT LISTENERS
    // ============================================

    // Handle work_focus "Other" selection
    const workFocusSelect = document.querySelector('select[name="work_focus"]');
    const workFocusOtherInput = document.querySelector('input[name="work_focus_other"]');

    workFocusSelect?.addEventListener('change', function() {
        if (this.value === 'other') {
            workFocusOtherInput.style.display = 'block';
            workFocusOtherInput.required = true;
        } else {
            workFocusOtherInput.style.display = 'none';
            workFocusOtherInput.required = false;
        }
    });

    // Handle technologies "Other" selection
    const techOtherCheckbox = document.querySelector('input[name="technology"][value="other"]');
    const techOtherInput = document.querySelector('input[name="technologies_other"]');

    techOtherCheckbox?.addEventListener('change', function() {
        if (this.checked) {
            techOtherInput.style.display = 'block';
        } else {
            techOtherInput.style.display = 'none';
            techOtherInput.value = '';
        }
    });

    // Challenge counter for max 3 selection
    const challengeCheckboxes = document.querySelectorAll('input[name="challenge"]');
    const challengeCounter = document.getElementById('challenge-counter');

    challengeCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const checkedCount = document.querySelectorAll('input[name="challenge"]:checked').length;

            // Update counter
            challengeCounter.textContent = `Select up to 3 challenges (${checkedCount} selected)`;

            // Disable unchecked checkboxes if 3 are selected
            if (checkedCount >= 3) {
                challengeCheckboxes.forEach(cb => {
                    if (!cb.checked) {
                        cb.disabled = true;
                        cb.parentElement.style.opacity = '0.5';
                    }
                });
            } else {
                challengeCheckboxes.forEach(cb => {
                    cb.disabled = false;
                    cb.parentElement.style.opacity = '1';
                });
            }
        });
    });

    // Form submission for Stage 2
    document.getElementById('user-survey-stage2-form')?.addEventListener('submit', submitSurveyStage2);

    // Close on outside click for Stage 2
    document.getElementById('survey-stage2-modal')?.addEventListener('click', function(e) {
        if (e.target === this) {
            closeSurveyStage2Modal();
        }
    });
});

// ============================================
// STAGE 2 SURVEY FUNCTIONS
// ============================================
let currentSurveyStage2Step = 1;
const totalSurveyStage2Steps = 5;

function showSurveyStage2Modal() {
    const modal = document.getElementById('survey-stage2-modal');
    modal.style.display = 'flex';

    // Reset form and step
    document.getElementById('user-survey-stage2-form').reset();
    document.querySelector('input[name="work_focus_other"]').style.display = 'none';
    document.querySelector('input[name="technologies_other"]').style.display = 'none';

    // Reset challenge counter
    const challengeCounter = document.getElementById('challenge-counter');
    challengeCounter.textContent = 'Select up to 3 challenges (0 selected)';

    // Re-enable all challenge checkboxes
    document.querySelectorAll('input[name="challenge"]').forEach(cb => {
        cb.disabled = false;
        cb.parentElement.style.opacity = '1';
    });

    currentSurveyStage2Step = 1;
    showSurveyStage2Step(1);
    updateSurveyStage2Progress();
}

function closeSurveyStage2Modal() {
    const modal = document.getElementById('survey-stage2-modal');
    modal.style.display = 'none';
    currentSurveyStage2Step = 1;
}

function showSurveyStage2Step(stepNumber) {
    // Hide all steps
    document.querySelectorAll('#user-survey-stage2-form .survey-step').forEach(step => {
        step.style.display = 'none';
    });

    // Show current step
    const currentStep = document.querySelector(`#user-survey-stage2-form .survey-step[data-step="${stepNumber}"]`);
    if (currentStep) {
        currentStep.style.display = 'block';
    }

    // Update button visibility
    const prevBtn = document.getElementById('survey-stage2-prev-btn');
    const nextBtn = document.getElementById('survey-stage2-next-btn');
    const submitBtn = document.getElementById('survey-stage2-submit-btn');

    prevBtn.style.display = stepNumber === 1 ? 'none' : 'block';
    nextBtn.style.display = stepNumber === totalSurveyStage2Steps ? 'none' : 'block';
    submitBtn.style.display = stepNumber === totalSurveyStage2Steps ? 'block' : 'none';
}

function validateCurrentStage2Step() {
    if (currentSurveyStage2Step === 1) {
        // Validate work focus
        const workFocus = document.querySelector('select[name="work_focus"]').value;
        if (!workFocus) {
            showSurveyError('Please select your work focus', 'survey-stage2-error');
            return false;
        }
        if (workFocus === 'other') {
            const workFocusOther = document.querySelector('input[name="work_focus_other"]').value.trim();
            if (!workFocusOther) {
                showSurveyError('Please specify your work focus', 'survey-stage2-error');
                return false;
            }
        }
    } else if (currentSurveyStage2Step === 2) {
        // Validate at least one PV segment
        const segments = document.querySelectorAll('input[name="pv_segment"]:checked');
        if (segments.length === 0) {
            showSurveyError('Please select at least one PV segment', 'survey-stage2-error');
            return false;
        }
    } else if (currentSurveyStage2Step === 3) {
        // Validate at least one technology
        const technologies = document.querySelectorAll('input[name="technology"]:checked');
        if (technologies.length === 0) {
            showSurveyError('Please select at least one technology', 'survey-stage2-error');
            return false;
        }
    } else if (currentSurveyStage2Step === 4) {
        // Validate at least one challenge (allow 1-3)
        const challenges = document.querySelectorAll('input[name="challenge"]:checked');
        if (challenges.length === 0) {
            showSurveyError('Please select at least one challenge', 'survey-stage2-error');
            return false;
        }
    }
    // Step 5 is optional (weekly insight)

    return true;
}

function nextSurveyStage2Step() {
    if (!validateCurrentStage2Step()) {
        return;
    }

    if (currentSurveyStage2Step < totalSurveyStage2Steps) {
        currentSurveyStage2Step++;
        showSurveyStage2Step(currentSurveyStage2Step);
        updateSurveyStage2Progress();
    }
}

function prevSurveyStage2Step() {
    if (currentSurveyStage2Step > 1) {
        currentSurveyStage2Step--;
        showSurveyStage2Step(currentSurveyStage2Step);
        updateSurveyStage2Progress();
    }
}

function updateSurveyStage2Progress() {
    const progressFill = document.getElementById('survey-stage2-progress-fill');
    const currentStepSpan = document.getElementById('survey-stage2-current-step');

    const progressPercent = (currentSurveyStage2Step / totalSurveyStage2Steps) * 100;
    progressFill.style.width = `${progressPercent}%`;
    currentStepSpan.textContent = currentSurveyStage2Step;
}

async function submitSurveyStage2(event) {
    event.preventDefault();

    const form = document.getElementById('user-survey-stage2-form');
    const formData = new FormData(form);

    // Validate at least one PV segment
    const pvSegments = formData.getAll('pv_segment');
    if (pvSegments.length === 0) {
        showSurveyError('Please select at least one PV segment', 'survey-stage2-error');
        return;
    }

    // Validate at least one technology
    const technologies = formData.getAll('technology');
    if (technologies.length === 0) {
        showSurveyError('Please select at least one technology', 'survey-stage2-error');
        return;
    }

    // Validate challenges (1-3)
    const challenges = formData.getAll('challenge');
    if (challenges.length === 0) {
        showSurveyError('Please select at least one challenge', 'survey-stage2-error');
        return;
    }
    if (challenges.length > 3) {
        showSurveyError('Please select a maximum of 3 challenges', 'survey-stage2-error');
        return;
    }

    // Prepare data
    const surveyData = {
        work_focus: formData.get('work_focus'),
        work_focus_other: formData.get('work_focus') === 'other' ? formData.get('work_focus_other') : null,
        pv_segments: pvSegments,
        technologies: technologies,
        technologies_other: technologies.includes('other') ? formData.get('technologies_other') : null,
        challenges: challenges,
        weekly_insight: formData.get('weekly_insight') || null
    };

    try {
        // Get CSRF token
        const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';

        const response = await fetch('/submit-user-survey-stage2', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(surveyData)
        });

        const data = await response.json();

        if (response.ok && data.success) {
            closeSurveyStage2Modal();

            // Show success message in chat
            addMessage({
                type: 'string',
                value: `🎉 **Thank you for completing the survey!**\n\nYou've unlocked **5 extra queries**. You now have ${data.new_query_count} queries available.\n\nReloading to activate your bonus queries...`
            }, false);

            // Reload page after 2 seconds to refresh session with new query limit
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else {
            showSurveyError(data.message || 'Failed to submit survey. Please try again.', 'survey-stage2-error');
        }
    } catch (error) {
        console.error('Error submitting Stage 2 survey:', error);
        showSurveyError('Failed to submit survey. Please try again.', 'survey-stage2-error');
    }
}
