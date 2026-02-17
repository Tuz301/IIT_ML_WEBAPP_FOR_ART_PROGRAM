# Backend 500 Error Diagnosis

## Error Details
- **Endpoint**: `/v1/auth/login`
- **Status Code**: 500 Internal Server Error
- **Error Location**: [`api.ts:143`](src/services/api.ts:143)

## Most Likely Root Causes

### 1. Database Not Initialized ⭐⭐⭐⭐⭐
**Probability**: Very High

**Symptoms**:
- Tables don't exist in database
- User table not created
- Relationship tables missing

**Diagnosis**:
```bash
# Check if backend is running
curl http://localhost:8000/health/

# Check database tables
# Backend logs should show: "Database tables created successfully"
```

**Fix**:
```bash
cd backend/ml-service
python -c "from app.core.db import init_database; init_database(); print('Database initialized')"
```

---

### 2. No Users in Database ⭐⭐⭐⭐⭐
**Probability**: Very High

**Symptoms**:
- Database exists but no users
- First time running the app
- Need to create initial user

**Diagnosis**:
```bash
# Check if users table exists and has records
# Backend should return user count
```

**Fix**:
```bash
cd backend/ml-service
python -c "
from app.core.db import SessionLocal
from app.models import User
from app.auth import get_password_hash

db = SessionLocal()
# Check if users exist
user_count = db.query(User).count()
print(f'Users in database: {user_count}')

if user_count == 0:
    # Create default admin user
    hashed_pw = get_password_hash('admin123')
    admin = User(
        username='admin',
        email='admin@example.com',
        hashed_password=hashed_pw,
        is_active=True,
        is_superuser=True
    )
    db.add(admin)
    db.commit()
    print('Created default admin user')
    print('Username: admin')
    print('Password: admin123')
else:
    print('Users already exist')
db.close()
"
```

---

### 3. Missing JWT Configuration ⭐⭐⭐⭐
**Probability**: High

**Symptoms**:
- JWT_SECRET_KEY not set
- Missing environment variables
- Configuration error

**Diagnosis**:
```bash
# Check .env file for JWT settings
grep JWT_SECRET .env
```

**Fix**:
Add to `.env`:
```bash
# Generate a secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env
JWT_SECRET_KEY=<generated_secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

---

### 4. Backend Not Running ⭐⭐⭐⭐
**Probability**: High

**Symptoms**:
- Connection refused
- 502 Bad Gateway
- No response from backend

**Diagnosis**:
```bash
# Check if backend is running
curl http://localhost:8000/health/

# Or check running processes
ps aux | grep uvicorn
```

**Fix**:
```bash
cd backend/ml-service

# Option 1: Run with uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Option 2: Run with docker-compose
docker-compose up -d

# Option 3: Run with Make
make dev
```

---

## Diagnostic Steps

### Step 1: Check Backend Health
```bash
curl http://localhost:8000/health/
```

Expected response:
```json
{
  "status": "healthy",
  "service": "IIT ML Service",
  "version": "1.0.0"
}
```

### Step 2: Check Backend Logs
Look for errors in backend console output:
```
- Database connection errors
- Import errors (bcrypt, python-jose)
- Configuration errors
- Table creation errors
```

### Step 3: Initialize Database
```bash
cd backend/ml-service
python init_db.py
```

### Step 4: Create Default User
```bash
cd backend/ml-service
python -c "
from app.core.db import SessionLocal
from app.models import User, Role
from app.auth import get_password_hash, create_default_roles_and_permissions

db = SessionLocal()

# Create roles
create_default_roles_and_permissions(db)

# Create admin user if not exists
admin = db.query(User).filter(User.username == 'admin').first()
if not admin:
    hashed_pw = get_password_hash('admin123')
    admin = User(
        username='admin',
        email='admin@example.com',
        hashed_password=hashed_pw,
        is_active=True,
        is_superuser=True
    )
    admin_role = db.query(Role).filter(Role.name == 'admin').first()
    if admin_role:
        admin.roles.append(admin_role)
    db.add(admin)
    db.commit()
    print('Created admin user')
    print('Username: admin')
    print('Password: admin123')
