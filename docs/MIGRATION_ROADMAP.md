# Migration Roadmap: Flask + Vanilla JS → FastAPI + React

**Current Stack**: Flask + SQLAlchemy + Jinja2 + Vanilla JavaScript
**Target Stack**: FastAPI + SQLAlchemy + React + TypeScript
**Status**: Planning Phase
**Estimated Timeline**: 3-6 months

---

## Executive Summary

This document outlines a phased migration strategy to transition from Flask to FastAPI and vanilla JavaScript to React, while maintaining service continuity and minimizing risk.

**Key Principles**:
1. **Incremental Migration** - No big bang rewrites
2. **Parallel Operation** - New and old systems coexist
3. **Zero Downtime** - Users never affected
4. **Data Integrity** - Database remains consistent
5. **Feature Parity** - No functionality lost

---

## Current State Analysis

### Backend (Flask)
```
app.py (3,300+ lines)
├── Routes: ~80 endpoints
├── Authentication: Flask-Login
├── Database: SQLAlchemy ORM
├── API Style: Mixed (REST-ish)
├── Validation: Manual/ad-hoc
└── Documentation: None (code comments only)
```

**Strengths**:
- ✅ Mature, battle-tested
- ✅ SQLAlchemy ORM (reusable)
- ✅ Good authentication system
- ✅ Comprehensive GDPR compliance

**Weaknesses**:
- ❌ Monolithic structure (3,300 lines in one file)
- ❌ Mixed concerns (routes + business logic)
- ❌ No API documentation
- ❌ Inconsistent validation
- ❌ No type hints
- ❌ Manual async handling

### Frontend (Vanilla JS)
```
main.js (5,872 lines)
├── DOM Manipulation: Direct
├── State Management: Global variables
├── API Calls: Fetch API
├── Rendering: innerHTML + templates
└── Type Safety: None
```

**Strengths**:
- ✅ No build step required
- ✅ Fast page loads
- ✅ SSE streaming works well
- ✅ D3.js charts (reusable)

**Weaknesses**:
- ❌ Monolithic JS file (5,872 lines)
- ❌ No component structure
- ❌ No state management
- ❌ No type safety
- ❌ Hard to test
- ❌ Repetitive code patterns

---

## Phase 1: Clean Up Current Codebase (1-2 months)

**Goal**: Make current code migration-ready

### Backend Tasks

#### 1.1: Refactor app.py into Modules (2 weeks)
**Priority**: HIGH

```
app.py (3,300 lines) →

app.py (200 lines)          # App initialization only
├── routes/
│   ├── __init__.py         # Blueprint registration
│   ├── auth.py             # /login, /register, /logout
│   ├── chat.py             # /chat endpoint
│   ├── conversations.py    # Conversation CRUD
│   ├── agents.py           # Agent management
│   ├── admin.py            # Admin operations
│   └── api.py              # API endpoints
├── services/
│   ├── __init__.py
│   ├── auth_service.py     # Authentication logic
│   ├── agent_service.py    # Agent execution
│   ├── query_service.py    # Query processing
│   └── user_service.py     # User management
├── schemas/
│   ├── __init__.py
│   ├── user.py             # Pydantic models (FastAPI-ready!)
│   ├── conversation.py
│   └── agent.py
└── utils/
    ├── __init__.py
    ├── validators.py       # Input validation
    └── helpers.py
```

**Benefits**:
- Clean separation of concerns
- Services layer easily portable to FastAPI
- Pydantic schemas work in both Flask and FastAPI
- Each module < 300 lines (maintainable)

**See**: [REFACTORING_GUIDE.md](./REFACTORING_GUIDE.md) for detailed plan

#### 1.2: Add Type Hints Everywhere (1 week)
**Priority**: HIGH

```python
# Before
def get_user(user_id):
    user = User.query.get(user_id)
    return user

# After (FastAPI-ready)
from typing import Optional
from models import User

def get_user(user_id: int) -> Optional[User]:
    """Get user by ID"""
    user = User.query.get(user_id)
    return user
```

**Benefits**:
- Immediate IDE autocomplete
- Catches bugs before runtime
- FastAPI requires type hints
- Better documentation

#### 1.3: Create API Schemas with Pydantic (1 week)
**Priority**: HIGH

