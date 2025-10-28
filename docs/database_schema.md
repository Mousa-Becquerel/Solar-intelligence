# Database Schema

## Tables

### User
Stores user account information with GDPR compliance fields.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key | Unique user identifier |
| username | String(80) | Unique, Not Null | Login username |
| password_hash | String(255) | Not Null | Hashed password |
| full_name | String(100) | Not Null | User's full name |
| role | String(50) | Default: 'user' | User role (admin/user) |
| created_at | DateTime | Default: UTC now | Account creation timestamp |
| is_active | Boolean | Default: True | Account active status |
| gdpr_consent_given | Boolean | Default: False, Not Null | GDPR consent flag |
| gdpr_consent_date | DateTime | Nullable | GDPR consent timestamp |
| terms_accepted | Boolean | Default: False, Not Null | Terms acceptance flag |
| terms_accepted_date | DateTime | Nullable | Terms acceptance timestamp |
| marketing_consent | Boolean | Default: False, Not Null | Marketing consent flag |
| marketing_consent_date | DateTime | Nullable | Marketing consent timestamp |
| privacy_policy_version | String(10) | Default: '1.0' | Accepted privacy policy version |
| terms_version | String(10) | Default: '1.0' | Accepted terms version |

### Conversation
Stores chat conversation sessions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key | Unique conversation identifier |
| title | String(256) | Nullable | Conversation title |
| created_at | DateTime | Default: UTC now | Conversation creation timestamp |
| agent_type | String(16) | Default: 'market' | Agent type (market/price/om) |
| user_id | Integer | Foreign Key (user.id), Not Null | Owner user ID |

**Relationships:**
- `messages`: One-to-many with Message table
- `user`: Many-to-one with User table

### Message
Stores individual messages within conversations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key | Unique message identifier |
| conversation_id | Integer | Foreign Key (conversation.id), Not Null | Parent conversation ID |
| sender | String(16) | Nullable | Message sender ('user' or 'bot') |
| content | Text | Nullable | Message content |
| timestamp | DateTime | Default: UTC now | Message timestamp |

**Relationships:**
- `conversation`: Many-to-one with Conversation table

### Waitlist
Stores email addresses for the waitlist feature.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key | Unique waitlist entry identifier |
| email | String(120) | Unique, Not Null, Indexed | Email address |
| created_at | DateTime | Default: UTC now | Subscription timestamp |
| notified | Boolean | Default: False | Notification sent flag |
| notified_at | DateTime | Nullable | Notification timestamp |
| ip_address | String(45) | Nullable | Subscriber IP address (IPv6 support) |
| user_agent | String(256) | Nullable | Subscriber user agent string |

### Feedback (New)
Stores user feedback submissions about the application.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key | Unique feedback identifier |
| user_id | Integer | Foreign Key (user.id), Nullable | Submitter user ID (null for anonymous) |
| rating | Integer | Not Null | Rating score (1-5) |
| feedback_text | Text | Nullable | Optional feedback text |
| allow_followup | Boolean | Default: False | Permission for follow-up contact |
| created_at | DateTime | Default: UTC now | Feedback submission timestamp |
| ip_address | String(45) | Nullable | Submitter IP address |
| user_agent | String(256) | Nullable | Submitter user agent string |

**Relationships:**
- `user`: Many-to-one with User table

## Indexes

- `user.username` - Unique index for fast login lookups
- `waitlist.email` - Unique index for email validation
- `conversation.user_id` - Foreign key index for user conversations
- `message.conversation_id` - Foreign key index for conversation messages
- `feedback.user_id` - Foreign key index for user feedback

## Migration Notes

The database schema is automatically updated on application startup via `db.create_all()` in app.py (lines 586-595).

For production deployments:
1. PostgreSQL: Tables are created if they don't exist, existing tables are preserved
2. SQLite: Migration logic handles adding missing GDPR columns to existing databases

The Feedback table was added in the latest update and will be automatically created on next application restart.
