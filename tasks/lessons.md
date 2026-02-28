# Lessons Learned - IHVN_AIML/my_app

This document captures lessons learned during development to prevent repeating the same mistakes.

## Login Failure - Multiple Backend Processes (2026-02-28)

### Problem
Login was failing with "Database operation failed" even after applying the correct fix for the Python 3.12+ timezone issue.

### Root Cause
**Multiple backend servers running on the same port (8000)** were causing conflicts. The curl request was hitting an old server without the fix, while the TestClient (which bypasses the HTTP layer) worked correctly.

### How to Detect
```bash
# Check for multiple processes on the same port
netstat -ano | findstr ":8000"

# Kill all conflicting processes
taskkill /F /PID <pid1> /PID <pid2> ...
```

### Rules to Prevent Recurrence

1. **Always check for port conflicts when debugging**
   - Use `netstat -ano | findstr ":port"` to verify only one process is listening
   - Kill all old processes before starting a new one
   - Don't rely on terminal status - processes may persist even after Ctrl+C

2. **TestClient vs curl differences**
   - TestClient bypasses uvicorn and directly calls FastAPI
   - TestClient may work while HTTP requests fail if there are server conflicts
   - Always verify with actual HTTP requests (curl/Postman) before declaring success

3. **Python bytecode cache can cause issues**
   - Clear `__pycache__` and `*.pyc` files after code changes
   - Use `del /s /q __pycache__` and `del /s /q *.pyc` on Windows
   - Restart servers after clearing cache

### Related Files
- [`backend/ml-service/app/auth.py`](backend/ml-service/app/auth.py) - Fixed timezone-aware datetime
- [`backend/ml-service/app/middleware/error_handling.py`](backend/ml-service/app/middleware/error_handling.py) - Fixed logger shadowing

### Verification Steps
- Kill all processes on port 8000
- Clear Python cache
- Start fresh backend server
- Test login with curl
- Verify only one process is listening on the port

---

## Error Boundary & Sentry Integration (2026-02-26)

### Problem
The [`ErrorBoundaryEnhanced.tsx`](src/components/ErrorBoundaryEnhanced.tsx) component had two critical bugs:

1. **Sentry Integration Failure**: The error boundary unconditionally called Sentry functions (`captureException`, `addBreadcrumb`) even when Sentry was not initialized. This caused crashes in development mode where `VITE_SENTRY_DSN` was not configured.

2. **useErrorBoundary Hook Anti-Pattern**: The `triggerError` function tried to throw errors in event handlers, but React Error Boundaries only catch errors during rendering, lifecycle methods, and constructors - not in event handlers or async code.

### Root Causes
1. **Missing initialization check**: [`sentry.ts`](src/lib/sentry.ts) had no way to check if Sentry was initialized before calling its functions
2. **Misunderstanding React Error Boundaries**: The hook was designed around throwing errors, which doesn't work in event handlers

### Solutions Implemented
1. Added `isSentryInitialized()` function to [`sentry.ts`](src/lib/sentry.ts)
2. Added null checks to all Sentry functions with fallback console logging
3. Rewrote `useErrorBoundary` hook to use state-based approach instead of throwing
4. Added comprehensive JSDoc documentation explaining React Error Boundary limitations

### Rules to Prevent Recurrence

1. **Always check initialization before using external services**
   - When integrating third-party services (Sentry, analytics, etc.), always provide a way to check if the service is initialized
   - Add graceful fallbacks when the service is unavailable

2. **Understand React Error Boundary limitations**
   - Error Boundaries only catch errors in: render, lifecycle methods, constructors
   - They do NOT catch errors in: event handlers, async code, setTimeout, useEffect callbacks
   - For event handler errors, use state-based error handling or manual logging

3. **Document hook limitations clearly**
   - When creating hooks that interact with React features, document what they can and cannot do
   - Provide examples for both sync and async error handling

### Related Files
- [`src/lib/sentry.ts`](src/lib/sentry.ts) - Added `isSentryInitialized()` and null checks
- [`src/components/ErrorBoundaryEnhanced.tsx`](src/components/ErrorBoundaryEnhanced.tsx) - Fixed Sentry calls and rewrote hook

### Verification Steps
- Run TypeScript type checking: `npm run type-check`
- Test error boundary in development mode (without Sentry DSN)
- Test error boundary in production mode (with Sentry DSN)
- Verify useErrorBoundary hook works in event handlers
