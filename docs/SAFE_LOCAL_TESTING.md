# Safe Local Testing Guide

## ⚠️ CRITICAL: Your Current Setup

**IMPORTANT DISCOVERY:**
Both your local app and AWS deployed app are connected to the **SAME production database**!

```
Current .env file:
DATABASE_URL=postgresql://solar_admin:datahub1@solar-intelligence-db...
                          ↓
                  AWS RDS PostgreSQL
                          ↑
Both local and AWS app connect here!
```

## What This Means

### Current Situation
- ✅ Your **code changes** are separate (local vs AWS)
- ⚠️ Your **database** is shared (same data for both)
- ⚠️ Running migrations locally = affects production database
- ⚠️ Creating test data locally = appears in production

### Implications
1. **Testing locally affects production** - any database changes are live
2. **Migration script affects production** - running it locally runs it on production DB
3. **Test users you create** - will appear in production

---

## Safe Testing Options

### Option 1: Use Local SQLite Database (RECOMMENDED for Testing)

**What**: Test with a completely separate local database

**How**:

1. **Rename your current .env to .env.production**
   ```bash
   cd "c:\Users\MousaSondoqah-Becque\OneDrive - ICARES\Desktop\Solar_intelligence\code_inter\Full_data_DH_bot"

   # Backup production config
   cp .env .env.production

   # Use local config
   cp .env.local .env
   ```

2. **Start app with local database**
   ```bash
   python app.py
   ```

3. **Test everything safely**
   - Create test users
   - Send queries
   - Test migrations
   - Nothing affects production!

4. **When done testing, switch back**
   ```bash
   cp .env.production .env
   ```

**Pros:**
- ✅ 100% safe - can't affect production
- ✅ Fast testing - no network latency
- ✅ Can break things without worry
- ✅ Can test migrations safely

**Cons:**
- ❌ Different database engine (SQLite vs PostgreSQL)
- ❌ No real production data to test with

---

### Option 2: Read-Only Testing with Production Database

**What**: Test code changes without making database changes

**How**:

1. **Keep current .env** (production database)

2. **Only test read operations**
   - Login (existing users only)
   - View conversations
   - Read messages
   - View stats

3. **DON'T run:**
   - Migration scripts
   - User creation
   - Database writes
   - Destructive operations

**Pros:**
- ✅ Test with real production data
- ✅ Test production database connection
- ✅ Verify queries work

**Cons:**
- ⚠️ Must be very careful not to write data
- ⚠️ Can't fully test new features
- ⚠️ Risk of accidental changes

---

### Option 3: Create Staging Database

**What**: Set up a separate staging database on AWS RDS

**How**:

1. **Create RDS snapshot** of production database
2. **Restore snapshot** to new RDS instance (staging)
3. **Update .env.local** with staging database URL
4. **Test on staging** before production

**Pros:**
- ✅ Identical to production (same engine, similar data)
- ✅ Safe testing environment
- ✅ Can test migrations safely
- ✅ Can break things without worry

**Cons:**
- ❌ Costs money (RDS instance)
- ❌ Takes time to set up
- ❌ Need to keep data in sync

---

## Recommended Workflow

### For Code Changes (Safe Now)

```bash
# 1. Use local SQLite for testing
cp .env.local .env

# 2. Test your code changes
python app.py
# Visit http://localhost:5002
# Create test user, test features

# 3. Once satisfied, prepare for deployment
cp .env.production .env

# 4. Deploy code to AWS (no database changes yet)
git add .
git commit -m "Security and performance improvements"
git push
```

### For Database Migrations (Evening Only)

```bash
# ONLY DO THIS IN THE EVENING!

# 1. Ensure using production database
cp .env.production .env

# 2. Backup production database first!
# (Follow DATABASE_MIGRATION_PLAN.md)

# 3. Run migration
python scripts/add_database_indexes.py

# 4. Verify and monitor
```

---

## Quick Reference: Which .env to Use

