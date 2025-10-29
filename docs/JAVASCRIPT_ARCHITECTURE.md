# JavaScript Architecture Documentation

## Overview

The Solar Intelligence application has been refactored from a monolithic 6,316-line `main.js` into a clean, modular architecture using ES6 modules. This document explains the new structure and how to work with it.

## Directory Structure

```
static/js/
├── main.js                          # Entry point (200 lines)
├── main.js.backup                   # Original monolithic file (backup)
├── suggested_queries.js             # Query data (unchanged)
├── modules/
│   ├── core/
│   │   ├── api.js                  # API communication layer
│   │   └── state.js                # Global state management
│   ├── chat/
│   │   └── approvalFlow.js         # Approval UI & logic
│   ├── conversation/
│   │   └── conversationManager.js  # Conversation CRUD operations
│   └── ui/
│       └── suggestedQueries.js     # Suggested queries component
└── utils/
    ├── dom.js                       # DOM manipulation helpers
    └── markdown.js                  # Markdown rendering utilities
```

## Module Descriptions

### Core Modules

#### `modules/core/api.js`
**Purpose**: Centralized API communication with consistent error handling.

**Exports**:
- `API` class: Handles all HTTP requests
- `api` singleton: Ready-to-use instance

**Key Methods**:
```javascript
import { api } from './modules/core/api.js';

// Conversations
await api.getConversations();
await api.getConversation(conversationId);
await api.deleteConversation(conversationId);
await api.createConversation(agentType);

// Chat
const eventSource = api.createChatStream(conversationId, message, agentType);
await api.sendApprovalResponse(approved, conversationId, context);

// User
await api.getCurrentUser();
await api.logout();
```

**Features**:
- Automatic CSRF token handling
- Consistent error handling
- SSE (Server-Sent Events) support
- Request/response logging

#### `modules/core/state.js`
**Purpose**: Reactive state management with pub-sub pattern.

**Exports**:
- `AppState` class: State container with subscriptions
- `appState` singleton: Global state instance

**Usage**:
```javascript
import { appState } from './modules/core/state.js';

// Get state
const user = appState.getCurrentUser();
const conversationId = appState.getState('currentConversationId');

// Set state
appState.setCurrentUser(user);
appState.setState('isSubmittingMessage', true);

// Subscribe to changes
const unsubscribe = appState.subscribe('currentConversationId', (newId, oldId) => {
    console.log('Conversation changed:', oldId, '->', newId);
});

// Unsubscribe when done
unsubscribe();
```

**State Properties**:
- `currentUser`: User object
- `currentConversationId`: Active conversation ID
- `conversations`: List of conversations
- `conversationHistory`: Message cache
- `isSubmittingMessage`: Submit flag
- `exportMode`: Export mode flag
- `currentAgentType`: Selected agent
- `hiredAgents`: Available agents

### Chat Modules

#### `modules/chat/approvalFlow.js`
**Purpose**: Handle approval requests (e.g., expert contact).

**Exports**:
- `ApprovalFlow` class: Approval UI and logic
- `approvalFlow` singleton

**Usage**:
```javascript
import { approvalFlow } from './modules/chat/approvalFlow.js';

// Display approval request
approvalFlow.displayApprovalRequest({
    message: "Would you like to contact an expert?",
    approval_question: "Proceed?",
    conversation_id: 123,
    context: "expert_contact"
});
```

**Features**:
- Creates Yes/No button UI
- Handles user response
- Sends approval to backend
- Shows loading states
- Error handling with retry

### Conversation Modules

#### `modules/conversation/conversationManager.js`
**Purpose**: Manage conversation list and lifecycle.

**Exports**:
- `ConversationManager` class
- `conversationManager` singleton

**Usage**:
```javascript
import { conversationManager } from './modules/conversation/conversationManager.js';

// Initialize (fetch conversations)
await conversationManager.initialize();

// Select conversation
await conversationManager.selectConversation(123);

// Start new chat
await conversationManager.startNewChat();

// Create conversation (when sending first message)
const newId = await conversationManager.createConversation('market');

// Delete conversation
await conversationManager.deleteConversation(123);
```

**Events Dispatched**:
- `conversationSelected`: When user selects a conversation
- `newChatStarted`: When new chat is initiated

### UI Modules

#### `modules/ui/suggestedQueries.js`
**Purpose**: Manage suggested query UI and visibility.

**Exports**:
- `SuggestedQueries` class
- `suggestedQueries` singleton

