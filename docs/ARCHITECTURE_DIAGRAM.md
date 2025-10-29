# Solar Intelligence App - Architecture Diagram

## Module Dependency Graph

```
┌─────────────────────────────────────────────────────────────────┐
│                         templates/index.html                     │
│                  <script type="module" src="main.js">            │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      static/js/main.js (595 lines)               │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │        class SolarIntelligenceApp                        │   │
│  │  - initialize()                                          │   │
│  │  - loadCurrentUser()                                     │   │
│  │  - sendMessage()                                         │   │
│  │  - startMessageStream()                                  │   │
│  │  - handleConversationSelected()                          │   │
│  │  - updateWelcomeMessageVisibility()                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
└───┬───────┬───────┬───────┬───────┬───────┬───────┬────────────┘
    │       │       │       │       │       │       │
    ▼       ▼       ▼       ▼       ▼       ▼       ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  api   │ │ state  │ │convMgr │ │queries │ │approval│ │  plot  │
└────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘
┌────────┐ ┌────────┐
│  dom   │ │markdown│
└────────┘ └────────┘
```

## Detailed Module Structure

```
static/js/
│
├── main.js (595 lines) ─────────────────────────────────────┐
│   │                                                         │
│   ├─> SolarIntelligenceApp class                           │
│   │   ├─> Event Handlers                                   │
│   │   ├─> Message Streaming                                │
│   │   └─> UI State Management                              │
│   │                                                         │
│   └─> DOMContentLoaded initialization                      │
│                                                             │
├── modules/                                                  │
│   │                                                         │
│   ├── core/                                                 │
│   │   ├── api.js (227 lines) ◄──────────────────────────┐ │
│   │   │   └── class API                                  │ │
│   │   │       ├── request(url, options)                  │ │
│   │   │       ├── get/post/delete/patch                  │ │
│   │   │       ├── Conversation endpoints                 │ │
│   │   │       ├── Chat endpoints                         │ │
│   │   │       ├── User endpoints                         │ │
│   │   │       └── Export/Survey/News endpoints           │ │
│   │   │                                                   │ │
│   │   └── state.js (264 lines) ◄────────────────────────┐│ │
│   │       └── class AppState                             ││ │
│   │           ├── setState(key, value)                   ││ │
│   │           ├── getState(key)                          ││ │
│   │           └── subscribe(key, callback)               ││ │
│   │                                                       ││ │
│   ├── chat/                                               ││ │
│   │   ├── approvalFlow.js (193 lines) ◄──────────────────┼┼─┤
│   │   │   └── class ApprovalFlow                         ││ │
│   │   │       ├── displayApprovalRequest()               ││ │
│   │   │       ├── createApprovalUI()                     ││ │
│   │   │       └── handleApprovalResponse()               ││ │
│   │   │           └─> api.sendApprovalResponse() ────────┘│ │
│   │   │                                                    │ │
│   │   └── plotHandler.js (165 lines) ◄────────────────────┼─┤
│   │       └── class PlotHandler                           │ │
│   │           └── createPlot(eventData, agentType, ...)   │ │
│   │               ├─> createElement() ──────────────────┐ │ │
│   │               ├─> scrollToBottom() ─────────────────┤ │ │
│   │               └─> window.renderD3Chart()            │ │ │
│   │                                                      │ │ │
│   ├── conversation/                                      │ │ │
│   │   └── conversationManager.js (296 lines) ◄──────────┼─┼─┤
│   │       └── class ConversationManager                 │ │ │
│   │           ├── initialize()                          │ │ │
│   │           ├── fetchConversations() ─────> api.get() ┘ │ │
│   │           ├── createConversation() ─────> api.post()  │ │
│   │           ├── deleteConversation() ─────> api.delete()│ │
│   │           ├── selectConversation()                    │ │
│   │           └── renderConversationList()                │ │
│   │               └─> createElement() ──────────────────┐ │ │
│   │                                                      │ │ │
│   └── ui/                                                │ │ │
│       └── suggestedQueries.js (175 lines) ◄─────────────┼─┼─┤
│           └── class SuggestedQueries                    │ │ │
│               ├── initialize()                          │ │ │
│               ├── updateQueries(agentType)              │ │ │
│               ├── show() / hide()                       │ │ │
│               ├── updateVisibility()                    │ │ │
│               └── subscribe to appState ────────────────┘ │ │
│                                                            │ │
└── utils/                                                   │ │
    ├── dom.js (199 lines) ◄─────────────────────────────────┘ │
    │   ├── qs(selector)                                       │
    │   ├── qsa(selector)                                      │
    │   ├── createElement(tag, options)                        │
    │   ├── scrollToBottom(element)                            │
    │   ├── showElement(element) / hideElement(element)        │
    │   └── toggleClass(element, className)                    │
    │                                                           │
    └── markdown.js (42 lines) ◄──────────────────────────────┘
        └── safeRenderMarkdown(text)
            ├─> marked.parse()
            └─> DOMPurify.sanitize()
```

