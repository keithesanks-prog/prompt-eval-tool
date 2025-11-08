# SEAL API Integration Guide

This document explains how the Prompt-Eval-Tool integrates with the SEAL API to fetch real intervention plans instead of generating them locally.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Integration Method](#integration-method)
3. [Health Check Mechanism](#health-check-mechanism)
4. [Caching Strategy](#caching-strategy)
5. [Implementation Details](#implementation-details)
6. [Usage Instructions](#usage-instructions)
7. [API Endpoints](#api-endpoints)
8. [Error Handling](#error-handling)
9. [Troubleshooting](#troubleshooting)

## Architecture Overview

The integration uses a **REST API client pattern** where:

- **SEAL** runs as a FastAPI server exposing REST endpoints
- **Prompt-Eval-Tool** uses an HTTP client (`SEALAPIClient`) to communicate with SEAL
- Both systems share the same schemas via the `tilli-prompts` package for consistency
- Health checks ensure connectivity before attempting API calls
- Caching prevents redundant health checks on every user interaction

```
┌─────────────────────┐         HTTP/REST          ┌──────────────────┐
│  Prompt-Eval-Tool   │ ──────────────────────────> │   SEAL API       │
│  (Streamlit App)    │                             │  (FastAPI)       │
│                     │ <────────────────────────── │                  │
│  - SEALAPIClient    │      JSON Responses        │  - /health       │
│  - Health Check     │                             │  - /score        │
│  - Caching          │                             │  - /curriculum   │
└─────────────────────┘                             └──────────────────┘
         │                                                    │
         │                                                    │
         └─────────────── Shared Schemas ────────────────────┘
                    (tilli-prompts package)
```

## Integration Method

### 1. API Client Implementation

The integration uses a dedicated `SEALAPIClient` class (`seal_client.py`) that wraps HTTP requests to SEAL endpoints.

**Key Features:**
- **Type-safe requests**: Uses Pydantic models (`InterventionRequest`, `CurriculumRequest`) from `tilli-prompts`
- **Error handling**: Comprehensive exception handling for timeouts, connection errors, and HTTP errors
- **Configurable timeouts**: Default 30 seconds for generation, 10 seconds for health checks
- **Automatic JSON serialization**: Converts Pydantic models to JSON automatically

**Example Usage:**
```python
from seal_client import SEALAPIClient
from tilli_prompts.schemas import InterventionRequest

# Initialize client
client = SEALAPIClient(base_url="http://localhost:8000")

# Check health
if client.health_check():
    # Generate intervention
    request = InterventionRequest(**input_data)
    response = client.generate_intervention(request)
```

### 2. Shared Schema Package

Both systems use the `tilli-prompts` package to ensure:
- **Consistent data structures**: Same request/response schemas
- **Type validation**: Pydantic models validate data before sending
- **Single source of truth**: Changes to schemas propagate to both systems

**Schemas Used:**
- `InterventionRequest`: For EMT-based intervention plans
- `CurriculumRequest`: For curriculum-based intervention plans
- `HealthResponse`: For health check responses

## Health Check Mechanism

### SEAL Side (`/health` endpoint)

The SEAL API implements a resilient health check that:

1. **Always returns HTTP 200** when the service is accessible (even if components are degraded)
2. **Checks component health** separately:
   - `llm_healthy`: LLM gateway status
   - `curriculum_healthy`: Curriculum gateway status
3. **Returns status**:
   - `"healthy"`: All components operational
   - `"degraded"`: Service running but some components unavailable

**Response Format:**
```json
{
  "status": "healthy" | "degraded",
  "version": "1.0.0",
  "llm_provider": "gemini",
  "llm_healthy": true | false,
  "curriculum_healthy": true | false
}
```

**Implementation (SEAL):**
```python
@app.get("/health", response_model=HealthResponse)
async def health_check():
    llm_healthy = False
    curriculum_healthy = False
    
    try:
        llm_healthy = llm_gateway.health_check()
    except Exception as e:
        logger.warning(f"LLM health check failed: {str(e)}")
        llm_healthy = False
    
    try:
        curriculum_healthy = curriculum_gateway.health_check()
    except Exception as e:
        logger.warning(f"Curriculum health check failed: {str(e)}")
        curriculum_healthy = False
    
    # Always return 200 - service is running even if LLM is temporarily unavailable
    return HealthResponse(
        status="healthy" if (llm_healthy and curriculum_healthy) else "degraded",
        llm_healthy=llm_healthy,
        curriculum_healthy=curriculum_healthy
    )
```

### Prompt-Eval-Tool Side

The client-side health check:

1. **Makes GET request** to `/health` endpoint
2. **Accepts HTTP 200** as success (even if status is "degraded")
3. **Handles errors gracefully**: Returns `False` on timeout, connection errors, or non-200 status
4. **Uses 10-second timeout** to prevent hanging

**Implementation (Prompt-Eval-Tool):**
```python
def health_check(self) -> bool:
    """Check if SEAL API is healthy and accessible."""
    try:
        response = requests.get(
            f"{self.base_url}/health", timeout=10
        )
        # Accept 200 status even if status is "degraded" - service is still accessible
        if response.status_code == 200:
            return True
        return False
    except requests.exceptions.Timeout:
        return False
    except requests.exceptions.ConnectionError:
        return False
    except Exception:
        return False
```

## Caching Strategy

### Problem Solved

Streamlit re-runs the entire script on every user interaction (button clicks, input changes). Without caching, this would cause:
- **Redundant health checks** on every button click
- **Performance degradation** from repeated HTTP requests
- **Inconsistent state** if health checks fail intermittently

### Solution: Session State Caching

The integration uses Streamlit's `session_state` to cache:
1. **Health check results** (per URL)
2. **SEAL client instance** (reused across interactions)

**Cache Key Structure:**
```python
health_cache_key = f"health_{seal_api_url}"
st.session_state.seal_health_check[health_cache_key] = {
    "healthy": bool,
    "timestamp": float,
    "url": str,
    "error": str  # Optional, if health check failed
}
```

**When Health Check Runs:**
- ✅ **First time** checking the "Use SEAL API" checkbox
- ✅ **URL changes** (automatically clears cache and re-checks)
- ✅ **Manual refresh** (user clicks "🔄 Refresh" button)
- ❌ **NOT on every button click** (uses cached result)

**Implementation:**
```python
# Initialize session state
if "seal_health_check" not in st.session_state:
    st.session_state.seal_health_check = {}
if "seal_client" not in st.session_state:
    st.session_state.seal_client = None

# Check cache
health_cache_key = f"health_{seal_api_url}"
if health_cache_key not in st.session_state.seal_health_check:
    # Perform health check and cache result
    seal_client = SEALAPIClient(base_url=seal_api_url)
    is_healthy = seal_client.health_check()
    st.session_state.seal_health_check[health_cache_key] = {
        "healthy": is_healthy,
        "timestamp": time.time(),
        "url": seal_api_url
    }
    if is_healthy:
        st.session_state.seal_client = seal_client
else:
    # Use cached result
    health_status = st.session_state.seal_health_check[health_cache_key]
    if health_status.get("healthy"):
        seal_client = st.session_state.seal_client
```

## Implementation Details

### File Structure

```
prompt-eval-tool/
├── seal_client.py          # SEAL API client implementation
├── app.py                 # Streamlit app with integration logic
└── tilli-prompts/         # Shared schemas package
    └── tilli_prompts/
        └── schemas/
            ├── base.py    # InterventionRequest, HealthResponse
            └── curriculum.py  # CurriculumRequest

seal/
├── app/
│   ├── main.py           # FastAPI app with /health endpoint
│   ├── api/
│   │   └── endpoints/
│   │       └── stream.py  # Streaming endpoint
│   └── schemas/
│       └── base.py       # HealthResponse schema
```

### Integration Flow

1. **User enables SEAL API** in Streamlit sidebar
2. **Health check runs** (if not cached) → Caches result
3. **User clicks "Generate & Evaluate"**
4. **App checks cache** → Uses cached client if available
5. **Makes API call** to SEAL (`/score` or `/curriculum`)
6. **Receives response** → Displays in UI
7. **Falls back to local generation** if API call fails

### Code Integration Points

**In `app.py` (Prompt-Eval-Tool):**

```python
# 1. UI Configuration (Sidebar)
use_seal_api = st.checkbox("Use SEAL API for generation")
seal_api_url = st.text_input("SEAL API URL", value="http://localhost:8000")

# 2. Health Check with Caching
if use_seal_api:
    if health_cache_key not in st.session_state.seal_health_check:
        seal_client = SEALAPIClient(base_url=seal_api_url)
        is_healthy = seal_client.health_check()
        # Cache result...
    
# 3. Generation Logic
if use_seal_api and seal_client:
    if prompt_type == "emt":
        intervention_request = InterventionRequest(**input_data)
        seal_response = seal_client.generate_intervention(intervention_request)
        answer = json.dumps(seal_response, indent=2)
    elif prompt_type == "curriculum":
        curriculum_request = CurriculumRequest(**input_data)
        seal_response = seal_client.generate_curriculum(curriculum_request)
        answer = json.dumps(seal_response, indent=2)
```

## Usage Instructions

### Prerequisites

1. **SEAL API running**:
   ```bash
   cd /path/to/seal
   uvicorn app.main:app --reload
   ```

2. **Shared package installed**:
   ```bash
   pip install -e /path/to/tilli-prompts
   ```

3. **Dependencies installed**:
   ```bash
   pip install requests  # For HTTP client
   ```

### Step-by-Step Usage

1. **Start SEAL API** (Terminal 1):
   ```bash
   cd seal
   uvicorn app.main:app --reload
   ```

2. **Start Prompt-Eval-Tool** (Terminal 2):
   ```bash
   cd prompt-eval-tool
   streamlit run app.py
   ```

3. **In the UI**:
   - Navigate to sidebar
   - Check "Use SEAL API for generation"
   - Enter SEAL API URL (default: `http://localhost:8000`)
   - Wait for "✅ SEAL API is accessible" message
   - Click "🔄 Refresh" if you need to re-check health status

4. **Generate & Evaluate**:
   - Select prompt type (EMT or Curriculum)
   - Enter input data
   - Click "🚀 Generate & Evaluate"
   - The tool will fetch from SEAL API instead of generating locally

## API Endpoints

### Health Check
```
GET /health
```
- **Purpose**: Verify SEAL API is accessible
- **Response**: `HealthResponse` with component status
- **Status Codes**: Always 200 (if service is running)

### Generate Intervention (EMT)
```
POST /score
Content-Type: application/json

{
  "scores": {
    "EMT1": [35.0, 40.0, 38.0],
    "EMT2": [75.0, 78.0, 80.0],
    "EMT3": [70.0, 72.0, 68.0],
    "EMT4": [65.0, 67.0, 70.0]
  },
  "metadata": {
    "class_id": "CLASS_5A_2024",
    "deficient_area": "EMT1",
    "num_students": 25
  }
}
```

### Generate Curriculum
```
POST /curriculum
Content-Type: application/json

{
  "grade_level": "1",
  "skill_areas": ["emotional_awareness"],
  "score": 25.0
}
```

## Error Handling

### Health Check Failures

**Symptoms:**
- "⚠️ SEAL API is not accessible" message
- Health check returns `False`

**Causes & Solutions:**
1. **SEAL not running**: Start SEAL API server
2. **Wrong URL**: Verify URL matches SEAL instance
3. **Network issues**: Check firewall/network settings
4. **Timeout**: Increase timeout in `seal_client.py` (default: 10s)

### API Call Failures

**Automatic Fallback:**
- If API call fails, the tool automatically falls back to local generation
- Error message displayed: "❌ Failed to fetch from SEAL API: {error}"
- User can continue using the tool with local generation

**Common Errors:**
- **Timeout**: Request took longer than 30 seconds
- **Connection Error**: Cannot reach SEAL API
- **HTTP Error**: API returned error status (400, 500, etc.)
- **Validation Error**: Input data doesn't match schema

## Troubleshooting

### Issue: Health Check Passes But Generation Fails

**Possible Causes:**
1. Health check succeeded but API endpoint is failing
2. Input data format doesn't match SEAL's expected schema
3. SEAL API logs show errors

**Solutions:**
1. Check SEAL API logs for detailed error messages
2. Verify input data matches `InterventionRequest` or `CurriculumRequest` schema
3. Test API directly with `curl`:
   ```bash
   curl -X POST http://localhost:8000/score \
     -H "Content-Type: application/json" \
     -d '{"scores": {...}, "metadata": {...}}'
   ```

### Issue: Health Check Fails Intermittently

**Possible Causes:**
1. Network latency causing timeouts
2. SEAL API temporarily unavailable
3. Cached result is stale

**Solutions:**
1. Click "🔄 Refresh" to force a new health check
2. Increase timeout in `seal_client.py`:
   ```python
   response = requests.get(f"{self.base_url}/health", timeout=15)
   ```
3. Check SEAL API logs for component failures

### Issue: Cached Client Not Working

**Symptoms:**
- Health check passes but `seal_client` is `None`
- Generation fails with "SEAL API is not accessible"

**Solution:**
- Clear cache by unchecking and re-checking "Use SEAL API"
- Or click "🔄 Refresh" button
- Or change the URL (then change it back)

## Key Design Decisions

### 1. Why Always Return HTTP 200 for Health?

**Reason**: Allows clients to detect if the API service is running even if underlying LLM services are temporarily unavailable. This prevents false negatives when the service is accessible but components are degraded.

**Benefit**: More resilient integration that doesn't fail completely when only some components are down.

### 2. Why Cache Health Checks?

**Reason**: Streamlit re-runs scripts on every interaction, causing redundant HTTP requests.

**Benefit**: 
- Better performance (no repeated health checks)
- Consistent state across interactions
- Reduced load on SEAL API

### 3. Why Use Shared Schemas?

**Reason**: Ensures type safety and consistency between systems.

**Benefit**:
- Compile-time validation
- Single source of truth
- Easier maintenance

### 4. Why Automatic Fallback?

**Reason**: Provides graceful degradation when API is unavailable.

**Benefit**: Users can continue working even if SEAL API is down.

## Future Enhancements

Potential improvements to the integration:

1. **Health Check Expiration**: Add TTL to cached health checks (e.g., re-check after 5 minutes)
2. **Retry Logic**: Automatic retries for failed API calls with exponential backoff
3. **Connection Pooling**: Reuse HTTP connections for better performance
4. **Metrics**: Track API call success rates, latency, and errors
5. **WebSocket Support**: Real-time updates for streaming responses
6. **Authentication**: Add API key or token authentication for production use

## Related Documentation

- [SEAL README](../seal/README.md) - SEAL API documentation
- [Prompt-Eval-Tool README](README.md) - Main tool documentation
- [Integration Summary](INTEGRATION_SUMMARY.md) - High-level integration overview
- [Shared Package Integration](SHARED_PACKAGE_INTEGRATION.md) - Schema sharing details

---

**Last Updated**: 2024
**Integration Version**: 1.0.0

