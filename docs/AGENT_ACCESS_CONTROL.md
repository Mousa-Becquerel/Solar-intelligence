# Agent Access Control System

## Overview

The Agent Access Control system provides fine-grained control over which users can access specific AI agents in the Solar Intelligence platform. This system combines plan-based access control with user-specific whitelisting for maximum flexibility.

## Key Features

✅ **Plan-Based Access** - Control agent access by user subscription tier (Free, Premium, Max)
✅ **User Whitelisting** - Grant specific users access to agents regardless of their plan
✅ **Global Agent Toggle** - Enable/disable agents entirely
✅ **Expiring Access** - Set expiration dates for whitelist entries
✅ **Audit Trail** - Track who granted access and when
✅ **Backward Compatible** - Agents without configuration are accessible by default

## Architecture

### Database Schema

#### `agent_access` Table
Stores global configuration for each agent:
- `agent_type` (unique): Identifier for the agent (e.g., 'market', 'price')
- `required_plan`: Minimum plan level required ('free', 'premium', 'max', 'admin')
- `is_enabled`: Global on/off switch for the agent
- `description`: Description of access requirements
- `created_at`, `updated_at`: Timestamps

#### `agent_whitelist` Table
Stores user-specific access grants:
- `agent_type`: Which agent the whitelist applies to
- `user_id`: User receiving special access
- `granted_by`: Admin who granted access
- `granted_at`: When access was granted
- `expires_at`: Optional expiration date
- `is_active`: Active/inactive flag
- `reason`: Why access was granted

### Plan Hierarchy

```
free (0) < premium (1) < max (2) < admin (3)
```

Users with a higher plan level can access agents requiring lower plan levels.

## Implementation

### 1. Database Migration

Run the migration script to create the tables and seed default configurations:

```bash
python migrations/add_agent_access_control.py
```

This will:
1. Create `agent_access` and `agent_whitelist` tables
2. Seed default configurations for all agents
3. Set recommended access levels based on agent complexity

### 2. Default Configuration

The migration sets these default access levels:

| Agent | Required Plan | Reasoning |
|-------|--------------|-----------|
| Market Intelligence | Free | Core feature, available to all |
| Technology Knowledge | Free | Educational, available to all |
| News & Updates | Free | Keep users informed |
| Price Analytics | Premium | Advanced analytics |
| Digitalization Trends | Premium | Specialized insights |
| Forecasting | Premium | Advanced predictive features |
| Permitting & Compliance | Premium | Complex regulatory data |
| O&M | Max | Enterprise-level operations |
| System Design | Max | Professional design tools |

You can modify these defaults based on your business model.

### 3. Access Check Flow

When a user attempts to access an agent:

```
1. Is agent globally enabled? → No → DENY
2. Is user an admin? → Yes → ALLOW
3. Is user in whitelist (active, not expired)? → Yes → ALLOW
4. Does user's plan meet required_plan? → Yes → ALLOW
5. Otherwise → DENY with upgrade message
```

### 4. Backend Integration

The system is automatically integrated at:

