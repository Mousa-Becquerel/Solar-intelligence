# Solar Intelligence Platform - Database Schema Overview

## 📊 Database Tables & Data Storage

### **Core Tables**

#### 1. **`users` Table**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,     -- Email address (used for login)
    password_hash VARCHAR(255) NOT NULL,     -- Bcrypt hashed password
    full_name VARCHAR(100) NOT NULL,         -- Display name
    role VARCHAR(50) DEFAULT 'user',         -- 'admin' or 'user'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

**Sample Data:**
- Admin users (admins can create/manage users)
- Regular users (can chat with AI agents)
- Predefined system users (created on startup)

#### 2. **`conversations` Table**
```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    title VARCHAR(256),                      -- Auto-generated or custom title
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    agent_type VARCHAR(16) DEFAULT 'market', -- 'market', 'module_prices', 'news'
    user_id INTEGER NOT NULL,               -- Foreign key to users.id
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**Sample Data:**
- Market analysis conversations
- Module price analysis conversations
- News research conversations
- Each user can have multiple conversations
- Conversations maintain agent context/memory

#### 3. **`messages` Table**
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    conversation_id INTEGER NOT NULL,        -- Foreign key to conversations.id
    sender VARCHAR(16),                      -- 'user' or 'bot'
    content TEXT,                           -- JSON-encoded message content
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
```

**Sample Data Structure:**
The `content` field stores JSON with different message types:

### **Message Content Types**

#### **1. Text Messages**
```json
{
    "type": "string",
    "value": "What is the solar capacity in Germany?",
    "comment": null
}
```

#### **2. Interactive Charts (D3/JSON Plots)**
```json
{
    "type": "interactive_chart",
    "value": "Solar Capacity by Country (2020-2024)",
    "plot_data": {
        "plot_type": "stacked_bar",
        "title": "Solar Capacity by Country (2020-2024)",
        "x_axis_label": "Year",
        "y_axis_label": "Capacity (GW)",
        "unit": "GW",
        "data": [
            {
                "year": 2020,
                "Germany": 53.7,
                "France": 11.1,
                "Italy": 21.6
            },
            {
                "year": 2021,
                "Germany": 59.2,
                "France": 13.1,
                "Italy": 22.7
            }
        ],
        "series_info": [
            {"name": "Germany", "color": "#1f77b4"},
            {"name": "France", "color": "#ff7f0e"},
            {"name": "Italy", "color": "#2ca02c"}
        ],
        "notes": ["Data source: European PV market analysis", "Includes all connection types"]
    },
    "comment": null
}
```

#### **3. Data Tables**
```json
{
    "type": "table",
    "value": "Top 5 Countries by Solar Capacity",
    "table_data": [
        {"Country": "Germany", "Capacity_GW": 59.2, "Year": 2021},
        {"Country": "Italy", "Capacity_GW": 22.7, "Year": 2021},
        {"Country": "France", "Capacity_GW": 13.1, "Year": 2021}
    ],
    "full_data": [...],  // Complete dataset
    "comment": null
}
```

#### **4. Static Charts (Legacy)**
```json
{
    "type": "chart",
    "value": "Module Price Trends Analysis",
    "artifact": "/static/plots/chart_20241215_143022.png",
    "comment": null
}
```

### **Data Volume & Usage Patterns**

#### **Typical Storage Requirements:**

1. **Text Messages**: ~100-500 bytes each
2. **Interactive Charts**: ~5-50 KB each (depends on data points)
3. **Data Tables**: ~1-10 KB each (depends on rows)
4. **Static Charts**: Reference only (~200 bytes), actual files stored in filesystem

#### **Sample Data Volumes:**
- **10 users, 50 conversations each, 20 messages per conversation**:
  - Users: ~1 KB
  - Conversations: ~50 KB  
  - Messages: ~5-50 MB (depending on chart complexity)
  - **Total: ~50-100 MB for moderate usage**

#### **Growth Patterns:**
- **Messages grow linearly** with user activity
- **Chart data can be significant** (each market analysis chart ~10-30 KB)
- **Conversation titles** auto-generated from first user message
- **User data is minimal** (just authentication + basic profile)

### **Data Relationships**

```
users (1) ──────────── (many) conversations
                              │
                              │ (1)
                              │
                              └─── (many) messages
```

### **Query Patterns**

#### **Common Queries:**
1. **Load user conversations**: `SELECT * FROM conversations WHERE user_id = ? ORDER BY created_at DESC`
2. **Load conversation messages**: `SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC`
3. **User authentication**: `SELECT * FROM users WHERE username = ?`
4. **Conversation statistics**: `SELECT COUNT(*) FROM conversations WHERE user_id = ?`

#### **Performance Considerations:**
- **Index on `user_id`** in conversations table (frequent filtering)
- **Index on `conversation_id`** in messages table (frequent joins)
- **Index on `username`** in users table (login queries)
- **Index on `created_at`** for chronological sorting

### **Data Retention & Cleanup**

#### **Current Policy:**
- **No automatic cleanup** (all data preserved)
- **User can delete conversations** (cascades to messages)
- **Admin can manage users** and their data

#### **Recommendations for Production:**
- **Implement data retention** policies (e.g., 1-2 years)
- **Archive old conversations** to reduce active database size
- **Compress chart data** for long-term storage
- **Monitor message content size** to prevent abuse

### **Security Considerations**

#### **Sensitive Data:**
- **User passwords**: Bcrypt hashed (secure)
- **API keys**: Should be in environment variables, NOT in database
- **User conversations**: Private per user, isolated by user_id
- **Chart data**: May contain business-sensitive market data

#### **Access Controls:**
- **User isolation**: Users can only access their own conversations
- **Admin privileges**: Can view user lists, but not conversation content
- **Authentication required**: All routes except landing page
- **CSRF protection**: Enabled for all forms

### **Backup Requirements**

#### **Critical Data:**
1. **User accounts** (authentication, profiles)
2. **Conversation history** (user's analysis work)
3. **Chart configurations** (expensive to regenerate)

#### **Less Critical:**
1. **Message timestamps** (can be regenerated)
2. **Static chart files** (can be regenerated from plot_data)

#### **Backup Strategy:**
- **Daily database dumps** (SQL format)
- **Weekly full backups** (including static files)
- **Point-in-time recovery** capability for production

### **Migration Considerations**

#### **From SQLite to PostgreSQL:**
- **Schema compatible** (minor type adjustments needed)
- **Data export/import** straightforward
- **No application code changes** required (SQLAlchemy abstraction)

#### **Scaling Considerations:**
- **Read replicas** for conversation loading
- **Connection pooling** (already configured)
- **Table partitioning** by user_id for very large deployments
- **Separate chart data** storage (S3) for massive datasets

This schema supports the current Solar Intelligence platform and is designed to scale with growing user adoption and data complexity.