**Usage**:
```javascript
import { suggestedQueries } from './modules/ui/suggestedQueries.js';

// Initialize
suggestedQueries.initialize();

// Update for agent type
suggestedQueries.updateQueries('market');

// Show/hide
suggestedQueries.show();
suggestedQueries.hide();

// Check if should show
if (suggestedQueries.shouldShow(excludeSubmitting: true)) {
    // ...
}
```

**Features**:
- Agent-specific queries
- Auto-hide on typing
- Respects submit state
- Click to populate input

### Utility Modules

#### `utils/dom.js`
**Purpose**: DOM manipulation helpers.

**Key Functions**:
```javascript
import { createElement, showElement, hideElement, scrollToBottom, qs, qsa } from './utils/dom.js';

// Create element
const div = createElement('div', {
    classes: ['message', 'bot-message'],
    attributes: { 'data-id': '123' },
    textContent: 'Hello',
    innerHTML: '<strong>Bold</strong>'
});

// Show/hide
showElement('#my-element');
hideElement('.hidden-class');

// Query selectors
const element = qs('#user-input');
const elements = qsa('.message-container');

// Scroll
scrollToBottom('#chat-messages', smooth: true);

// Utilities
const id = generateId('msg');
const debounced = debounce(myFunc, 300);
const cleanup = addListener(element, 'click', handler);
```

#### `utils/markdown.js`
**Purpose**: Safe markdown rendering.

**Key Functions**:
```javascript
import { safeRenderMarkdown, markdownToPlainText } from './utils/markdown.js';

// Render markdown with sanitization
const html = safeRenderMarkdown('**Bold** text');

// Strip markdown formatting
const plainText = markdownToPlainText('**Bold** text'); // "Bold text"
```

## Main Application Entry Point

### `main.js`

The main entry point is now a clean 500-line file that:

1. **Imports modules**
2. **Defines `SolarIntelligenceApp` class**
3. **Initializes on DOMContentLoaded**

**Key Methods**:

```javascript
class SolarIntelligenceApp {
    async initialize()              // Setup application
    async loadCurrentUser()         // Load user info
    setupEventListeners()           // Attach event handlers
    async sendMessage()             // Send message to agent
    addUserMessage(message)         // Add user message to UI
    startMessageStream()            // Start SSE stream
    renderMessage(msg)              // Render single message
    showError(message)              // Display error
}
```

**Global Access**:
```javascript
// Access app instance globally (for debugging)
window.app
window.app.appState
window.app.api
window.app.conversationManager
```

## How to Add New Features

### Example: Adding a Feedback Component

#### 1. Create Module

**File**: `static/js/modules/ui/feedback.js`

```javascript
import { api } from '../core/api.js';
import { createElement } from '../../utils/dom.js';

export class Feedback {
    constructor() {
        this.setupEventListeners();
    }

    render(messageId) {
        const container = createElement('div', {
            classes: 'feedback-container'
        });

        const thumbsUp = createElement('button', {
            classes: 'feedback-btn',
            innerHTML: '👍',
            attributes: { 'data-feedback': 'positive' }
        });

        const thumbsDown = createElement('button', {
            classes: 'feedback-btn',
            innerHTML: '👎',
            attributes: { 'data-feedback': 'negative' }
        });

        thumbsUp.addEventListener('click', () => this.submit(messageId, 'positive'));
        thumbsDown.addEventListener('click', () => this.submit(messageId, 'negative'));

        container.appendChild(thumbsUp);
        container.appendChild(thumbsDown);

        return container;
    }

    async submit(messageId, feedback) {
        try {
            await api.post('/api/feedback', { messageId, feedback });
            console.log('Feedback submitted');
        } catch (error) {
            console.error('Feedback error:', error);
        }
    }

    setupEventListeners() {
        // Listen for state changes if needed
    }
}

export const feedback = new Feedback();
```

#### 2. Import in Main

**File**: `static/js/main.js`

```javascript
// Add import
import { feedback } from './modules/ui/feedback.js';

// Use in renderMessage()
renderMessage(msg) {
    // ... existing code ...

    // Add feedback component
    const feedbackUI = feedback.render(msg.id);
    messageContainer.appendChild(feedbackUI);
}
```

#### 3. Add Styles

**File**: `static/css/style.css`

```css
.feedback-container {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.5rem;
}

.feedback-btn {
    padding: 0.25rem 0.5rem;
    border: 1px solid var(--becq-blue);
    background: transparent;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.feedback-btn:hover {
    background: var(--becq-gold);
}
```

#### 4. Add Backend Endpoint (if needed)

