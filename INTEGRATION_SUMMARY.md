# Integration Summary & Quick Start Guide

## ✅ Completed Tasks

### 1. Shared Package Creation ✅
- Created `tilli-prompts` package with prompts and schemas
- Package structure: `tilli_prompts/{prompts,schemas}/`
- Includes both intervention and curriculum prompts
- All Pydantic schemas consolidated

### 2. Prompt-Eval-Tool Integration ✅
- Updated imports to use `tilli_prompts`
- Updated test files
- Added SEAL API connector
- Added UI for SEAL API integration

### 3. Documentation ✅
- Created `SHARED_PACKAGE_INTEGRATION.md` - Setup guide
- Created `TECHNICAL_IMPROVEMENTS.md` - Improvement suggestions
- Created `SHARED_PACKAGE_PROPOSAL.md` - Integration proposal
- Created `DUPLICATION_ANALYSIS.md` - Original analysis

### 4. SEAL API Connector ✅
- Created `seal_client.py` - API client module
- Added UI controls in Streamlit sidebar
- Integrated into generation workflow
- Fallback to local generation if API unavailable

## 🚀 Quick Start

### Step 1: Install Shared Package

```bash
cd /home/keith/tilli-prompts
pip install -e .
```

### Step 2: Install Prompt-Eval-Tool Dependencies

```bash
cd /home/keith/prompt-eval-tool
pip install -r requirements.txt
```

### Step 3: Set Up Environment

Create `.env` file:
```bash
GOOGLE_API_KEY=your_api_key_here
SEAL_API_URL=http://localhost:8000  # Optional, for API integration
```

### Step 4: Run Prompt-Eval-Tool

```bash
cd /home/keith/prompt-eval-tool
streamlit run app.py
```

### Step 5: (Optional) Run SEAL API

In another terminal:
```bash
cd /home/keith/seal
uvicorn app.main:app --reload
```

Then in Prompt-Eval-Tool UI:
1. Check "Use SEAL API for generation" in sidebar
2. Enter SEAL API URL (default: http://localhost:8000)
3. The health check will run automatically and cache the result
4. Click "🔄 Refresh" if you need to re-check the health status
5. Generate & Evaluate will fetch from SEAL API using the cached client

**Note**: Health check results are cached in session state to improve performance and reliability. The health check only runs when:
- First time checking the checkbox
- URL changes
- Manual refresh button is clicked

## 📋 What's Changed

### Files Created
- `/home/keith/tilli-prompts/` - Shared package
- `/home/keith/prompt-eval-tool/seal_client.py` - API client
- `/home/keith/prompt-eval-tool/SHARED_PACKAGE_INTEGRATION.md`
- `/home/keith/prompt-eval-tool/TECHNICAL_IMPROVEMENTS.md`
- `/home/keith/prompt-eval-tool/SHARED_PACKAGE_PROPOSAL.md`

### Files Modified
- `/home/keith/prompt-eval-tool/app.py` - Added SEAL API integration
- `/home/keith/prompt-eval-tool/requirements.txt` - Added `requests`
- `/home/keith/prompt-eval-tool/tests/test_prompts.py` - Updated imports

### Files to Update (SEAL - Not Yet Done)
- `/home/keith/seal/app/main.py` - Update imports
- `/home/keith/seal/app/llm/gateway.py` - Update imports
- `/home/keith/seal/app/llm/curriculum_gateway.py` - Update imports
- `/home/keith/seal/requirements.txt` - Add tilli-prompts dependency

## 🔄 Next Steps for SEAL Integration

1. **Update SEAL imports:**
   ```python
   # Change from:
   from app.prompts.intervention import InterventionPrompt
   # To:
   from tilli_prompts import InterventionPrompt
   ```

2. **Install shared package:**
   ```bash
   cd /home/keith/seal
   pip install -e ../tilli-prompts
   ```

3. **Update requirements.txt:**
   ```
   tilli-prompts @ git+https://github.com/yourorg/tilli-prompts.git@main
   # Or for local dev:
   # tilli-prompts @ file:///home/keith/tilli-prompts
   ```

4. **Test SEAL API:**
   ```bash
   uvicorn app.main:app --reload
   # Test /score and /curriculum endpoints
   ```

## 🎯 Key Features

### Shared Package Benefits
- ✅ Single source of truth for prompts/schemas
- ✅ Automatic consistency across repos
- ✅ Easier maintenance and updates
- ✅ Independent versioning

### SEAL API Integration Benefits
- ✅ Fetch real SEAL outputs for evaluation
- ✅ Compare SEAL vs local generation
- ✅ Test SEAL API endpoints
- ✅ End-to-end workflow

## 📊 Testing Checklist

### Prompt-Eval-Tool
- [ ] Install shared package: `pip install -e ../tilli-prompts`
- [ ] Run app: `streamlit run app.py`
- [ ] Test EMT prompt generation
- [ ] Test Curriculum prompt generation
- [ ] Test evaluation workflow
- [ ] Test SEAL API integration (if SEAL running)

### SEAL (After Integration)
- [ ] Install shared package
- [ ] Update all imports
- [ ] Run API: `uvicorn app.main:app --reload`
- [ ] Test `/score` endpoint
- [ ] Test `/curriculum` endpoint
- [ ] Test `/health` endpoint

## 🐛 Troubleshooting

### Import Errors
```bash
# If you see "No module named 'tilli_prompts'"
pip install -e /home/keith/tilli-prompts
```

### SEAL API Connection Issues
- Check SEAL is running: `curl http://localhost:8000/health`
- Verify URL in sidebar matches SEAL address
- Check firewall/network settings
- **Health Check Caching**: The health check result is cached in session state to avoid re-checking on every button click. Use the "🔄 Refresh" button to manually re-check the health status.
- **Improved Reliability**: The health check now accepts HTTP 200 responses even if the service status is "degraded" (some components unavailable), as long as the API is accessible.

### Version Conflicts
```bash
# Ensure compatible Pydantic version
pip install --upgrade pydantic>=2.9.0
```

## 📚 Documentation Files

1. **SHARED_PACKAGE_INTEGRATION.md** - How to integrate the shared package
2. **TECHNICAL_IMPROVEMENTS.md** - Improvement suggestions and recommendations
3. **SHARED_PACKAGE_PROPOSAL.md** - Detailed integration proposal
4. **DUPLICATION_ANALYSIS.md** - Original duplication analysis

## 🎉 Success Criteria

- [x] Shared package created and functional
- [x] Prompt-Eval-Tool integrated with shared package
- [x] SEAL API connector implemented
- [x] Documentation created
- [ ] SEAL integrated with shared package (TODO)
- [ ] Both systems tested end-to-end (TODO)

## 📝 Notes

- The shared package uses relative imports within the package
- Both repos can import from `tilli_prompts` after installation
- SEAL API integration is optional - local generation still works
- Old `prompts/` and `schemas/` directories can be removed after validation

## 🔮 Future Enhancements

1. Publish shared package to internal PyPI
2. Add CI/CD for shared package
3. Create unified evaluation endpoint in SEAL
4. Add caching for prompt templates
5. Implement parallel batch processing

---

**Status**: Prompt-Eval-Tool integration complete ✅ | SEAL integration pending ⏳



