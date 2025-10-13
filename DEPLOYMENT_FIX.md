# Deployment Fix Guide

## Issue
The deployment is failing because of missing dependencies (`prometheus_client`, `psutil`, etc.) that are required for the production monitoring features.

## Solutions

### Option 1: Update Requirements (Recommended)
I've updated the `requirements.txt` file to include all necessary dependencies:

```bash
# The updated requirements.txt now includes:
prometheus_client>=0.17.0,<1.0.0
psutil>=5.9.0,<6.0.0
aiohttp>=3.8.0,<4.0.0
numpy>=1.24.0,<2.0.0
matplotlib>=3.7.0,<4.0.0
```

**To fix the deployment:**
1. Commit and push the updated `requirements.txt`
2. Redeploy on Render - it should now install all dependencies correctly

### Option 2: Use Minimal Deployment
If the full requirements cause issues, use the minimal deployment:

1. **Update your Render deployment command to:**
   ```
   uvicorn deploy:app --host 0.0.0.0 --port 10000
   ```

2. **Or use minimal requirements:**
   - Rename `requirements.txt` to `requirements-full.txt`
   - Rename `requirements-minimal.txt` to `requirements.txt`
   - Redeploy

### Option 3: Environment-Specific Requirements
Create different requirement files for different environments:

```bash
# For production with monitoring
pip install -r requirements.txt

# For minimal deployment
pip install -r requirements-minimal.txt
```

## What I Fixed

### 1. Made Prometheus Imports Optional
Updated `api/app/metrics.py` to gracefully handle missing `prometheus_client`:

```python
try:
    from prometheus_client import Counter, Histogram, Gauge, Info
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Mock classes for fallback
```

### 2. Created Fallback Deployment Script
Created `deploy.py` that provides a minimal API if the full version fails to load.

### 3. Updated Requirements
Added all necessary dependencies to `requirements.txt`.

## Testing the Fix

### Local Testing
```bash
# Test with full requirements
pip install -r requirements.txt
python -m uvicorn api.app.main:app --reload

# Test with minimal requirements
pip install -r requirements-minimal.txt
python deploy.py
```

### Production Testing
After deployment, test these endpoints:
- `GET /` - Should return API info
- `GET /healthz` - Should return health status
- `POST /parse` - Should parse text (may be limited in minimal mode)
- `GET /docs` - Should show API documentation

## Recommended Next Steps

1. **Try Option 1 first** - Update requirements and redeploy
2. **If that fails**, use Option 2 - Minimal deployment
3. **Once deployed**, you can gradually add back features

## Monitoring After Deployment

Once deployed successfully, you can:

```bash
# Test the API
curl https://your-app.onrender.com/healthz

# Run production validation (if full version deployed)
python run_production_validation.py --single-run --api-url https://your-app.onrender.com
```

## Common Issues and Solutions

### Issue: "Module not found" errors
**Solution**: Make sure all imports in the updated `requirements.txt` are included

### Issue: Memory/CPU limits on Render
**Solution**: Use the minimal deployment option which has fewer dependencies

### Issue: Import path errors
**Solution**: The `app/main.py` file handles import paths correctly for Render's auto-detection

## Success Indicators

✅ Deployment completes without errors  
✅ `/healthz` endpoint returns 200 OK  
✅ `/docs` shows API documentation  
✅ `/parse` endpoint accepts POST requests  
✅ No import errors in logs  

The deployment should now work correctly with either the full feature set or the minimal version!