else:
    print('Admin user already exists')

db.close()
"
```

### Step 5: Test Login
```bash
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

Expected response:
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    ...
  }
}
```

---

## Quick Fix Script

Create [`backend/ml-service/fix_auth.sh`](backend/ml-service/fix_auth.sh):

```bash
#!/bin/bash
echo "🔧 Fixing IIT ML Service Authentication..."

cd backend/ml-service

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
    source venv/bin/activate
else
    echo "Virtual environment exists"
    source venv/bin/activate
fi

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Check .env file
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# Database
DATABASE_URL=sqlite:///./iit_ml_service.db

# JWT Secret (generate your own!)
JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Redis (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
CACHE_ENABLED=false
CACHE_TTL=300
EOF
fi

# Initialize database
echo "Initializing database..."
python init_db.py

# Create default admin user
echo "Creating default admin user..."
python -c "
from app.core.db import SessionLocal
from app.models import User, Role
from app.auth import get_password_hash, create_default_roles_and_permissions

db = SessionLocal()

# Create roles
try:
    create_default_roles_and_permissions(db)
    print('✓ Roles created')
except Exception as e:
    print(f'Roles might exist: {e}')

# Create admin user
admin = db.query(User).filter(User.username == 'admin').first()
if not admin:
    hashed_pw = get_password_hash('admin123')
    admin = User(
        username='admin',
        email='admin@example.com',
        hashed_password=hashed_pw,
        is_active=True,
        is_superuser=True
    )
    admin_role = db.query(Role).filter(Role.name == 'admin').first()
    if admin_role:
        admin.roles.append(admin_role)
    db.add(admin)
    db.commit()
    print('✓ Admin user created')
    print('  Username: admin')
    print('  Password: admin123')
    print('  Email: admin@example.com')
else:
    print('✓ Admin user already exists')

db.close()
"

echo ""
echo "✅ Authentication setup complete!"
echo ""
echo "You can now login with:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
echo "Starting backend server..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Make it executable and run:
```bash
chmod +x backend/ml-service/fix_auth.sh
./backend/ml-service/fix_auth.sh
```

---

## Verification

After fixing, verify the fix works:

1. **Backend Health Check**:
```bash
curl http://localhost:8000/health/
```

2. **Test Login**:
```bash
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

3. **Test Frontend Login**:
- Go to http://localhost:5173/login
- Enter username: `admin`
- Enter password: `admin123`
- Should successfully login

---

## Prevention

To prevent this in the future:

1. **Add Database Initialization to Startup**:
```python
# In main.py
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    from app.core.db import init_database, verify_database_connectivity
    
    if verify_database_connectivity():
        init_database()
    else:
        logger.error("Database not accessible, skipping initialization")
```

2. **Add Default User Creation**:
```python
# In main.py
@app.on_event("startup")
async def create_default_user():
    """Create default admin user if none exists"""
    from app.core.db import SessionLocal
    from app.models import User
    from app.auth import get_password_hash
    
    db = SessionLocal()
    user_count = db.query(User).count()
    
    if user_count == 0:
        hashed_pw = get_password_hash('admin123')
        admin = User(
            username='admin',
            email='admin@example.com',
            hashed_password=hashed_pw,
            is_active=True,
            is_superuser=True
        )
        db.add(admin)
        db.commit()
        logger.info("Created default admin user")
    
    db.close()
```

3. **Add Health Check Endpoint**:
Already exists at `/health/` - use it to verify backend status before attempting login.

---

## Summary

The 500 error on `/v1/auth/login` is most likely caused by:
1. **Database not initialized** (90% probability)
2. **No users in database** (80% probability)
3. **Missing JWT configuration** (30% probability)
4. **Backend not running** (20% probability)

Run the diagnostic script above to fix the issue and verify the backend is working before attempting to login from the frontend.
