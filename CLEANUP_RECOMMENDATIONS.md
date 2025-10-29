# 🧹 Cleanup Recommendations - Unnecessary Files

**Date:** October 29, 2025
**Current State:** Many obsolete files taking up space

---

## 📊 Summary

| Category | Count | Action |
|----------|-------|--------|
| **Test Files** | 7 | Move to tests/ folder |
| **Status MD Files** | 12 | Archive or delete |
| **Old Config Files** | 3 | Delete (using refactored version) |
| **Generated Plots** | 466 | Clean up old plots |
| **Old Python Scripts** | 3+ | Archive or delete |

---

## 🗂️ Files to Clean Up

### 1. **Test Files (Move to `tests/` folder)**

```
test_blueprints.py
test_new_config.py
test_refactored_integration.py
test_schemas.py
test_services.py
test_simple_integration.py
verify_refactored_app.py
```

**Action:** Move to `tests/` folder for proper organization

**Command:**
```bash
mkdir -p tests
mv test_*.py tests/
mv verify_refactored_app.py tests/
```

---

### 2. **Status/Fix Documentation Files (Archive or Delete)**

These are historical status files documenting fixes that are now complete:

```
CODE_CLEANUP_COMPLETED.md          # Old app.py cleanup
CODE_CLEANUP_PLAN.md                # Obsolete planning doc
CODE_IMPROVEMENTS_COMPLETE.md       # Historical
CSS_MODULARIZATION_COMPLETE.md      # Historical
DUPLICATE_MESSAGE_FIX.md            # Bug fix doc
HTTP2_FIX_APPLIED.md               # Historical fix
HTTP2_PROTOCOL_ERROR_FIX.md        # Duplicate
INTEGRATION_STATUS.md              # Obsolete
MAIN_JS_CODE_REVIEW_FIXES.md       # Historical
PENDING_USERS_FIX.md               # Bug fix doc
PLOTTING_AGENT_MODEL_CHANGE.md     # Historical
PRICE_AGENT_TABLE_FIX.md           # Bug fix doc
RUN_INTEGRATION_TEST.md            # Test instructions
SESSION_CLEANUP_SUMMARY.md         # Historical
VISIBILITY_FIX.md                  # Bug fix doc
```

**Action:** Move to `docs/archive/` for reference

**Command:**
```bash
mkdir -p docs/archive
mv *_FIX.md *_COMPLETE.md *_SUMMARY.md *_STATUS.md docs/archive/
```

---

### 3. **Obsolete Python Files**

#### **app.py** (147KB - MONOLITHIC VERSION)
❌ **DELETE** - Replaced by refactored architecture
- Old monolithic file (2,600+ lines)
- Replaced by `app/` folder structure
- Using `run_refactored.py` instead

#### **app_config_bridge.py**
❓ **REVIEW** - Check if still needed for backwards compatibility

#### **longer_market_agent_flow.py**
❓ **REVIEW** - Appears to be experimental/alternative version

---

### 4. **Generated Plot Files**

**466 total PNG files** across two locations:

```
static/plots/     → 275 PNG files  (dynamically generated)
exports/charts/   → 191 PNG files  (agent exports)
```

**Issue:** These accumulate over time and aren't cleaned up

**Recommendations:**

**Option A: Automated Cleanup Script**
```python
# cleanup_old_plots.py
import os
from datetime import datetime, timedelta

def cleanup_old_plots(directory, days_old=7):
    """Delete plot files older than X days"""
    now = datetime.now()
    count = 0

    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if filename.endswith('.png'):
            file_age = now - datetime.fromtimestamp(os.path.getmtime(filepath))
            if file_age > timedelta(days=days_old):
                os.remove(filepath)
                count += 1

    return count

# Run cleanup
removed_static = cleanup_old_plots('static/plots', days_old=7)
removed_exports = cleanup_old_plots('exports/charts', days_old=7)
print(f"Removed {removed_static + removed_exports} old plot files")
```

**Option B: Manual Cleanup**
```bash
# Delete all plots older than 7 days
find static/plots -name "*.png" -mtime +7 -delete
find exports/charts -name "*.png" -mtime +7 -delete
```

**Option C: Add to .gitignore**
```
# .gitignore
static/plots/*.png
exports/charts/*.png
```

---

### 5. **Other Utility Files to Review**

#### **plotting_agent_prompt_condensed.txt**
- Appears to be a prompt template
- Should be in `prompts/` or `docs/` folder

#### **ppt_gen.py**
- PowerPoint generation utility
- Keep if used, otherwise archive

#### **request_context.py**
- Context management utility
- Likely still needed (keep)

#### **rebuild_docker.sh, update_dependencies.sh**
- Utility scripts (keep)

#### **runtime.txt**
- Heroku/deployment config (keep if deploying there)

---

## 🎯 Recommended Folder Structure After Cleanup