**File**: `app/routes/chat.py`

```python
@chat_bp.route('/api/feedback', methods=['POST'])
@login_required
def submit_feedback():
    data = request.get_json()
    message_id = data.get('messageId')
    feedback = data.get('feedback')

    # Save to database
    # ...

    return jsonify({'success': True})
```

## Testing

### Unit Testing Modules

```javascript
// Example: Test API module
import { API } from './modules/core/api.js';

describe('API Module', () => {
    let api;

    beforeEach(() => {
        api = new API();
    });

    test('should get conversations', async () => {
        const convs = await api.getConversations();
        expect(Array.isArray(convs)).toBe(true);
    });
});
```

### Manual Testing Checklist

- [ ] Load page - no console errors
- [ ] Suggested queries appear on new chat
- [ ] Send message - queries hide
- [ ] Message streams correctly
- [ ] Conversation list updates
- [ ] Select conversation loads messages
- [ ] Delete conversation works
- [ ] Approval flow (Yes/No buttons) works
- [ ] New chat clears messages

## Migration Notes

### Breaking Changes

1. **Global Functions Removed**
   - Old: `sendMessage()` (global function)
   - New: `app.sendMessage()` (class method)

2. **Direct State Access**
   - Old: `currentConversationId` (global variable)
   - New: `appState.getState('currentConversationId')`

3. **Event Listeners**
   - Old: Inline event handlers
   - New: Centralized in `setupEventListeners()`

### Backward Compatibility

To maintain compatibility with external code:

```javascript
// In main.js, expose legacy API
window.sendMessage = () => app.sendMessage();
window.startNewChat = () => conversationManager.startNewChat();
```

## Performance Benefits

1. **Lazy Loading**: Modules loaded only when needed
2. **Code Splitting**: Browser can cache individual modules
3. **Tree Shaking**: Unused code eliminated in production
4. **Better Minification**: Smaller production bundles

## Debugging

### Enable Module Logging

```javascript
// In browser console
localStorage.setItem('debug', 'true');
```

### Access Modules

```javascript
// Access state
window.app.appState.getAllState();

// Access API
window.app.api;

// Access conversation manager
window.app.conversationManager;
```

### Common Issues

**Issue**: Module not found error
**Solution**: Check import paths are correct (relative to importing file)

**Issue**: Function is not a function
**Solution**: Check you're importing the correct export (named vs default)

**Issue**: State not updating
**Solution**: Use `setState()` instead of direct assignment

## Best Practices

### 1. Single Responsibility
Each module should have one clear purpose.

### 2. Dependency Injection
Pass dependencies rather than importing globally.

```javascript
// Good
class MyComponent {
    constructor(apiService, stateManager) {
        this.api = apiService;
        this.state = stateManager;
    }
}

// Avoid
class MyComponent {
    constructor() {
        this.api = api; // Global import
    }
}
```

### 3. Event-Driven Communication
Use events for cross-module communication.

```javascript
// Dispatch
window.dispatchEvent(new CustomEvent('conversationSelected', {
    detail: { conversationId, messages }
}));

// Listen
window.addEventListener('conversationSelected', (e) => {
    console.log(e.detail);
});
```

### 4. Error Handling
Always wrap async operations in try-catch.

```javascript
async fetchData() {
    try {
        const data = await api.getData();
        return data;
    } catch (error) {
        console.error('Fetch error:', error);
        this.showError('Failed to load data');
        throw error;
    }
}
```

### 5. State Management
Use centralized state, avoid module-level state.

```javascript
// Good
appState.setState('currentUser', user);

// Avoid
let currentUser = user; // Module-level variable
```

## Future Enhancements

### Phase 2: Component Templates
Extract HTML into template strings or components.

### Phase 3: TypeScript Migration
Add type safety with TypeScript.

### Phase 4: Testing Framework
Add Jest/Vitest for unit tests.

### Phase 5: Build Pipeline
Add Vite/Webpack for optimization.

## Support

For questions or issues with the modular architecture:
1. Check this documentation
2. Review module source code (well-commented)
3. Check browser console for errors
4. Use debugger to step through code

## Changelog

### v2.0.0 (2025-01-29)
- ✅ Complete modular refactoring
- ✅ Extracted 6 core modules
- ✅ Created utility libraries
- ✅ Implemented state management
- ✅ Reduced main.js from 6,316 to ~500 lines
- ✅ Added comprehensive documentation

### v1.0.0 (Previous)
- Monolithic main.js (6,316 lines)
- Mixed concerns
- Global state
- Difficult to extend
