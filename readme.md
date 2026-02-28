# IIT ML Service

**Integrated HIV/Tuberculosis (IIT) Prediction ML Service**

A machine learning system for predicting IIT co-infection risk in patients.

---

## 📚 Documentation

**[📖 Complete Documentation](docs/README.md)** - Start here for the complete guide

**[🗺️ Documentation Site Map](docs/SITE_MAP.md)** - Navigation guide for all documentation

---

## 🚀 Quick Start

```bash
# Install dependencies
npm install
cd backend/ml-service && pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start backend (Terminal 1)
python -m uvicorn backend.ml-service.app.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend (Terminal 2)
npm run dev
```

## 🔗 Access Points

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:5173 | React application |
| Backend API | http://localhost:8000 | FastAPI backend |
| API Docs | http://localhost:8000/docs | Swagger/OpenAPI documentation |
| Health Check | http://localhost:8000/health | Service health status |

## 📂 Project Structure

```
my_app/
├── docs/                    # 📚 Complete documentation
├── src/                     # Frontend (React + TypeScript)
├── backend/ml-service/      # Backend (FastAPI + Python)
├── scripts/                 # Utility scripts
├── monitoring/              # Monitoring configurations
└── plans/                  # Architecture plans
```

## 🛠️ Development

**Run Tests:**
```bash
# Frontend
npm test

# Backend
cd backend/ml-service && pytest
```

**Code Quality:**
```bash
# Frontend
npm run lint
npm run type-check

# Backend
cd backend/ml-service && pylint app/
```

## 🚢 Deployment

See [Deployment Guide](docs/README.md#7-deployment-guide) for production deployment instructions.

---

**Version:** 1.0.0  
**Last Updated:** 2026-02-28