```python
# Create schemas/user.py (works in Flask AND FastAPI!)
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    """Schema for user registration"""
    username: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=100)
    gdpr_consent: bool
    terms_accepted: bool

class UserResponse(BaseModel):
    """Schema for user data in responses"""
    id: int
    username: str
    full_name: str
    role: str
    plan_type: str
    created_at: datetime

    class Config:
        from_attributes = True  # Works with SQLAlchemy models

class QueryRequest(BaseModel):
    """Schema for chat query"""
    message: str = Field(min_length=1, max_length=5000)
    conversation_id: int
    agent_type: str = Field(pattern="^(market|price|news|om|digitalization)$")

class QueryResponse(BaseModel):
    """Schema for query response"""
    response: list[dict]
    conversation_id: int
    timestamp: datetime
```

**Benefits**:
- Automatic validation
- API documentation
- Type safety
- Works in both Flask and FastAPI

**Usage in Flask** (during transition):
```python
from schemas.user import UserCreate, UserResponse

@app.route('/register', methods=['POST'])
def register():
    try:
        # Validate with Pydantic
        user_data = UserCreate(**request.get_json())

        # Use validated data
        user = User(
            username=user_data.username,
            full_name=user_data.full_name,
            # ...
        )
        # ...

        # Return with schema
        return UserResponse.from_orm(user).dict()
    except ValidationError as e:
        return jsonify({'errors': e.errors()}), 400
```

#### 1.4: Extract Business Logic to Services (2 weeks)
**Priority**: MEDIUM

```python
# services/agent_service.py (FastAPI-ready!)
from typing import AsyncIterator, Dict, Any
from models import User, Conversation

class AgentService:
    """Business logic for agent operations"""

    async def execute_query(
        self,
        user: User,
        conversation_id: int,
        message: str,
        agent_type: str
    ) -> Dict[str, Any]:
        """Execute agent query"""
        # This service works in both Flask and FastAPI!
        pass

    async def stream_response(
        self,
        user: User,
        conversation_id: int,
        message: str,
        agent_type: str
    ) -> AsyncIterator[str]:
        """Stream agent response (SSE)"""
        # Same async code works in both!
        pass
```

**Benefits**:
- Business logic independent of framework
- Easily testable
- Reusable in FastAPI
- Single source of truth

#### 1.5: Add Comprehensive Tests (2 weeks)
**Priority**: HIGH

```
tests/
├── unit/
│   ├── test_services.py       # Test business logic
│   ├── test_validators.py     # Test validation
│   └── test_schemas.py         # Test Pydantic models
├── integration/
│   ├── test_auth_flow.py      # Test login/register
│   ├── test_query_flow.py     # Test chat functionality
│   └── test_admin_flow.py     # Test admin operations
└── e2e/
    └── test_user_journey.py   # Full user scenarios
```

**Goal**: 80% test coverage before migration

---

### Frontend Tasks

#### 1.6: Modularize main.js (2 weeks)
**Priority**: HIGH

```
main.js (5,872 lines) →

src/
├── config/
│   └── constants.js        # CONFIG object
├── api/
│   └── client.js           # API calls (fetch wrapper)
├── auth/
│   └── auth.js             # Authentication logic
├── chat/
│   ├── chat.js             # Chat interface
│   ├── messages.js         # Message handling
│   └── streaming.js        # SSE streaming
├── agents/
│   └── agents.js           # Agent management
├── charts/
│   ├── d3-charts.js        # D3.js chart rendering
│   └── chart-utils.js      # Chart helpers
├── utils/
│   ├── dom.js              # DOM helpers
│   ├── validation.js       # Input validation
│   └── security.js         # safeRenderMarkdown()
└── main.js (200 lines)     # Entry point only
```

**Benefits**:
- Each module < 500 lines
- Clear responsibilities
- Easier to migrate piece by piece
- Can be converted to TypeScript modules

#### 1.7: Create API Client Layer (3 days)
**Priority**: HIGH

```javascript
// src/api/client.js (React-ready!)
class APIClient {
    constructor(baseURL = '') {
        this.baseURL = baseURL;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        };

        const response = await fetch(url, config);

        if (!response.ok) {
            throw new Error(`API Error: ${response.statusText}`);
        }

        return response.json();
    }

    // Auth
    async login(username, password) {
        return this.request('/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
    }

    // Chat
    async sendQuery(conversationId, message, agentType) {
        return this.request('/chat', {
            method: 'POST',
            body: JSON.stringify({
                conversation_id: conversationId,
                message,
                agent_type: agentType
            })
        });
    }

    // Conversations
    async getConversations() {
        return this.request('/conversations');
    }

    // Streaming (SSE)
    createEventSource(endpoint, data) {
        // SSE helper
        const eventSource = new EventSource(endpoint);
        return eventSource;
    }
}

export const api = new APIClient();
```

