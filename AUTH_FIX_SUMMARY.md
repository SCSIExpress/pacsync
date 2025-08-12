# Authentication Fix Summary

## Problem
The client was getting 401 (Unauthorized) errors when trying to call sync endpoints, causing:
- Repeated token refresh attempts
- Rate limiting issues
- Multiple duplicate endpoints being registered
- Endpoints showing as offline in the interface
- Error: `'Depends' object has no attribute 'credentials'`

## Root Cause
The authentication handling in the sync endpoints (`server/api/sync.py`) and some endpoint routes (`server/api/endpoints.py`) was incorrect. The code was trying to manually call the authentication dependency function without properly handling the FastAPI dependency injection system and the required `credentials` parameter.

### Incorrect Pattern (Before Fix)
```python
async def get_authenticate_endpoint(request: Request):
    """Get endpoint authentication dependency from app state."""
    authenticate_func = request.app.state.authenticate_endpoint
    return await authenticate_func(request)  # ❌ Wrong - missing credentials parameter

# Usage in endpoints:
authenticate_endpoint = get_authenticate_endpoint(request)
current_endpoint = await authenticate_endpoint(request)  # ❌ Wrong - manual call
```

### Correct Pattern (After Fix)
```python
async def get_authenticate_endpoint(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Endpoint:
    """Get endpoint authentication dependency from app state."""
    auth_func = request.app.state.authenticate_endpoint
    return await auth_func(request, credentials)  # ✅ Correct - proper parameters

# Usage in endpoints:
current_endpoint: Endpoint = Depends(get_authenticate_endpoint)  # ✅ Correct - FastAPI dependency
```

## Files Modified

### 1. `server/api/sync.py`
- Added imports for `HTTPBearer` and `HTTPAuthorizationCredentials`
- Added `security = HTTPBearer(auto_error=False)` instance
- Fixed `get_authenticate_endpoint()` function to properly handle both `request` and `credentials` parameters
- Updated all sync endpoints to use FastAPI dependency injection:
  - `sync_to_latest()` - now uses `current_endpoint: Endpoint = Depends(get_authenticate_endpoint)`
  - `set_as_latest()` - now uses `current_endpoint: Endpoint = Depends(get_authenticate_endpoint)`
  - `revert_to_previous()` - now uses `current_endpoint: Endpoint = Depends(get_authenticate_endpoint)`
  - `get_endpoint_operations()` - now uses `current_endpoint: Endpoint = Depends(get_authenticate_endpoint)`

### 2. `server/api/endpoints.py`
- Added imports for `HTTPBearer` and `HTTPAuthorizationCredentials`
- Added `security = HTTPBearer(auto_error=False)` instance
- Fixed `get_authenticate_endpoint()` function to properly handle both `request` and `credentials` parameters
- Updated authenticated endpoints to use FastAPI dependency injection:
  - `update_endpoint_status()` - now uses `current_endpoint: Endpoint = Depends(get_authenticate_endpoint)`
  - `remove_endpoint()` - now uses `current_endpoint: Endpoint = Depends(get_authenticate_endpoint)`
  - `submit_repository_info()` - now uses `current_endpoint: Endpoint = Depends(get_authenticate_endpoint)`

## How the Authentication Should Work

1. **Server Setup** (`server/api/main.py`):
   ```python
   authenticate_endpoint, authenticate_admin = create_auth_dependencies(
       jwt_secret=config.security.jwt_secret_key,
       admin_tokens=config.security.admin_tokens
   )
   app.state.authenticate_endpoint = authenticate_endpoint
   ```

2. **Endpoint Usage**:
   ```python
   async def some_endpoint(
       request: Request,
       current_endpoint: Endpoint = Depends(get_authenticate_endpoint),
       ...
   ):
       # current_endpoint is automatically injected by FastAPI
       # and contains the authenticated endpoint object
   ```

3. **Token Flow**:
   - Client registers and receives JWT token
   - Client includes token in `Authorization: Bearer <token>` header
   - FastAPI extracts credentials using `HTTPBearer` security scheme
   - `get_authenticate_endpoint` receives both `request` and `credentials`
   - Server validates token and returns authenticated endpoint object
   - Endpoint can only perform operations on itself (security check)

## Testing the Fix

1. **Start the server** (on port 4444 as mentioned):
   ```bash
   python server/main.py
   ```

2. **Test client authentication**:
   - Client should successfully register and receive token
   - Sync operations should work without 401 errors
   - No more duplicate endpoint registrations
   - Endpoints should show as online in the interface

3. **Verify logs**:
   - No more authentication errors in server logs
   - No more rate limiting warnings
   - Successful sync operation logs

## Additional Issue: Missing States API Endpoint

After fixing the authentication issue, a new error appeared:
- `HTTP 405 - Method Not Allowed` for `POST /api/states/{id}`

### Root Cause
The client was trying to call a `/api/states/` endpoint that didn't exist in the server implementation, even though it was documented in the API documentation.

### Solution
Created a new `server/api/states.py` router with the following endpoints:
- `POST /api/states/{endpoint_id}` - Submit package state for an endpoint
- `GET /api/states/{state_id}` - Get specific state by ID (placeholder)
- `GET /api/states/endpoint/{endpoint_id}` - Get historical states for an endpoint
- `GET /api/states/pool/{pool_id}` - Get states across pool endpoints (placeholder)
- `GET /api/states/health` - Health check for states service

### Files Added/Modified
- **Added**: `server/api/states.py` - New states API router
- **Modified**: `server/api/main.py` - Added states router to application

### Additional Fix: Incorrect Method Calls
After implementing the states API, there was an error: `'SyncCoordinator' object has no attribute 'save_endpoint_state'`

**Root Cause**: The states API was calling non-existent methods on SyncCoordinator.

**Solution**: Fixed method calls to use the correct StateManager methods:
- Changed `sync_coordinator.save_endpoint_state()` to `sync_coordinator.state_manager.save_state()`
- Changed `sync_coordinator.get_endpoint_states()` to `sync_coordinator.state_manager.get_endpoint_states()`

## Expected Behavior After Fix

- ✅ Client authenticates successfully on first attempt
- ✅ Sync endpoints accept authenticated requests
- ✅ No more 401 errors on sync operations
- ✅ No more 405 errors on states endpoints
- ✅ No more 500 errors on state submission
- ✅ No more duplicate endpoint registrations
- ✅ Endpoints show as online in the web interface
- ✅ Token refresh works properly when needed
- ✅ Rate limiting no longer triggered by auth failures
- ✅ State submission endpoints are available

## Additional Notes

- The fix maintains all existing security checks (endpoints can only operate on themselves)
- No changes to the client-side code were needed
- The authentication middleware and token generation remain unchanged
- The new states API provides the missing endpoints that were documented but not implemented
- Some state endpoints are marked as "not yet implemented" and return 501 status codes for future development