## Data Flow Diagrams

### 1. User Sends Message

```
┌─────────┐
│  User   │ types message
└────┬────┘
     │
     ▼
┌──────────────────┐
│ #user-input      │
│ <textarea>       │
└────┬─────────────┘
     │ keypress(Enter) or click(#send-btn)
     ▼
┌──────────────────────────────┐
│ app.sendMessage()            │
│ - Validate input             │
│ - Set submitting flag        │
│ - Add user message to UI     │
└────┬─────────────────────────┘
     │
     ├──> suggestedQueries.hide()
     │
     ├──> conversationManager.createConversation() if needed
     │    └──> api.post('/conversations/fresh')
     │         └──> Backend creates conversation
     │              └──> Returns { id: 123 }
     │
     ▼
┌──────────────────────────────┐
│ app.showLoadingIndicator()   │
│ - Create loading spinner     │
│ - Show in chat               │
└────┬─────────────────────────┘
     │
     ▼
┌──────────────────────────────┐
│ app.startMessageStream()     │
│ - POST to /chat              │
│ - Get Response body          │
│ - Create ReadableStream      │
└────┬─────────────────────────┘
     │
     ▼
┌──────────────────────────────┐
│ api.sendChatMessage()        │
│ POST /chat                   │
│ {                            │
│   message: "...",            │
│   conversation_id: 123,      │
│   agent_type: "price"        │
│ }                            │
└────┬─────────────────────────┘
     │
     ▼
┌──────────────────────────────┐
│ Backend Processing           │
│ - Route to agent             │
│ - Query database/API         │
│ - Generate response          │
│ - Stream SSE events          │
└────┬─────────────────────────┘
     │
     └──> SSE Stream ────┐
                         │
     ┌───────────────────┘
     │
     ▼
┌──────────────────────────────┐
│ reader.read() loop           │
│ - Decode chunks              │
│ - Parse SSE lines            │
│ - Extract JSON events        │
└────┬─────────────────────────┘
     │
     ├─> Event: status ───────> app.handleStatusEvent()
     │                           └─> Update loading text
     │
     ├─> Event: chunk/text ───> Accumulate text
     │                           └─> Render markdown incrementally
     │
     ├─> Event: plot ─────────> plotHandler.createPlot()
     │                           ├─> Create plot card
     │                           ├─> Generate unique ID
     │                           └─> Render D3 chart
     │
     ├─> Event: approval ─────> approvalFlow.displayApprovalRequest()
     │                           ├─> Create approval UI
     │                           └─> Wait for user response
     │
     ├─> Event: error ────────> app.handleErrorEvent()
     │                           └─> Show error message
     │
     └─> Event: done ─────────> app.removeLoadingIndicator()
                                 ├─> Update welcome visibility
                                 └─> Set submitting = false
```

### 2. State Management Flow

```
┌──────────────────────────────┐
│ User Action                  │
│ - Select agent               │
│ - Create conversation        │
│ - Submit message             │
└────┬─────────────────────────┘
     │
     ▼
┌──────────────────────────────┐
│ appState.setState(key, value)│
└────┬─────────────────────────┘
     │
     ├─> Compare: oldValue !== newValue ?
     │   └─> No change → Return early
     │   └─> Changed → Continue
     │
     ├─> Update: this.state[key] = value
     │
     └─> Notify subscribers
         │
         ├─> subscribers[key].forEach(callback)
         │   │
         │   ├─> suggestedQueries.updateQueries(agentType)
         │   │   └─> Render new query suggestions
         │   │
         │   ├─> conversationManager.updateActiveConv(id)
         │   │   └─> Highlight selected conversation
         │   │
         │   └─> app.updateWelcomeMessage()
         │       └─> Change welcome text for agent
         │
         └─> All subscribers execute in order
```

### 3. API Request Flow