**Benefits**:
- Centralized API logic
- Easy to mock for testing
- Can be converted to TypeScript
- Works with React (just import it!)

#### 1.8: Extract Components (Pseudo) (1 week)
**Priority**: MEDIUM

Create pseudo-components (still vanilla JS, but structured like React):

```javascript
// src/chat/MessageComponent.js (React-like structure!)
export class MessageComponent {
    constructor(message, sender, timestamp) {
        this.message = message;
        this.sender = sender;
        this.timestamp = timestamp;
    }

    render() {
        const container = document.createElement('div');
        container.className = `message ${this.sender}-message`;

        const content = document.createElement('div');
        content.className = 'message-content';
        content.innerHTML = safeRenderMarkdown(this.message);

        const time = document.createElement('span');
        time.className = 'message-time';
        time.textContent = new Date(this.timestamp).toLocaleString();

        container.appendChild(content);
        container.appendChild(time);

        return container;
    }
}

// Later, converting to React is easy:
// export const MessageComponent = ({ message, sender, timestamp }) => (
//     <div className={`message ${sender}-message`}>
//         <div className="message-content"
//              dangerouslySetInnerHTML={{ __html: safeRenderMarkdown(message) }} />
//         <span className="message-time">
//             {new Date(timestamp).toLocaleString()}
//         </span>
//     </div>
// );
```

**Benefits**:
- Component mindset
- Easy to convert to React
- Testable in isolation
- Reusable

---

## Phase 2: Create New FastAPI Backend (2 months)

**Goal**: Build new API alongside Flask

### 2.1: Setup FastAPI Project (1 week)

```
fastapi_backend/
├── app/
│   ├── __init__.py
│   ├── main.py             # FastAPI app
│   ├── config.py           # Settings
│   ├── dependencies.py     # Dependency injection
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py         # Auth endpoints
│   │   ├── chat.py         # Chat endpoints
│   │   ├── conversations.py
│   │   └── admin.py
│   │
│   ├── services/           # Copy from Flask!
│   │   ├── auth_service.py
│   │   ├── agent_service.py
│   │   └── query_service.py
│   │
│   ├── schemas/            # Copy from Flask!
│   │   ├── user.py
│   │   ├── conversation.py
│   │   └── query.py
│   │
│   ├── models/             # Same SQLAlchemy models!
│   │   ├── __init__.py
│   │   └── models.py       # Copy from Flask models.py
│   │
│   └── core/
│       ├── security.py     # JWT, password hashing
│       └── database.py     # DB connection
│
├── tests/
├── alembic/                # Database migrations
├── .env
├── requirements.txt
└── docker-compose.yml
```

### 2.2: Implement Core Endpoints (4 weeks)

**Week 1: Authentication**
```python
# app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserResponse, Token
from app.services.auth_service import AuthService
from app.core.database import get_db

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register new user"""
    auth_service = AuthService(db)
    user = await auth_service.create_user(user_data)
    return user

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login user"""
    auth_service = AuthService(db)
    token = await auth_service.authenticate(form_data.username, form_data.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return token

@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user info"""
    return current_user
```

**Week 2: Conversations**
```python
# app/api/conversations.py
from fastapi import APIRouter, Depends
from app.schemas.conversation import ConversationResponse, ConversationCreate
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])

@router.get("/", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user conversations"""
    service = ConversationService(db)
    return await service.get_user_conversations(current_user.id)

@router.post("/", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    conversation: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new conversation"""
    service = ConversationService(db)
    return await service.create_conversation(current_user.id, conversation)
```

