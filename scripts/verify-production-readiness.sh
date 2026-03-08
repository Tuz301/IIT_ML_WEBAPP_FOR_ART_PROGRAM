#!/bin/bash

###############################################################################
# Production Readiness Verification Script
# 
# This script verifies that all production-readiness implementations are
# working correctly, including soft deletes, Sentry integration, load balancing,
# and CDN configuration.
#
# Usage:
#   ./scripts/verify-production-readiness.sh
###############################################################################

set -e  # Exit on error

###############################################################################
# Configuration
###############################################################################

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
BACKEND_DIR="./backend/ml-service"
API_URL="${API_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123}"

# Test results
PASSED=0
FAILED=0
WARNINGS=0

###############################################################################
# Functions
###############################################################################

log_header() {
  echo ""
  echo -e "${CYAN}============================================${NC}"
  echo -e "${CYAN}$1${NC}"
  echo -e "${CYAN}============================================${NC}"
  echo ""
}

log_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[✓ PASS]${NC} $1"
  ((PASSED++))
}

log_fail() {
  echo -e "${RED}[✗ FAIL]${NC} $1"
  ((FAILED++))
}

log_warning() {
  echo -e "${YELLOW}[⚠ WARN]${NC} $1"
  ((WARNINGS++))
}

print_summary() {
  echo ""
  echo -e "${CYAN}============================================${NC}"
  echo -e "${CYAN}Verification Summary${NC}"
  echo -e "${CYAN}============================================${NC}"
  echo -e "Passed:   ${GREEN}${PASSED}${NC}"
  echo -e "Failed:   ${RED}${FAILED}${NC}"
  echo -e "Warnings: ${YELLOW}${WARNINGS}${NC}"
  echo ""
  
  if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All critical checks passed!${NC}"
    return 0
  else
    echo -e "${RED}Some checks failed. Please review the output above.${NC}"
    return 1
  fi
}

###############################################################################
# Pre-flight Checks
###############################################################################

check_prerequisites() {
  log_header "Pre-flight Checks"
  
  # Check if backend is running
  log_info "Checking if backend is running..."
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/health" 2>/dev/null || echo "000")
  if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
    log_success "Backend is running at ${API_URL}"
  else
    log_fail "Backend is not running at ${API_URL} (HTTP $HTTP_CODE)"
    log_info "Start the backend with: cd backend/ml-service && python -m uvicorn app.main:app --reload"
  fi
  
  # Check if required files exist
  log_info "Checking required files..."
  
  local required_files=(
    "${BACKEND_DIR}/app/models.py"
    "${BACKEND_DIR}/app/crud.py"
    "${BACKEND_DIR}/app/sentry_integration.py"
    "${BACKEND_DIR}/app/config.py"
    "${BACKEND_DIR}/requirements.txt"
    "nginx/nginx-load-balanced.conf"
    "docker-compose.load-balanced.yml"
    "src/config/cdn.ts"
  )
  
  for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
      log_success "File exists: $file"
    else
      log_fail "File missing: $file"
    fi
  done
}

###############################################################################
# Soft Delete Verification
###############################################################################

verify_soft_deletes() {
  log_header "Soft Delete Implementation"
  
  log_info "Checking for soft delete columns in models..."
  
  # Check if deleted_at column exists in models
  if grep -q "deleted_at" "${BACKEND_DIR}/app/models.py"; then
    log_success "Soft delete columns found in models.py"
  else
    log_fail "Soft delete columns not found in models.py"
  fi
  
  # Check if soft delete utilities exist
  if [ -f "${BACKEND_DIR}/app/utils/soft_delete.py" ]; then
    log_success "Soft delete utilities module exists"
  else
    log_fail "Soft delete utilities module missing"
  fi
  
  # Check if migration file exists
  if [ -f "alembic/versions/add_soft_deletes_to_core_models.py" ]; then
    log_success "Soft delete migration file exists"
  else
    log_fail "Soft delete migration file missing"
  fi
  
  # Check if CRUD functions support soft deletes
  if grep -q "include_deleted" "${BACKEND_DIR}/app/crud.py"; then
    log_success "CRUD functions support soft delete filtering"
  else
    log_fail "CRUD functions don't support soft delete filtering"
  fi
  
  # Check if restore endpoints exist
  if grep -q "restore_deleted_patient" "${BACKEND_DIR}/app/api/patients.py"; then
    log_success "Restore endpoints exist in API"
  else
    log_fail "Restore endpoints missing from API"
  fi
}

