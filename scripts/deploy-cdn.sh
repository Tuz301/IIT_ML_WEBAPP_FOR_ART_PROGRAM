#!/bin/bash

###############################################################################
# CDN Deployment Script
# 
# This script uploads static assets to a CDN (Cloudflare, AWS CloudFront, etc.)
# and invalidates the cache to ensure fresh content is served.
#
# Usage:
#   ./scripts/deploy-cdn.sh [cdn_provider] [environment]
#
# Examples:
#   ./scripts/deploy-cdn.sh cloudflare production
#   ./scripts/deploy-cdn.sh aws staging
###############################################################################

set -e  # Exit on error
set -u  # Exit on undefined variable

###############################################################################
# Configuration
###############################################################################

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script arguments
CDN_PROVIDER="${1:-cloudflare}"
ENVIRONMENT="${2:-production}"

# Load environment variables
if [ -f ".env.${ENVIRONMENT}" ]; then
  source ".env.${ENVIRONMENT}"
elif [ -f ".env" ]; then
  source ".env"
else
  echo -e "${RED}Error: Environment file not found${NC}"
  exit 1
fi

# Configuration variables
STATIC_DIR="${STATIC_DIR:-./public}"
CDN_ENABLED="${CDN_ENABLED:-false}"
CDN_URL="${CDN_URL:-}"

# AWS Configuration
AWS_S3_BUCKET="${AWS_S3_BUCKET:-}"
AWS_CLOUDFRONT_DISTRIBUTION="${AWS_CLOUDFRONT_DISTRIBUTION:-}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Cloudflare Configuration
CLOUDFLARE_ZONE_ID="${CLOUDFLARE_ZONE_ID:-}"
CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN:-}"

###############################################################################
# Functions
###############################################################################

log_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
  log_info "Checking requirements..."
  
  # Check if static directory exists
  if [ ! -d "$STATIC_DIR" ]; then
    log_error "Static directory not found: $STATIC_DIR"
    exit 1
  fi
  
  # Check CDN is enabled
  if [ "$CDN_ENABLED" != "true" ]; then
    log_warning "CDN is not enabled. Set CDN_ENABLED=true to deploy."
    exit 0
  fi
  
  # Check provider-specific requirements
  case "$CDN_PROVIDER" in
    cloudflare)
      if [ -z "$CLOUDFLARE_ZONE_ID" ] || [ -z "$CLOUDFLARE_API_TOKEN" ]; then
        log_error "Cloudflare credentials not configured"
        log_error "Set CLOUDFLARE_ZONE_ID and CLOUDFLARE_API_TOKEN"
        exit 1
      fi
      ;;
    aws)
      if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not installed. Install from: https://aws.amazon.com/cli/"
        exit 1
      fi
      if [ -z "$AWS_S3_BUCKET" ]; then
        log_error "AWS S3 bucket not configured. Set AWS_S3_BUCKET"
        exit 1
      fi
      ;;
    *)
      log_error "Unsupported CDN provider: $CDN_PROVIDER"
      log_error "Supported providers: cloudflare, aws"
      exit 1
      ;;
  esac
  
  log_success "All requirements met"
}

build_assets() {
  log_info "Building assets..."
  
  # Build frontend if npm is available
  if command -v npm &> /dev/null; then
    log_info "Running npm build..."
    npm run build
  fi
  
  # Optimize images if available
  if command -v imagemin &> /dev/null; then
    log_info "Optimizing images..."
    imagemin "$STATIC_DIR/**/*.{png,jpg,jpeg,gif,svg}" --out-dir="$STATIC_DIR"
  fi
  
  log_success "Assets built successfully"
}

deploy_to_aws() {
  log_info "Deploying to AWS CloudFront..."
  
  # Sync files to S3
  log_info "Syncing files to S3 bucket: $AWS_S3_BUCKET"
  aws s3 sync "$STATIC_DIR" "s3://$AWS_S3_BUCKET" \
    --region "$AWS_REGION" \
    --delete \
    --cache-control "public, max-age=31536000, immutable" \
    --metadata-directive REPLACE \
    --exclude "*.html" \
    --include "*.html" \
    --cache-control "public, max-age=0, must-revalidate"
  
  # Invalidate CloudFront cache
  if [ -n "$AWS_CLOUDFRONT_DISTRIBUTION" ]; then
    log_info "Invalidating CloudFront cache: $AWS_CLOUDFRONT_DISTRIBUTION"
    INVALIDATION_ID=$(aws cloudfront create-invalidation \
      --distribution-id "$AWS_CLOUDFRONT_DISTRIBUTION" \
      --paths "/*" \
      --query "Invalidation.Id" \
      --output text)
    
    log_success "Invalidation created: $INVALIDATION_ID"
    log_info "Wait for invalidation to complete..."
    aws cloudfront wait invalidation-completed \
      --distribution-id "$AWS_CLOUDFRONT_DISTRIBUTION" \
      --id "$INVALIDATION_ID"
  fi
  
  log_success "Deployed to AWS CloudFront"
}