**Week 3: Chat/Query Endpoint**
```python
# app/api/chat.py
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.schemas.query import QueryRequest, QueryResponse
from app.services.agent_service import AgentService

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

@router.post("/", response_model=QueryResponse)
async def send_query(
    query: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send query to agent (non-streaming)"""
    service = AgentService(db)

    # Check query limits
    if not current_user.can_make_query():
        raise HTTPException(status_code=429, detail="Query limit reached")

    # Increment count BEFORE processing
    current_user.increment_query_count()
    db.commit()

    # Process query
    response = await service.execute_query(
        user=current_user,
        conversation_id=query.conversation_id,
        message=query.message,
        agent_type=query.agent_type
    )

    return response

@router.post("/stream")
async def stream_query(
    query: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send query to agent (streaming SSE)"""
    service = AgentService(db)

    # Check query limits
    if not current_user.can_make_query():
        raise HTTPException(status_code=429, detail="Query limit reached")

    # Increment count BEFORE processing
    current_user.increment_query_count()
    db.commit()

    # Stream response
    async def event_generator():
        async for chunk in service.stream_response(
            user=current_user,
            conversation_id=query.conversation_id,
            message=query.message,
            agent_type=query.agent_type
        ):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

**Week 4: Admin Endpoints**

### 2.3: Add Authentication (JWT) (1 week)

```python
# app/core/security.py
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt
```

### 2.4: Add Auto-Generated API Docs (automatic!)

FastAPI automatically generates:
- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI Schema**: `/openapi.json`

No extra work needed! Just visit `/docs` and you have interactive API documentation.

---

## Phase 3: Create React Frontend (2-3 months)

**Goal**: Build new UI consuming FastAPI

### 3.1: Setup React Project (1 week)

```bash
npx create-react-app solar-intelligence-frontend --template typescript
cd solar-intelligence-frontend

# Add dependencies
npm install @tanstack/react-query axios react-router-dom
npm install -D @types/react @types/react-dom
```

```
solar-intelligence-frontend/
├── public/
├── src/
│   ├── api/
│   │   ├── client.ts           # Axios instance
│   │   ├── auth.ts             # Auth API calls
│   │   ├── chat.ts             # Chat API calls
│   │   └── conversations.ts
│   │
│   ├── components/
│   │   ├── common/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   └── Loading.tsx
│   │   ├── chat/
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── MessageList.tsx
│   │   │   ├── MessageInput.tsx
│   │   │   └── AgentSelector.tsx
│   │   ├── charts/
│   │   │   └── D3Chart.tsx     # Reuse D3.js logic!
│   │   └── layout/
│   │       ├── Header.tsx
│   │       ├── Sidebar.tsx
│   │       └── Footer.tsx
│   │
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useChat.ts
│   │   └── useConversations.ts
│   │
│   ├── context/
│   │   ├── AuthContext.tsx
│   │   └── ChatContext.tsx
│   │
│   ├── types/
│   │   ├── user.ts
│   │   ├── conversation.ts
│   │   └── message.ts
│   │
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── Register.tsx
│   │   ├── Chat.tsx
│   │   └── Admin.tsx
│   │
│   ├── utils/
│   │   ├── validation.ts
│   │   └── formatting.ts
│   │
│   ├── App.tsx
│   └── index.tsx
│
├── package.json
├── tsconfig.json
└── .env
```

### 3.2: Implement Core Features (6 weeks)

**Week 1: Authentication**
```typescript
// src/api/auth.ts
import { apiClient } from './client';
import { User, LoginCredentials, RegisterData, Token } from '../types/user';

export const authAPI = {
    login: async (credentials: LoginCredentials): Promise<Token> => {
        const response = await apiClient.post('/api/v1/auth/login', credentials);
        return response.data;
    },

    register: async (data: RegisterData): Promise<User> => {
        const response = await apiClient.post('/api/v1/auth/register', data);
        return response.data;
    },

    getCurrentUser: async (): Promise<User> => {
        const response = await apiClient.get('/api/v1/auth/me');
        return response.data;
    }
};

// src/hooks/useAuth.ts
import { useContext } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { AuthContext } from '../context/AuthContext';
import { authAPI } from '../api/auth';

export const useAuth = () => {
    const context = useContext(AuthContext);

    const loginMutation = useMutation({
        mutationFn: authAPI.login,
        onSuccess: (data) => {
            localStorage.setItem('token', data.access_token);
            context.setUser(data.user);
        }
    });

    const { data: user, isLoading } = useQuery({
        queryKey: ['currentUser'],
        queryFn: authAPI.getCurrentUser,
        enabled: !!localStorage.getItem('token')
    });

    return {
        user,
        isLoading,
        login: loginMutation.mutate,
        isLoggingIn: loginMutation.isLoading
    };
};
```

**Week 2-3: Chat Interface**
```typescript
// src/components/chat/ChatInterface.tsx
import React, { useState } from 'react';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { AgentSelector } from './AgentSelector';
import { useChat } from '../../hooks/useChat';