###############################################################################
# Sentry Integration Verification
###############################################################################

verify_sentry() {
  log_header "Sentry Error Tracking"
  
  log_info "Checking Sentry integration..."
  
  # Check if Sentry integration file exists
  if [ -f "${BACKEND_DIR}/app/sentry_integration.py" ]; then
    log_success "Sentry integration module exists"
  else
    log_fail "Sentry integration module missing"
  fi
  
  # Check if Sentry is imported in main.py
  if grep -q "sentry_integration" "${BACKEND_DIR}/app/main.py"; then
    log_success "Sentry is imported in main.py"
  else
    log_fail "Sentry is not imported in main.py"
  fi
  
  # Check if Sentry configuration exists in config.py
  if grep -q "sentry_dsn" "${BACKEND_DIR}/app/config.py"; then
    log_success "Sentry configuration fields exist in config.py"
  else
    log_fail "Sentry configuration fields missing from config.py"
  fi
  
  # Check if sentry-sdk is in requirements.txt
  if grep -q "sentry-sdk" "${BACKEND_DIR}/requirements.txt"; then
    log_success "sentry-sdk is in requirements.txt"
  else
    log_fail "sentry-sdk is not in requirements.txt"
  fi
  
  # Check if Sentry is configured in .env.example
  if grep -q "SENTRY_DSN" "${BACKEND_DIR}/.env.example"; then
    log_success "Sentry configuration is documented in .env.example"
  else
    log_warning "Sentry configuration not documented in .env.example"
  fi
}

###############################################################################
# Load Balancing Verification
###############################################################################

verify_load_balancing() {
  log_header "Load Balancing Configuration"
  
  log_info "Checking load balancing setup..."
  
  # Check if nginx load balanced config exists
  if [ -f "nginx/nginx-load-balanced.conf" ]; then
    log_success "Load balanced nginx configuration exists"
  else
    log_fail "Load balanced nginx configuration missing"
  fi
  
  # Check if Docker Compose load balanced config exists
  if [ -f "docker-compose.load-balanced.yml" ]; then
    log_success "Load balanced Docker Compose configuration exists"
  else
    log_fail "Load balanced Docker Compose configuration missing"
  fi
  
  # Check if upstream has multiple servers
  if grep -q "ml-service-1:" "nginx/nginx-load-balanced.conf" 2>/dev/null; then
    log_success "Nginx configuration includes multiple backend servers"
  else
    log_warning "Nginx configuration may not include multiple backend servers"
  fi
  
  # Check if health checks are configured
  if grep -q "max_fails" "nginx/nginx-load-balanced.conf" 2>/dev/null; then
    log_success "Health checks are configured in nginx"
  else
    log_warning "Health checks may not be configured in nginx"
  fi
  
  # Check if documentation exists
  if [ -f "docs/LOAD_BALANCING_SETUP.md" ]; then
    log_success "Load balancing documentation exists"
  else
    log_warning "Load balancing documentation missing"
  fi
}

###############################################################################
# CDN Configuration Verification
###############################################################################