deploy_to_cloudflare() {
  log_info "Deploying to Cloudflare CDN..."
  
  # Note: Cloudflare CDN works by proxying your origin server
  # This script purges the cache so new content is fetched
  
  log_info "Purging Cloudflare cache..."
  
  # Purge all cache
  RESPONSE=$(curl -s -X POST \
    "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/purge_cache" \
    -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
    -H "Content-Type: application/json" \
    --data '{"purge_everything":true}')
  
  # Check response
  SUCCESS=$(echo "$RESPONSE" | grep -o '"success":[^,]*' | cut -d':' -f2)
  
  if [ "$SUCCESS" = "true" ]; then
    log_success "Cloudflare cache purged successfully"
  else
    log_error "Failed to purge Cloudflare cache"
    echo "$RESPONSE"
    exit 1
  fi
}

verify_deployment() {
  log_info "Verifying deployment..."
  
  if [ -z "$CDN_URL" ]; then
    log_warning "CDN_URL not set, skipping verification"
    return
  fi
  
  # Check if CDN is accessible
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$CDN_URL" || echo "000")
  
  if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ]; then
    log_success "CDN is accessible (HTTP $HTTP_CODE)"
  else
    log_warning "CDN returned unexpected HTTP code: $HTTP_CODE"
  fi
  
  # Check cache headers
  log_info "Checking cache headers for sample asset..."
  HEADERS=$(curl -s -I "$CDN_URL" 2>&1 || echo "")
  
  if echo "$HEADERS" | grep -q "Cache-Control"; then
    CACHE_CONTROL=$(echo "$HEADERS" | grep -i "Cache-Control" | head -1)
    log_success "Cache headers present: $CACHE_CONTROL"
  else
    log_warning "No cache headers found"
  fi
}

print_summary() {
  echo ""
  echo "=========================================="
  echo "CDN Deployment Summary"
  echo "=========================================="
  echo "Provider:     $CDN_PROVIDER"
  echo "Environment:  $ENVIRONMENT"
  echo "Static Dir:   $STATIC_DIR"
  echo "CDN URL:      $CDN_URL"
  echo "=========================================="
  echo ""
  
  if [ "$CDN_PROVIDER" = "aws" ]; then
    echo "AWS Resources:"
    echo "  S3 Bucket:       $AWS_S3_BUCKET"
    echo "  CloudFront ID:   $AWS_CLOUDFRONT_DISTRIBUTION"
    echo "  Region:          $AWS_REGION"
  elif [ "$CDN_PROVIDER" = "cloudflare" ]; then
    echo "Cloudflare Resources:"
    echo "  Zone ID:         $CLOUDFLARE_ZONE_ID"
  fi
  echo ""
}

###############################################################################
# Main Execution
###############################################################################

main() {
  echo ""
  log_info "Starting CDN deployment..."
  echo ""
  
  print_summary
  
  # Check requirements
  check_requirements
  
  # Build assets
  build_assets
  
  # Deploy to CDN
  case "$CDN_PROVIDER" in
    aws)
      deploy_to_aws
      ;;
    cloudflare)
      deploy_to_cloudflare
      ;;
    *)
      log_error "Unsupported CDN provider: $CDN_PROVIDER"
      exit 1
      ;;
  esac
  
  # Verify deployment
  verify_deployment
  
  echo ""
  log_success "CDN deployment completed successfully!"
  echo ""
  
  # Print next steps
  echo "Next Steps:"
  echo "  1. Verify assets are accessible at: $CDN_URL"
  echo "  2. Check CDN cache hit ratio in your provider dashboard"
  echo "  3. Monitor performance using WebPageTest or GTmetrix"
  echo ""
}

# Run main function
main "$@"
