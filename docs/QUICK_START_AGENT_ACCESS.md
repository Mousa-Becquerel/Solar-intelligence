# Quick Start: Agent Access Control

## Setup (One-Time)

### 1. Run Database Migration

```bash
python migrations/add_agent_access_control.py
```

This creates the tables and sets up default agent configurations.

### 2. Verify Setup

Log in as admin and visit: `http://your-domain/admin/agent-access`

You should see all agents listed with their current access settings.

## Common Tasks

### Make an Agent Premium-Only

**Scenario:** You want to restrict the "Price Analytics" agent to Premium users only.

1. Go to `/admin/agent-access`
2. Find "Price Analytics" agent
3. Change "Required Plan" to "Premium"
4. Click "Save"

✅ Done! Only Premium/Max users can now hire this agent.

### Give a Free User Temporary Access

**Scenario:** A free user wants to try Premium features for 14 days.

1. Go to `/admin/agent-access`
2. Select the Premium agent (e.g., "Price Analytics")
3. Click "Whitelist User"
4. Enter user email: `user@example.com`
5. Set expiration: Today + 14 days
6. Add reason: "14-day trial"
7. Click "Grant Access"

✅ User can now access the agent for 14 days!

### Temporarily Disable an Agent

**Scenario:** Agent has bugs, needs to be taken offline for fixes.

1. Go to `/admin/agent-access`
2. Select the problematic agent
3. Toggle "Enabled" to OFF
4. Click "Save"

✅ Agent is now unavailable to all users (including admins see it as disabled).

### Remove User's Special Access

**Scenario:** Trial period ended, need to revoke access.

1. Go to `/admin/agent-access`
2. Select the agent
3. Click "Whitelisted Users"
4. Find the user in the list
5. Click "Remove"

✅ User loses special access (falls back to plan-based access).

## Access Logic Cheat Sheet

```
┌─────────────────────────────────────────┐
│ Can user access agent?                  │
├─────────────────────────────────────────┤
│ 1. Is agent disabled? → NO              │
│ 2. Is user admin? → YES                 │
│ 3. Is user whitelisted? → YES           │
│ 4. User plan >= required plan? → YES    │
│ 5. Otherwise → NO (show upgrade msg)    │
└─────────────────────────────────────────┘
```

## Plan Levels

```
Free (0) < Premium (1) < Max (2) < Admin (∞)
```

- Free user: Can access "Free" agents only
- Premium user: Can access "Free" + "Premium" agents
- Max user: Can access all agents
- Admin: Always has access (bypasses all checks)

## Example Configurations

### Free Tier Strategy
```
Market Intelligence: Free
News: Free
Technology: Free
Price Analytics: Premium (blocked)
O&M: Max (blocked)
```

### Freemium Strategy
```
Market Intelligence: Free (limited features)
Price Analytics: Premium
Forecasting: Premium
Design: Max
O&M: Max
```

### Enterprise Strategy
```
All basic agents: Free
Advanced agents: Whitelisted only
```

## Testing Your Configuration

1. Create a test user with Free plan
2. Log in as that user
3. Try to hire a Premium agent
4. Should see: "This agent requires a Premium plan or higher"
5. As admin, whitelist the test user
6. Test user can now hire the agent
7. Remove from whitelist
8. Test user blocked again

## Monitoring Access

### Check who has access to expensive agents:

```python
from app.services.agent_access_service import AgentAccessService

whitelisted = AgentAccessService.get_whitelisted_users('price')
print(f"{len(whitelisted)} users whitelisted for Price Analytics")

for user in whitelisted:
    print(f"  - {user['full_name']}: {user['reason']}")
    if user['expires_at']:
        print(f"    Expires: {user['expires_at']}")
```

### Audit all agent access:

```python
from models import AgentAccess

for agent in AgentAccess.query.all():
    print(f"{agent.agent_type}:")
    print(f"  Required plan: {agent.required_plan}")
    print(f"  Enabled: {agent.is_enabled}")
    print(f"  Whitelisted users: {len(AgentAccessService.get_whitelisted_users(agent.agent_type))}")
```

## Integration with Pricing

### Free Plan (0 agents)
```python
# In registration or plan update:
user.plan_type = 'free'  # Can access agents marked 'free'
```

### Premium Plan (3-5 agents)
```python
user.plan_type = 'premium'  # Can access 'free' + 'premium' agents
```

### Max Plan (all agents)
```python
user.plan_type = 'max'  # Can access everything
```

### Special Customer (custom agents)
```python
# Grant access to specific high-value agents
AgentAccessService.grant_user_access(
    agent_type='custom_enterprise_agent',
    user_id=customer.id,
    granted_by_id=admin.id,
    reason='Enterprise contract #12345'
)
```

## Safety Features

✅ **Admins always have access** - Can't lock yourself out
✅ **Graceful degradation** - Missing configs allow access (backward compatible)
✅ **Audit trail** - Track who granted access and why
✅ **Expiring access** - Trials automatically end
✅ **Rate limiting** - Prevent admin endpoint abuse

## Troubleshooting

### "Agent not found" error
→ Agent doesn't exist in `agent_access` table
→ Run migration or manually add configuration

### User has Premium but can't access
→ Check if agent is globally disabled
→ Verify required_plan setting
→ Review application logs

### Whitelist not working
→ Check if entry is active
→ Verify expiration date hasn't passed
→ Confirm agent is enabled

## Next Steps

1. **Run migration** to set up tables
2. **Review default configurations** in admin panel
3. **Adjust required plans** to match your pricing strategy
4. **Test with a free account** to verify access control
5. **Document your decisions** (which agents require which plans)

---

For detailed information, see [AGENT_ACCESS_CONTROL.md](AGENT_ACCESS_CONTROL.md)
