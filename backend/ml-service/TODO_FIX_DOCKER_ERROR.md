# Fix Docker ModuleNotFoundError

## Summary
Fixed the ModuleNotFoundError: No module named 'app.etl' in /app/app/api/etl.py by updating imports and Docker configuration.

## Changes Made
- [x] Changed relative imports in `app/api/etl.py` from `from ..etl.pipeline` to `from etl.pipeline`
- [x] Added `ENV PYTHONPATH=/app` to `Dockerfile` to ensure etl module is in Python path
- [x] Added etl router to `app/main.py` imports and include_router calls
- [x] Added etl_router to `app/api/__init__.py` (though not strictly necessary for the import fix)

## Next Steps
- Test Docker build and run to verify the fix
- If issues persist, consider moving etl directory inside app directory for cleaner structure