verify_cdn() {
  log_header "CDN Configuration"
  
  log_info "Checking CDN setup..."
  
  # Check if CDN config module exists
  if [ -f "src/config/cdn.ts" ]; then
    log_success "CDN configuration module exists"
  else
    log_fail "CDN configuration module missing"
  fi
  
  # Check if CDN deployment script exists
  if [ -f "scripts/deploy-cdn.sh" ]; then
    log_success "CDN deployment script exists"
  else
    log_warning "CDN deployment script missing"
  fi
  
  # Check if CDN is documented in .env.example
  if grep -q "CDN_ENABLED" ".env.example" 2>/dev/null || grep -q "CDN_ENABLED" "${BACKEND_DIR}/.env.example"; then
    log_success "CDN configuration is documented in .env.example"
  else
    log_warning "CDN configuration not documented in .env.example"
  fi
  
  # Check if CDN documentation exists
  if [ -f "docs/CDN_SETUP.md" ]; then
    log_success "CDN documentation exists"
  else
    log_warning "CDN documentation missing"
  fi
}

###############################################################################
# API Endpoint Verification
###############################################################################

verify_api_endpoints() {
  log_header "API Endpoint Verification"
  
  log_info "Testing critical API endpoints..."
  
  # Test health endpoint
  log_info "Testing /health endpoint..."
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/health" 2>/dev/null || echo "000")
  if [ "$HTTP_CODE" = "200" ]; then
    log_success "Health endpoint is accessible"
  else
    log_fail "Health endpoint is not accessible (HTTP $HTTP_CODE)"
  fi
  
  # Test metrics endpoint
  log_info "Testing /metrics endpoint..."
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/metrics" 2>/dev/null || echo "000")
  if [ "$HTTP_CODE" = "200" ]; then
    log_success "Metrics endpoint is accessible"
  else
    log_warning "Metrics endpoint is not accessible (HTTP $HTTP_CODE)"
  fi
  
  # Test OpenAPI docs
  log_info "Testing /docs endpoint..."
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/docs" 2>/dev/null || echo "000")
  if [ "$HTTP_CODE" = "200" ]; then
    log_success "API documentation is accessible"
  else
    log_warning "API documentation is not accessible (HTTP $HTTP_CODE)"
  fi
}

###############################################################################
# Security Verification
###############################################################################

verify_security() {
  log_header "Security Configuration"
  
  log_info "Checking security settings..."
  
  # Check if CORS is configured
  if grep -q "cors_origins" "${BACKEND_DIR}/app/config.py"; then
    log_success "CORS configuration exists"
  else
    log_fail "CORS configuration missing"
  fi
  
  # Check if JWT is configured
  if grep -q "JWT_SECRET_KEY" "${BACKEND_DIR}/.env.example"; then
    log_success "JWT configuration is documented"
  else
    log_warning "JWT configuration not documented"
  fi
  
  # Check if rate limiting is configured
  if grep -q "RATE_LIMIT" "${BACKEND_DIR}/.env.example"; then
    log_success "Rate limiting configuration is documented"
  else
    log_warning "Rate limiting configuration not documented"
  fi
}

###############################################################################
# Documentation Verification
###############################################################################

verify_documentation() {
  log_header "Documentation"
  
  log_info "Checking documentation..."
  
  local docs=(
    "docs/PRODUCTION_READINESS_ASSESSMENT.md"
    "docs/LOAD_BALANCING_SETUP.md"
    "docs/CDN_SETUP.md"
    "docs/GITHUB_SETSUP_GUIDE.md"
  )
  
  for doc in "${docs[@]}"; do
    if [ -f "$doc" ]; then
      log_success "Documentation exists: $doc"
    else
      log_warning "Documentation missing: $doc"
    fi
  done
}

###############################################################################
# Main Execution
###############################################################################

main() {
  echo ""
  echo -e "${CYAN}╔════════════════════════════════════════════════╗${NC}"
  echo -e "${CYAN}║  Production Readiness Verification            ║${NC}"
  echo -e "${CYAN}║  IIT ML Service                                ║${NC}"
  echo -e "${CYAN}╚════════════════════════════════════════════════╝${NC}"
  echo ""
  
  # Run all verification checks
  check_prerequisites
  verify_soft_deletes
  verify_sentry
  verify_load_balancing
  verify_cdn
  verify_api_endpoints
  verify_security
  verify_documentation
  
  # Print summary
  print_summary
}

# Run main function
main "$@"