| Scenario | Use This File | Database |
|----------|---------------|----------|
| **Local testing** | `.env.local` | Local SQLite (safe) |
| **Production testing** | `.env.production` | AWS RDS (careful!) |
| **Migration (evening)** | `.env.production` | AWS RDS (with backup!) |
| **AWS deployment** | Environment vars set in AWS | AWS RDS |

---

## Commands Cheat Sheet

### Switch to Local Testing
```bash
cp .env.local .env
python app.py
# Safe to test everything!
```

### Switch to Production
```bash
cp .env.production .env
python app.py
# BE CAREFUL - affects production!
```

### Check Current Database
```bash
# Look at your current .env
grep DATABASE_URL .env

# If you see:
# sqlite:///local_test.db  → Local (safe)
# postgresql://solar-intelligence-db  → Production (careful!)
```

### Create Test Admin User (Local Only)
```bash
# Make sure using .env.local first!
export ADMIN_EMAIL=admin@test.com
export ADMIN_PASSWORD=TestPassword123!
python app.py
```

---

## What's Safe to Run Now

### ✅ Safe with Production Database (.env.production)

**Code deployments** (don't touch database):
- Deploying security fixes (XSS, admin password)
- Deploying timeout changes
- Deploying frontend changes
- Deploying agent changes
- Running the app normally

### ⚠️ DO NOT RUN with Production Database

**Database operations** (wait until evening):
- `python scripts/add_database_indexes.py`
- Any migration scripts
- Database schema changes
- Bulk data operations

### ✅ Safe with Local Database (.env.local)

**Everything!** Including:
- Testing migrations
- Creating test users
- Experimenting with features
- Breaking things
- Learning the system

---

## Testing Your Changes Safely

### Test Security Fixes

```bash
# 1. Switch to local
cp .env.local .env

# 2. Start app
python app.py

# 3. Test XSS protection
# - Create user
# - Send message with HTML: <script>alert('test')</script>
# - Should be sanitized (no alert)

# 4. Test admin creation
export ADMIN_EMAIL=admin@test.com
export ADMIN_PASSWORD=TestPass123!
# Restart app
python app.py
# Login as admin@test.com
```

### Test Performance

```bash
# 1. Use local database
cp .env.local .env

# 2. Run migration to create indexes
python scripts/add_database_indexes.py

# 3. Create test data
# - Register users
# - Create conversations
# - Send queries

# 4. Check query speed
# Should be noticeably faster!
```

---

## Evening Migration Checklist

When you're ready to run the database migration:

- [ ] It's evening (low traffic time)
- [ ] Using production config: `cp .env.production .env`
- [ ] Production database backed up
- [ ] AWS RDS snapshot taken
- [ ] Tested migration on local database first
- [ ] Read DATABASE_MIGRATION_PLAN.md
- [ ] Team notified (if applicable)
- [ ] Ready to monitor for 30 minutes after

Then run:
```bash
python scripts/add_database_indexes.py
```

---

## Summary

**Right Now:**
1. ✅ Use `.env.local` for testing (safe SQLite database)
2. ✅ Test all code changes locally
3. ✅ Deploy code changes to AWS (they're safe)
4. ⏳ Wait until evening for database migration

**This Evening:**
1. 💾 Backup production database
2. 🔄 Switch to `.env.production`
3. 🚀 Run migration script
4. 👀 Monitor and verify

**Key Insight:**
Your local app is currently pointed at the production database. Always check which `.env` file you're using before running database operations!

---

## Questions?

### Q: Can I test locally right now?
**A:** Yes! Use `.env.local` with SQLite. 100% safe.

### Q: Will my code changes affect production?
**A:** No, code is separate. Database is shared.

### Q: When should I run the migration?
**A:** This evening, with production database, after backup.

### Q: What if I accidentally run migration now?
**A:** It would affect production database immediately. That's why we created `.env.local`!

### Q: How do I know which database I'm using?
**A:** Check `grep DATABASE_URL .env`
- `sqlite:///` = Local (safe)
- `postgresql://` = Production (careful!)

---

**Stay safe! Use `.env.local` for testing, `.env.production` for migrations (evening only).**