- **Route Level** - [app/routes/chat.py:143-152](app/routes/chat.py#L143-L152)
  ```python
  # Check if user has access before hiring agent
  can_access, reason = AgentAccessService.can_user_access_agent(current_user, agent_type)
  if not can_access:
      return jsonify({'error': reason, 'requires_upgrade': True}), 403
  ```

- **Service Layer** - [app/services/agent_access_service.py](app/services/agent_access_service.py)
  - `can_user_access_agent()` - Check if user has access
  - `get_user_accessible_agents()` - Get all agents with access status
  - `grant_user_access()` - Add user to whitelist
  - `revoke_user_access()` - Remove from whitelist
  - `update_agent_config()` - Modify agent settings

### 5. Admin Interface

Admin routes for managing agent access: [app/routes/admin.py:300-447](app/routes/admin.py#L300-L447)

**Available endpoints:**

- `GET /admin/agent-access` - Agent access management page
- `GET /admin/agent-access/<agent_type>/config` - Get agent configuration
- `POST /admin/agent-access/<agent_type>/update` - Update agent settings
- `POST /admin/agent-access/<agent_type>/whitelist` - Add user to whitelist
- `DELETE /admin/agent-access/<agent_type>/whitelist/<user_id>` - Remove from whitelist

## Usage Examples

### Check if User Can Access Agent

```python
from app.services.agent_access_service import AgentAccessService

can_access, reason = AgentAccessService.can_user_access_agent(user, 'price')

if can_access:
    # Allow access
    pass
else:
    # Show upgrade message: reason
    print(reason)  # "This agent requires a Premium plan or higher"
```

### Get All Agents with Access Status

```python
agents = AgentAccessService.get_user_accessible_agents(user)

for agent in agents:
    print(f"{agent['agent_type']}: {agent['can_access']}")
    if not agent['can_access']:
        print(f"  Reason: {agent['access_reason']}")
    if agent['is_whitelisted']:
        print(f"  User has special access!")
```

### Grant User Access (Whitelist)

```python
from datetime import datetime, timedelta

success, error = AgentAccessService.grant_user_access(
    agent_type='price',
    user_id=123,
    granted_by_id=current_user.id,  # Admin granting access
    expires_at=datetime.utcnow() + timedelta(days=30),  # 30-day trial
    reason='30-day trial for enterprise customer'
)

if success:
    print("Access granted!")
else:
    print(f"Error: {error}")
```

### Revoke User Access

```python
success, error = AgentAccessService.revoke_user_access(
    agent_type='price',
    user_id=123
)
```

### Update Agent Configuration

```python
success, error = AgentAccessService.update_agent_config(
    agent_type='price',
    required_plan='max',  # Upgrade to Max plan requirement
    is_enabled=True,
    description='Premium pricing analytics - Requires Max plan'
)
```

### Get Whitelisted Users for Agent

```python
users = AgentAccessService.get_whitelisted_users('price')

for user_info in users:
    print(f"{user_info['full_name']} ({user_info['username']})")
    print(f"  Granted: {user_info['granted_at']}")
    print(f"  Expires: {user_info['expires_at'] or 'Never'}")
    print(f"  Reason: {user_info['reason']}")
```

## Admin Workflows

### Scenario 1: Grant Trial Access to Free User

A free user wants to try the Premium "Price Analytics" agent:

1. Admin goes to `/admin/agent-access`
2. Selects "Price Analytics" agent
3. Clicks "Add User to Whitelist"
4. Enters user email/ID
5. Sets expiration date (e.g., 14 days)
6. Adds reason: "14-day trial for evaluation"
7. User can now access the agent until expiration

### Scenario 2: Make Agent Premium-Only

Convert a free agent to premium:

1. Admin goes to `/admin/agent-access`
2. Selects the agent
3. Changes "Required Plan" from "Free" to "Premium"
4. Updates description
5. All free users lose access immediately (unless whitelisted)

### Scenario 3: Temporarily Disable Agent

Disable an agent for maintenance:

1. Admin goes to `/admin/agent-access`
2. Selects the agent
3. Toggles "Enabled" to OFF
4. All users (including admins) see agent as unavailable

## Security Considerations

✅ **Authorization Checks** - All routes protected with `@admin_required` decorator
✅ **Fail-Safe Defaults** - Agents without configuration remain accessible (backward compatibility)
✅ **Admin Bypass** - Admins always have access (for testing/support)
✅ **Input Validation** - Plan types, dates, and user IDs validated
✅ **Audit Trail** - Track who granted access and when
✅ **Rate Limiting** - Admin endpoints rate-limited to prevent abuse

## Best Practices

### For Admins

1. **Document Whitelist Reasons** - Always provide a reason when whitelisting users
2. **Set Expiration Dates** - Use expiring access for trials/temporary grants
3. **Review Regularly** - Periodically audit whitelist entries
4. **Test Changes** - Use a test account to verify access changes
5. **Communicate Changes** - Notify users before changing agent access levels

### For Developers

1. **Check Access Early** - Validate access before processing expensive operations
2. **Provide Clear Messages** - Return helpful error messages with upgrade paths
3. **Handle Gracefully** - Degrade features gracefully for users without access
4. **Log Access Denials** - Track access denials for business intelligence
5. **Cache Access Checks** - Consider caching for frequently accessed agents

## Troubleshooting

### Agent Not Appearing in Whitelist UI

**Cause:** Agent not in `agent_access` table
**Solution:** Re-run migration or manually add agent configuration

### User Has Plan But Can't Access

**Check:**
1. Is agent enabled globally?
2. Does user's plan meet `required_plan`?
3. Are there any database errors in logs?

### Whitelist Not Working

**Check:**
1. Is whitelist entry active (`is_active = true`)?
2. Has it expired (`expires_at < now`)?
3. Is agent globally disabled?

### Admin Can't Access Agent

**This shouldn't happen!**
Admins bypass all access checks. If occurring:
1. Verify user role is actually 'admin'
2. Check database for corruption
3. Review authentication logs

## API Reference

See [app/services/agent_access_service.py](app/services/agent_access_service.py) for full API documentation.

## Database Queries

### Find all users with access to an agent

```sql
SELECT u.id, u.username, u.full_name, u.plan_type,
       CASE
         WHEN aw.id IS NOT NULL THEN 'Whitelisted'
         ELSE 'Plan-based'
       END as access_type
FROM user u
LEFT JOIN agent_whitelist aw ON u.id = aw.user_id
  AND aw.agent_type = 'price'
  AND aw.is_active = true
WHERE u.role = 'admin'
   OR aw.id IS NOT NULL
   OR u.plan_type IN ('premium', 'max');
```

### Find agents accessible to a specific user

```sql
SELECT aa.agent_type, aa.required_plan, aa.is_enabled,
       CASE
         WHEN u.role = 'admin' THEN true
         WHEN aw.id IS NOT NULL THEN true
         WHEN aa.required_plan = 'free' THEN true
         WHEN aa.required_plan = 'premium' AND u.plan_type IN ('premium', 'max') THEN true
         WHEN aa.required_plan = 'max' AND u.plan_type = 'max' THEN true
         ELSE false
       END as can_access
FROM agent_access aa
CROSS JOIN user u
LEFT JOIN agent_whitelist aw ON aa.agent_type = aw.agent_type
  AND aw.user_id = u.id
  AND aw.is_active = true
WHERE u.id = 123;  -- Replace with actual user ID
```

## Future Enhancements

Potential improvements for V2:

- [ ] Role-based access (e.g., "researcher" role gets specific agents)
- [ ] Usage quotas per agent (e.g., 100 queries/month for premium agents)
- [ ] Agent-specific pricing (e.g., $10/month for this agent)
- [ ] User-requested access workflow (request → approval → grant)
- [ ] Analytics dashboard for agent usage by plan tier
- [ ] Bulk whitelist operations (CSV upload)
- [ ] API tokens with agent-specific scopes

## Support

For questions or issues:
- Check logs in `app.log` for error details
- Review this documentation
- Contact the development team

---

**Last Updated:** 2025-01-04
**Version:** 1.0.0