export const ChatInterface: React.FC = () => {
    const [agentType, setAgentType] = useState('market');
    const { messages, sendMessage, isStreaming } = useChat();

    const handleSend = (message: string) => {
        sendMessage({
            message,
            agentType,
            conversationId: currentConversationId
        });
    };

    return (
        <div className="chat-interface">
            <AgentSelector value={agentType} onChange={setAgentType} />
            <MessageList messages={messages} isLoading={isStreaming} />
            <MessageInput onSend={handleSend} disabled={isStreaming} />
        </div>
    );
};

// src/hooks/useChat.ts
import { useState, useEffect } from 'react';
import { useSSE } from './useSSE';
import { chatAPI } from '../api/chat';

export const useChat = () => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [isStreaming, setIsStreaming] = useState(false);

    const sendMessage = async (query: QueryRequest) => {
        setIsStreaming(true);

        // Create SSE connection
        const eventSource = chatAPI.streamQuery(query);

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'chunk') {
                // Append chunk to current message
                setMessages(prev => appendChunk(prev, data.content));
            } else if (data.type === 'done') {
                // Message complete
                setIsStreaming(false);
            }
        };

        eventSource.onerror = () => {
            setIsStreaming(false);
            eventSource.close();
        };
    };

    return { messages, sendMessage, isStreaming };
};
```

**Week 4-5: Charts with D3**
```typescript
// src/components/charts/D3Chart.tsx
import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { ChartData } from '../../types/chart';

interface D3ChartProps {
    data: ChartData;
    type: 'line' | 'bar' | 'pie';
    width?: number;
    height?: number;
}

export const D3Chart: React.FC<D3ChartProps> = ({
    data,
    type,
    width = 800,
    height = 400
}) => {
    const svgRef = useRef<SVGSVGElement>(null);

    useEffect(() => {
        if (!svgRef.current) return;

        // Clear previous chart
        d3.select(svgRef.current).selectAll('*').remove();

        // Render chart based on type
        // (Reuse existing D3.js logic from main.js!)
        renderChart(svgRef.current, data, type, width, height);
    }, [data, type, width, height]);

    return <svg ref={svgRef} width={width} height={height} />;
};
```

**Week 6: Admin Panel**

### 3.3: Add TypeScript Types (ongoing)

```typescript
// src/types/user.ts
export interface User {
    id: number;
    username: string;
    full_name: string;
    role: 'user' | 'admin';
    plan_type: 'free' | 'premium';
    created_at: string;
    monthly_query_count: number;
    query_limit: number;
}

export interface LoginCredentials {
    username: string;
    password: string;
}

export interface RegisterData {
    username: string;
    password: string;
    full_name: string;
    gdpr_consent: boolean;
    terms_accepted: boolean;
}

export interface Token {
    access_token: string;
    token_type: string;
    user: User;
}

// src/types/conversation.ts
export interface Conversation {
    id: number;
    title: string;
    created_at: string;
    agent_type: string;
}

export interface Message {
    id: number;
    conversation_id: number;
    sender: 'user' | 'bot';
    content: MessageContent;
    timestamp: string;
}

export type MessageContent =
    | { type: 'string'; value: string }
    | { type: 'plot'; value: PlotData }
    | { type: 'table'; value: TableData };