```
Full_data_DH_bot/
├── app/                          # Refactored application ✅
├── templates/                    # Jinja2 templates ✅
├── static/                       # CSS, JS, images ✅
├── tests/                        # All test files 📦 NEW
│   ├── test_blueprints.py
│   ├── test_services.py
│   └── verify_refactored_app.py
├── docs/                         # Documentation ✅
│   ├── REFACTORED_ARCHITECTURE.md
│   ├── MODULAR_ARCHITECTURE_COMPLETE.md
│   └── archive/                  # Historical docs 📦 NEW
│       ├── CODE_CLEANUP_COMPLETED.md
│       ├── DUPLICATE_MESSAGE_FIX.md
│       └── ... (all fix/status docs)
├── scripts/                      # Utility scripts ✅
│   ├── cleanup_old_plots.py     # 📦 NEW
│   ├── rebuild_docker.sh
│   └── update_dependencies.sh
├── exports/                      # Generated exports ✅
│   ├── charts/                  # Cleaned regularly
│   └── data/
├── datasets/                     # Data files ✅
├── models.py                     # Database models ✅
├── run_refactored.py            # Application entry ✅
├── requirements.txt              # Dependencies ✅
├── pyproject.toml               # Poetry config ✅
├── docker-compose.yml           # Docker config ✅
├── Dockerfile                    # Docker build ✅
├── README.md                     # Main readme ✅
└── .gitignore                   # Git ignore rules ✅
```

---

## 📋 Cleanup Checklist

### Phase 1: Organize Test Files
- [ ] Create `tests/` folder
- [ ] Move all `test_*.py` files to `tests/`
- [ ] Move `verify_refactored_app.py` to `tests/`
- [ ] Update any import paths if needed

### Phase 2: Archive Documentation
- [ ] Create `docs/archive/` folder
- [ ] Move historical status/fix docs to archive
- [ ] Keep only current docs in root

### Phase 3: Remove Obsolete Code
- [ ] **BACKUP first!**
- [ ] Delete `app.py` (replaced by `app/` folder)
- [ ] Review and remove `app_config_bridge.py` if unused
- [ ] Review `longer_market_agent_flow.py`

### Phase 4: Clean Up Generated Files
- [ ] Create `scripts/cleanup_old_plots.py`
- [ ] Run initial cleanup (delete plots >7 days old)
- [ ] Add cron job or scheduled task for automatic cleanup
- [ ] Update `.gitignore` to exclude plot files

### Phase 5: Organize Remaining Files
- [ ] Move `plotting_agent_prompt_condensed.txt` to `docs/prompts/`
- [ ] Review `ppt_gen.py` usage
- [ ] Ensure all scripts are in `scripts/` folder

---

## 🚀 Quick Cleanup Commands

### Safe Cleanup (Moves to archive)
```bash
# Create folders
mkdir -p tests docs/archive docs/prompts

# Move test files
mv test_*.py verify_refactored_app.py tests/

# Move historical docs
mv *_FIX.md *_COMPLETE.md *_SUMMARY.md *_STATUS.md docs/archive/

# Move prompt files
mv plotting_agent_prompt_condensed.txt docs/prompts/

# Clean old plots (>7 days)
find static/plots -name "*.png" -mtime +7 -exec rm {} \;
find exports/charts -name "*.png" -mtime +7 -exec rm {} \;
```

### Aggressive Cleanup (Deletes permanently)
```bash
# ⚠️ WARNING: This deletes files permanently

# Delete obsolete code
rm app.py
rm app_config_bridge.py
rm longer_market_agent_flow.py

# Delete all old plots
rm static/plots/*.png
rm exports/charts/*.png

# Delete old status docs
rm *_FIX.md *_COMPLETE.md *_SUMMARY.md *_STATUS.md
```

---

## 📈 Expected Results

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Root Python files** | ~20 | ~8 | 60% reduction |
| **Root MD files** | ~15 | ~3 | 80% reduction |
| **PNG files** | 466 | <50 | 90% reduction |
| **Test organization** | Scattered | In tests/ | Organized |
| **Docs organization** | Mixed | Structured | Clear |

---

## ⚠️ Important Notes

1. **Backup First!**
   ```bash
   # Create backup before cleanup
   tar -czf backup_$(date +%Y%m%d).tar.gz .
   ```

2. **Test After Cleanup**
   - Verify Docker still builds: `docker-compose up --build`
   - Run tests: `pytest tests/`
   - Check imports aren't broken

3. **Git Commit Strategy**
   ```bash
   # Commit cleanup in logical chunks
   git add tests/
   git commit -m "refactor: organize test files into tests/ folder"

   git add docs/archive/
   git commit -m "docs: archive historical status documents"

   git rm app.py
   git commit -m "refactor: remove obsolete monolithic app.py"
   ```

4. **`.gitignore` Updates**
   ```
   # Generated plots (regenerated on demand)
   static/plots/*.png
   exports/charts/*.png

   # Python cache
   __pycache__/
   *.pyc

   # Test coverage
   .coverage
   htmlcov/

   # Environment
   .env
   venv/
   *.egg-info/
   ```

---

## 🎯 Priority Actions

### High Priority (Do Immediately)
1. ✅ Move test files to `tests/` folder
2. ✅ Archive old documentation
3. ✅ Add plot cleanup script

### Medium Priority (This Week)
4. ⚠️ Delete `app.py` after confirming refactored version works
5. 📝 Update `.gitignore` for plots
6. 🧹 Run initial plot cleanup

### Low Priority (When Time Permits)
7. 📚 Organize prompts into `docs/prompts/`
8. 🔍 Review and consolidate utility scripts
9. 📖 Update README with new structure

---

**Conclusion:** Cleaning up these files will:
- Reduce clutter by ~70%
- Improve project navigation
- Speed up IDE indexing
- Make the codebase more professional
- Reduce disk space usage

**Next Step:** Run Phase 1 (organize tests) as it's the safest and easiest cleanup.
