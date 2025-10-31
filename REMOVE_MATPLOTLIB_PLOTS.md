# 🗑️ Remove Obsolete Matplotlib Plot System

**Date:** October 29, 2025
**Reason:** Application now uses D3.js for frontend plotting. Backend matplotlib plotting is obsolete.

---

## 📊 Current Situation

### Old System (Matplotlib - Backend)
- Agents generated plots using matplotlib
- Saved as PNG files to disk
- Served as static files
- **Location:** `static/plots/` (275 files) and `exports/charts/` (191 files)

### New System (D3.js - Frontend)
- Agents return data as JSON
- Frontend generates interactive plots with D3.js
- No disk storage needed
- Better user experience (interactive, zoomable, etc.)

---

## 🎯 Cleanup Actions

### 1. Delete Plot Folders ✅

```bash
# Delete all matplotlib-generated plots
rm -rf static/plots/
rm -rf exports/charts/

# Or on Windows
rmdir /s /q static\plots
rmdir /s /q exports\charts
```

**Space Saved:** ~466 PNG files

---

### 2. Remove Matplotlib Dependencies

#### Update `pyproject.toml`
Remove or make matplotlib optional:

```toml
# Before
[tool.poetry.dependencies]
matplotlib = "^3.7.0"

# After - Make it optional since it's not core functionality
[tool.poetry.group.dev.dependencies]
matplotlib = "^3.7.0"  # Only for testing/development if needed
```

#### Update `requirements.txt`
Remove matplotlib if not needed for other purposes:
```
# matplotlib==3.7.0  # No longer needed for plotting
```

---

### 3. Remove Setup Code

#### `run_refactored.py` (lines 24-34)
```python
# ❌ REMOVE THIS - No longer needed
def setup_matplotlib():
    """Setup matplotlib backend when needed."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        return True
    except Exception as e:
        print(f"⚠️  Matplotlib setup failed: {e}")
        print("    Charts may not work, but app will run.")
        return False
```

---

### 4. Update `.gitignore`

Remove these lines (folders no longer exist):
```
# ❌ REMOVE - Folders deleted
static/plots/*.png
exports/charts/*.png
```

Add these if you ever need temporary exports:
```
# Temporary exports (if needed in future)
/exports/temp/
```

---

### 5. Update Docker Configuration

#### `Dockerfile`
Remove plot directory creation (line 32):
```dockerfile
# Before
RUN mkdir -p static/plots exports/data exports/charts datasets

# After
RUN mkdir -p exports/data datasets
```

Update permissions (line 38):
```dockerfile
# Before
RUN chmod 777 /app/static/plots /app/exports/data /app/exports/charts

# After
RUN chmod 777 /app/exports/data
```

---

### 6. Verify No Backend Code Generates Plots

**Search Results:** ✅ Clean
- No `savefig()` calls in current code
- No references to `static/plots` or `exports/charts` in active agents
- Matplotlib is only referenced in setup code (to be removed)

---

## 📋 Verification Checklist

After cleanup, verify:

- [ ] Application starts without errors
- [ ] D3.js plots still work on frontend
- [ ] No broken image links in UI
- [ ] Docker builds successfully
- [ ] No matplotlib import errors

---

## 🚀 Complete Cleanup Script

```bash
#!/bin/bash
# cleanup_matplotlib.sh

echo "🧹 Removing obsolete matplotlib plotting system..."

# 1. Delete plot folders
echo "Deleting plot folders..."
rm -rf static/plots/
rm -rf exports/charts/
echo "✅ Deleted 466 PNG files"

# 2. Update .gitignore
echo "Updating .gitignore..."
sed -i '/static\/plots/d' .gitignore
sed -i '/exports\/charts/d' .gitignore
echo "✅ Updated .gitignore"

# 3. Commit changes
echo "Committing changes..."
git add .gitignore Dockerfile
git rm -r static/plots/ exports/charts/
git commit -m "refactor: remove obsolete matplotlib plotting system

- Delete static/plots/ and exports/charts/ (466 PNG files)
- Application now uses D3.js for frontend plotting
- Remove matplotlib plot directories from Docker
- Update .gitignore accordingly"

echo "✅ Cleanup complete!"
echo ""
echo "📝 Manual steps remaining:"
echo "  1. Update run_refactored.py to remove setup_matplotlib()"
echo "  2. Review pyproject.toml matplotlib dependency"
echo "  3. Test D3.js plots still work"
echo "  4. Rebuild Docker: docker-compose up --build"
```

---

## 💾 Backup Before Deletion

If you want to keep a backup (just in case):

```bash
# Create backup archive
tar -czf matplotlib_plots_backup_$(date +%Y%m%d).tar.gz static/plots/ exports/charts/

# Then delete
rm -rf static/plots/ exports/charts/
```

---

## 📈 Benefits

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **PNG Files** | 466 | 0 | 100% reduction |
| **Disk Space** | ~50-100MB | 0 | Space saved |
| **Maintenance** | Manual cleanup needed | Auto-cleaned | Simplified |
| **User Experience** | Static images | Interactive D3 | Better UX |
| **Backend Load** | Generate + save plots | Just return data | Faster |

---

## 🎨 D3.js Implementation (Current)

Agents now return data like this:

```json
{
  "type": "chart",
  "chart_type": "line",
  "data": {
    "labels": ["Jan", "Feb", "Mar"],
    "datasets": [{
      "label": "Module Prices",
      "data": [0.15, 0.14, 0.13]
    }]
  }
}
```

Frontend renders with D3.js:
```javascript
// static/js/components/chart-renderer.js
renderLineChart(data) {
    const svg = d3.select("#chart-container")
        .append("svg")
        .attr("width", width)
        .attr("height", height);

    // D3 magic happens here...
}
```

---

## ⚠️ Important Notes

1. **Matplotlib might still be used for:**
   - Data analysis in notebooks (if any)
   - Testing/development
   - Alternative export formats (PDF reports, etc.)

2. **If you need matplotlib for other purposes:**
   - Keep it as a dev dependency
   - Don't remove from pyproject.toml
   - Just delete the plot folders

3. **D3.js advantages:**
   - Interactive (zoom, pan, hover)
   - No server-side rendering
   - No disk storage
   - Better performance
   - Modern user experience

---

## 🎯 Recommended Action

**Safe Approach:**
1. Delete plot folders first (biggest space saver)
2. Test application thoroughly
3. If everything works after 1 week, remove matplotlib dependency
4. Update documentation

**Command:**
```bash
# Safe: Just delete the folders
rm -rf static/plots/ exports/charts/

# Rebuild Docker
docker-compose up --build

# Test D3 charts work
```

---

**Status:** Ready to execute
**Risk:** Low (D3.js already in production)
**Time:** 5 minutes
**Space Saved:** 50-100MB