// src/types/query.ts
export interface QueryRequest {
    message: string;
    conversation_id: number;
    agent_type: 'market' | 'price' | 'news' | 'om' | 'digitalization';
}
```

---

## Phase 4: Parallel Operation (1 month)

**Goal**: Run both systems simultaneously

### 4.1: Setup Routing

```nginx
# Nginx configuration
server {
    listen 80;
    server_name solarintelligence.ai;

    # New React app (static files)
    location / {
        root /var/www/react-app/build;
        try_files $uri /index.html;
    }

    # FastAPI backend (new)
    location /api/v1/ {
        proxy_pass http://fastapi:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Flask backend (old - for backward compatibility)
    location /api/legacy/ {
        proxy_pass http://flask:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 4.2: Gradual Traffic Migration

**Week 1**: 10% traffic to new stack
**Week 2**: 25% traffic
**Week 3**: 50% traffic
**Week 4**: 100% traffic to new stack

Use feature flags:
```typescript
// src/config/featureFlags.ts
export const useNewAPI = () => {
    // Gradually roll out to users
    const rolloutPercentage = 50; // 50% of users
    const userId = getCurrentUser()?.id || 0;
    return (userId % 100) < rolloutPercentage;
};
```

---

## Phase 5: Deprecate Old System (1 month)

### 5.1: Monitor Metrics (2 weeks)

Track:
- Error rates (new vs old)
- Response times
- User satisfaction
- Query success rates

### 5.2: Fix Issues (2 weeks)

Address any problems found in new system.

### 5.3: Decommission Flask (1 week)

Once new system is stable:
1. Announce deprecation (30 days notice)
2. Redirect all traffic to new system
3. Keep Flask running (read-only) for 30 days
4. Final shutdown

---

## Benefits of New Stack

### FastAPI Benefits
- ⚡ **50% faster** than Flask (async by default)
- 📚 **Auto-generated docs** (Swagger/ReDoc)
- ✅ **Built-in validation** (Pydantic)
- 🔒 **Type safety** (catches bugs at dev time)
- 🚀 **Modern async** (no manual event loop management)
- 📦 **Smaller codebase** (less boilerplate)

### React Benefits
- 🧩 **Component reusability**
- 🔄 **Efficient re-rendering** (Virtual DOM)
- 🧪 **Easier testing** (Jest, React Testing Library)
- 📱 **Better mobile support**
- 🎨 **Rich ecosystem** (Material-UI, Ant Design, etc.)
- 💪 **TypeScript integration** (type safety)
- 🔧 **Better dev tools** (React DevTools)

### Combined Benefits
- **Better performance**: 30-50% faster overall
- **Better DX**: Hot reload, type safety, better errors
- **Better UX**: Smoother interactions, better loading states
- **Better maintainability**: Smaller files, clear structure
- **Better scalability**: Microservices-ready
- **Better hiring**: More developers know React/FastAPI

---

## Risk Mitigation

### Technical Risks

| Risk | Mitigation |
|------|------------|
| **Data migration issues** | Use same database, no migration needed |
| **Breaking changes** | Parallel operation, gradual rollout |
| **Performance regression** | Load testing before full rollout |
| **Feature parity gaps** | Comprehensive testing checklist |
| **Authentication issues** | JWT with same secret, seamless transition |

### Business Risks

| Risk | Mitigation |
|------|------------|
| **User disruption** | Zero-downtime deployment |
| **Revenue loss** | Maintain old system until proven |
| **Team velocity** | Incremental migration, no big bang |
| **Budget overrun** | Fixed timeline, clear phases |

---

## Cost Estimate

### Development Time
- **Phase 1** (Cleanup): 1-2 months
- **Phase 2** (FastAPI): 2 months
- **Phase 3** (React): 2-3 months
- **Phase 4** (Parallel): 1 month
- **Phase 5** (Deprecate): 1 month

**Total**: 7-9 months (1 full-time developer)

### Infrastructure Costs
- No additional costs (same database, same servers)
- May need staging environment: +$50/month

---

## Success Criteria

✅ **Performance**: 30%+ improvement in response times
✅ **Stability**: < 0.1% error rate
✅ **User Satisfaction**: No complaints about new UI
✅ **Developer Productivity**: 50% faster feature development
✅ **Code Quality**: 80%+ test coverage
✅ **Documentation**: 100% API documented

---

## Next Steps (Immediate)

### This Week
1. ✅ Complete critical bug fixes (DONE)
2. ⏳ Test fixes in Docker (IN PROGRESS)
3. ⏳ Deploy to production

### Next Week
1. Start Phase 1.1: Refactor app.py into modules
2. Add type hints to existing functions
3. Create Pydantic schemas

### This Month
1. Complete Phase 1 cleanup
2. Write comprehensive tests
3. Document current API endpoints

---

## Conclusion

This migration is **feasible and low-risk** because:

1. **Incremental approach** - No big bang rewrite
2. **Reusable components** - SQLAlchemy models, business logic, D3 charts
3. **Parallel operation** - Can test before fully committing
4. **Type safety** - Pydantic works in both Flask and FastAPI
5. **Clear benefits** - Faster, more maintainable, better DX

**Recommendation**: Start Phase 1 cleanup now. The refactoring will improve the current system AND make migration easier later.

---

**Questions? Let's discuss the roadmap and prioritize phases.**
