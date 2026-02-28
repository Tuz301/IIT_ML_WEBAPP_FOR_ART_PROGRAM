# Project Cleanup Plan

## Overview
This document outlines the cleanup of unused/bulky components from the IIT ML Service project.

**Estimated Savings:**
- Frontend: ~2MB+ in node_modules
- Backend: ~4,000+ lines of unused code
- Docker: 3 duplicate compose files

---

## Phase 1: Frontend Dependencies Cleanup

### Unused Dependencies to Remove
| Package | Size | Reason |
|---------|------|--------|
| `@ai-sdk/openai` | ~50KB | AI SDK - Not used |
| `@emotion/react` | ~50KB | CSS-in-JS - Not used (Tailwind instead) |
| `@emotion/styled` | ~50KB | CSS-in-JS - Not used (Tailwind instead) |
| `@mui/material` | ~400KB | Material UI - Not used (shadcn/ui instead) |
| `@mui/icons-material` | ~100KB | MUI Icons - Not used |
| `cannon-es` | ~200KB | 3D Physics - Not used |
| `matter-js` | ~100KB | 2D Physics - Not used |
| `three` | ~600KB | 3D Graphics - Not used |
| `gsap` | ~200KB | Animations - Not used (framer-motion instead) |
| `i18next` | ~50KB | i18n - Not used (no translations) |
| `react-i18next` | ~50KB | i18n - Not used |
| `i18next-browser-languagedetector` | ~50KB | i18n - Not used |
| `ai` | ~50KB | AI SDK - Not used |

### Components Using These Dependencies
- `@zxing/library` - Used in `BarcodeScanner.tsx` - **KEEP**
- `react-webcam` - Used in `PhotoCapture.tsx` - **KEEP**

---

## Phase 2: Backend Optional Features

### Modules to Move to `app/optional/`
These are advanced features that are implemented but not integrated:

| Module | Lines | Purpose |
|--------|-------|---------|
| `vector_store.py` | ~700 | Vector DB support (Pinecone, Weaviate, Chroma) |
| `rag.py` | ~500 | Clinical RAG decision support |
| `ai_observability.py` | ~400 | Model drift detection, bias monitoring |
| `multi_tenancy.py` | ~600 | Multi-tenant isolation architecture |
| `cost_monitoring.py` | ~600 | Per-tenant cost tracking |
| `incident_response.py` | ~350 | Incident response runbooks |
| `ab_testing.py` | ~450 | A/B testing framework |
| `ensemble_methods.py` | ~350 | Ensemble prediction methods |

### API Routers to Move to `api/optional/`
| Router | Purpose |
|--------|---------|
| `ab_testing.py` | A/B testing endpoints |
| `ensemble.py` | Ensemble prediction endpoints |

### Modules to Review/Document
| Module | Lines | Action Needed |
|--------|-------|---------------|
| `async_features.py` | ~200 | Document purpose or remove |
| `missing_models.py` | ~100 | Document purpose or remove |
| `audit_retention.py` | ~300 | Keep if audit logs are needed |

---

## Phase 3: Docker Consolidation

### Duplicate Files to Remove
- `docker-compose.prod.yml` - Use `docker-compose.production.yml` instead
- `compose.debug.yaml` - Use environment variables in main compose instead

### Keep
- `docker-compose.yml` - Main compose file
- `docker-compose.production.yml` - Production overrides
- `docker-compose.ssl.yml` - SSL configuration (can be merged)
- `docker-compose.jaeger.yml` - Jaeger tracing (can be merged)

---

## Phase 4: Standalone Apps

### Files to Document or Remove
- `streamlit_app.py` - Standalone Streamlit app (not integrated)
- `streamlit_requirements.txt` - Requirements for Streamlit app

---

## Execution Steps

### Step 1: Update package.json
Remove unused frontend dependencies.

### Step 2: Create Optional Directory
```bash
mkdir -p backend/ml-service/app/optional
mkdir -p backend/ml-service/app/api/optional
```

### Step 3: Move Optional Modules
Move advanced features to `optional/` directory.

### Step 4: Update Imports
Update all imports to reference new locations.

### Step 5: Remove Duplicate Docker Files
Remove duplicate compose files.

### Step 6: Update Documentation
Document the optional features and how to enable them.

---

## Rollback Plan

If issues occur after cleanup:
1. Restore `package.json` from git history
2. Move modules back from `optional/` to `app/`
3. Restore Docker compose files from git history

```bash
# Rollback commands
git checkout HEAD~1 package.json
git checkout HEAD~1 backend/ml-service/app/
git checkout HEAD~1 docker-compose.*.yml
```

---

## Post-Cleanup Verification

1. **Frontend Build**
   ```bash
   npm install
   npm run build
   ```

2. **Backend Tests**
   ```bash
   cd backend/ml-service
   pytest tests/ -v
   ```

3. **Docker Compose**
   ```bash
   docker-compose config
   ```

---

## Summary

**Files to Modify:**
- `package.json` - Remove unused dependencies
- `backend/ml-service/app/main.py` - Update imports
- `backend/ml-service/app/api/__init__.py` - Update router imports

**Files to Create:**
- `backend/ml-service/app/optional/__init__.py`
- `backend/ml-service/app/api/optional/__init__.py`

**Files to Remove:**
- `docker-compose.prod.yml`
- `compose.debug.yaml`

**Directories to Create:**
- `backend/ml-service/app/optional/`
- `backend/ml-service/app/api/optional/`