```
┌──────────────────────────────┐
│ Module calls API method      │
│ api.get('/conversations')    │
└────┬─────────────────────────┘
     │
     ▼
┌──────────────────────────────┐
│ api.request(url, options)    │
│ - Add CSRF token             │
│ - Set credentials            │
│ - Merge headers              │
└────┬─────────────────────────┘
     │
     ▼
┌──────────────────────────────┐
│ fetch(url, options)          │
└────┬─────────────────────────┘
     │
     ├─> Success (200-299) ────> response.json()
     │                           └─> Return data
     │
     └─> Error (4xx/5xx) ──────> Extract error message
                                  ├─> Try response.json()
                                  ├─> Fallback to HTTP status
                                  └─> throw Error(message)
                                      │
                                      ▼
                                  ┌──────────────────────────┐
                                  │ Calling code catches     │
                                  │ - Log to console         │
                                  │ - Show user message      │
                                  └──────────────────────────┘
```

## Event Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser Events                           │
└───┬─────────────────┬─────────────────┬───────────────┬─────────┘
    │                 │                 │               │
    │ DOMContentLoaded│ click          │ keypress      │ change
    │                 │                 │               │
    ▼                 ▼                 ▼               ▼
┌────────┐      ┌────────┐      ┌────────┐      ┌────────┐
│ init   │      │ send   │      │ send   │      │ agent  │
│ app    │      │ button │      │ Enter  │      │ select │
└───┬────┘      └───┬────┘      └───┬────┘      └───┬────┘
    │               │               │               │
    │               └───────┬───────┘               │
    │                       │                       │
    ▼                       ▼                       ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│ app.initialize │  │ app.sendMessage│  │ appState.set   │
└───┬────────────┘  └───┬────────────┘  │ AgentType      │
    │                   │               └───┬────────────┘
    │                   │                   │
    ▼                   ▼                   ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│ Load modules   │  │ Stream SSE     │  │ Notify         │
│ - convManager  │  │ - Handle events│  │ subscribers    │
│ - queries      │  │ - Render UI    │  └────────────────┘
│ - approvalFlow │  └────────────────┘
└────────────────┘
```

## Module Interaction Matrix

| Module | Depends On | Used By | Purpose |
|--------|-----------|---------|---------|
| **main.js** | api, state, convManager, queries, approval, plot, dom, markdown | - | App orchestration |
| **api.js** | - | main, convManager, approval | HTTP communication |
| **state.js** | - | main, queries, convManager | Reactive state |
| **convManager.js** | api, state, dom | main | Conversation CRUD |
| **queries.js** | state, dom | main | Query suggestions |
| **approval.js** | api, dom | main | Expert approval |
| **plot.js** | dom | main | Chart rendering |
| **dom.js** | - | all modules | DOM utilities |
| **markdown.js** | marked, DOMPurify | main | Safe rendering |

## External Dependencies

```
┌─────────────────────────────────────────────────────────────────┐
│                      templates/index.html                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  <script src="marked.min.js">        <!-- Markdown parser -->   │
│  <script src="dompurify.min.js">     <!-- XSS sanitizer -->     │
│  <script src="d3.v7.min.js">         <!-- Chart library -->     │
│  <script src="d3-legend.min.js">     <!-- Legend plugin -->     │
│  <script src="chart-utils.js">       <!-- Chart helpers -->     │
│                                                                   │
│  <script type="module" src="main.js"> <!-- Our app -->          │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
         │              │               │
         ▼              ▼               ▼
    ┌─────────┐  ┌───────────┐  ┌──────────────┐
    │ marked  │  │ DOMPurify │  │ D3.js        │
    │ .parse()│  │ .sanitize()│  │ renderD3Chart│
    └─────────┘  └───────────┘  └──────────────┘
         │              │               │
         └──────┬───────┴───────┬───────┘
                │               │
                ▼               ▼
         ┌─────────────┐ ┌──────────────┐
         │ markdown.js │ │ plotHandler  │
         └─────────────┘ └──────────────┘
```

## Summary

### Architecture Principles

1. **Modular Design**: Each module has single responsibility
2. **Clear Dependencies**: Import/export makes dependencies explicit
3. **Separation of Concerns**: UI, data, business logic separated
4. **Reactive State**: Pub-sub pattern for state changes
5. **Error Boundaries**: Try-catch at module boundaries
6. **Type Safety**: JSDoc comments document expected types
7. **Consistent Patterns**: All modules follow same structure

### Benefits

- **Maintainability**: Easy to find and modify specific functionality
- **Testability**: Modules can be tested in isolation
- **Reusability**: Utilities and modules can be reused
- **Scalability**: Easy to add new modules and features
- **Debugging**: Clear separation makes issues easier to isolate
- **Collaboration**: Multiple developers can work on different modules

### Trade-offs

- **More Files**: 8 modules vs 1 monolithic file
- **HTTP Requests**: Each module is a separate request (needs bundling for production)
- **Complexity**: More moving parts to understand
- **Learning Curve**: Team needs to understand module system
