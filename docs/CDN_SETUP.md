# CDN Setup Guide for Static Assets

This guide explains how to configure a Content Delivery Network (CDN) for the IIT ML Service static assets to improve performance and reduce server load.

## Overview

A CDN caches static assets (images, CSS, JavaScript, fonts) on edge servers around the world, delivering them to users from the nearest location.

### Benefits

- **Reduced latency**: Content delivered from nearby edge servers
- **Lower bandwidth costs**: CDN serves cached content
- **Improved performance**: Parallel downloads from edge servers
- **High availability**: CDN provides redundancy
- **DDoS protection**: CDN absorbs attack traffic

## Supported CDN Providers

This project supports the following CDN providers:

1. **Cloudflare CDN** (Recommended - Free tier available)
2. **AWS CloudFront**
3. **Azure CDN**
4. **Google Cloud CDN**
5. **Fastly CDN**

## Quick Start - Cloudflare CDN

### 1. Create Cloudflare Account

1. Sign up at https://dash.cloudflare.com/sign-up
2. Add your domain (e.g., `yourdomain.com`)
3. Update your domain's nameservers to Cloudflare's nameservers

### 2. Configure DNS Settings

In Cloudflare DNS dashboard:

| Type | Name | Content | Proxy Status |
|------|------|---------|--------------|
| A | @ | Your server IP | Proxied (Orange cloud) |
| A | api | Your server IP | Proxied (Orange cloud) |
| A | www | Your server IP | Proxied (Orange cloud) |
| CNAME | cdn | Your bucket/domain | Proxied (Orange cloud) |

### 3. Configure Caching Rules

Go to **Caching > Caching Rules** and create rules:

#### Rule 1: Static Assets (Aggressive Caching)
```
If incoming request matches:
  - URL path contains: /static/, /assets/, /images/, /fonts/
  - File extension: .js, .css, .png, .jpg, .jpeg, .gif, .svg, .woff, .woff2, .ttf, .eot

Then:
  - Cache Level: Cache Everything
  - Edge Cache TTL: 1 year
  - Browser Cache TTL: 1 year
```

#### Rule 2: API Responses (No Caching)
```
If incoming request matches:
  - URL path contains: /v1/api/, /v1/auth/, /v1/predictions/

Then:
  - Cache Level: Bypass
  - Disable Performance
```

#### Rule 3: HTML Documents (Moderate Caching)
```
If incoming request matches:
  - File extension: .html, .htm

Then:
  - Cache Level: Standard
  - Edge Cache TTL: 2 hours
  - Browser Cache TTL: 2 hours
```

### 4. Configure Page Rules (Optional)

Go to **Rules > Page Rules** and create:

```
URL: https://yourdomain.com/*
  - Cache Level: Cache Everything
  - Edge Cache TTL: 1 month
  - Browser Cache TTL: 1 month
  - Disable Performance: OFF

URL: https://yourdomain.com/v1/api/*
  - Cache Level: Bypass
  - Disable Performance: ON

URL: https://cdn.yourdomain.com/*
  - Cache Level: Cache Everything
  - Edge Cache TTL: 1 year
  - Browser Cache TTL: 1 year
```

## AWS CloudFront Setup

### 1. Create S3 Bucket for Static Assets

```bash
# Create bucket
aws s3 mb s3://ihvn-static-assets --region us-east-1

# Enable static hosting
aws s3 website s3://ihvn-static-assets --index-document index.html

# Upload assets
aws s3 sync ./public s3://ihvn-static-assets/ --delete
```

### 2. Configure Bucket Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::ihvn-static-assets/*"
    }
  ]
}
```

### 3. Create CloudFront Distribution

Using AWS Console or CLI:

```bash
aws cloudfront create-distribution \
  --origin-domain-name ihvn-static-assets.s3.amazonaws.com \
  --default-root-object index.html \
  --default-cache-behavior \
    TargetOriginId=ihvn-static-assets \
    ViewerProtocolPolicy=redirect-to-https \
    MinTTL=31536000 \
    MaxTTL=31536000 \
    DefaultTTL=86400 \
    Compress=true \
    ForwardedValues=QueryString=false
```

### 4. Configure Cache Behaviors

Create cache behaviors for different content types:

#### Static Assets (High TTL)
- **Path Pattern**: `/static/*`, `/assets/*`, `*.js`, `*.css`
- **TTL**: Min: 31536000, Max: 31536000, Default: 86400
- **Compress**: Yes
- **Forward Query Strings**: No

#### API Responses (No Caching)
- **Path Pattern**: `/v1/api/*`, `/v1/auth/*`
- **TTL**: Min: 0, Max: 0, Default: 0
- **Forward Query Strings**: Yes
- **Forward Cookies**: All

#### HTML Documents (Moderate TTL)
- **Path Pattern**: `*.html`
- **TTL**: Min: 0, Max: 86400, Default: 3600
- **Compress**: Yes
- **Forward Query Strings**: Yes

## Nginx CDN Configuration

For self-hosted CDN or origin server configuration:

```nginx
# Static files location with CDN-friendly headers
location /static/ {
    alias /var/www/static/;
    
    # CORS for CDN
    add_header Access-Control-Allow-Origin "*";
    add_header Access-Control-Allow-Methods "GET, OPTIONS";
    add_header Access-Control-Allow-Headers "Origin, X-Requested-With, Content-Type, Accept";
    
    # Cache headers for CDN
    expires 1y;
    add_header Cache-Control "public, immutable";
    add_header X-Content-Type-Options "nosniff";
    
    # CDN cache key headers
    add_header Vary "Accept-Encoding";
    
    # Pre-compression
    gzip_static on;
    brotli_static on;
    
    access_log off;
}

# Versioned assets (cache busting)
location ~* ^/static/v[0-9]+/ {
    alias /var/www/static/;
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# Fonts with proper CORS
location ~* \.(woff|woff2|ttf|eot|otf)$ {
    alias /var/www/static/fonts/;
    expires 1y;
    add_header Cache-Control "public, immutable";
    add_header Access-Control-Allow-Origin "*";
}
```

## Application Configuration

### Update Frontend for CDN URLs

Create `src/config/cdn.ts`:

```typescript
export const CDN_CONFIG = {
  enabled: process.env.CDN_ENABLED === 'true',
  baseUrl: process.env.CDN_URL || '',
  assets: {
    images: process.env.CDN_IMAGES_URL || '/static/images/',
    fonts: process.env.CDN_FONTS_URL || '/static/fonts/',
    css: process.env.CDN_CSS_URL || '/static/css/',
    js: process.env.CDN_JS_URL || '/static/js/',
  }
};

export function getAssetUrl(path: string): string {
  if (!CDN_CONFIG.enabled || !CDN_CONFIG.baseUrl) {
    return path;
  }
  
  // Remove leading slash if present
  const cleanPath = path.startsWith('/') ? path.slice(1) : path;
  return `${CDN_CONFIG.baseUrl}/${cleanPath}`;
}
```

### Update Environment Variables

Add to `.env`:

```bash
# CDN Configuration
CDN_ENABLED=true
CDN_URL=https://cdn.yourdomain.com
CDN_IMAGES_URL=https://cdn.yourdomain.com/images/
CDN_FONTS_URL=https://cdn.yourdomain.com/fonts/
```

## Cache Invalidation

### Cloudflare Cache Purge

```bash
# Purge all cache
curl -X POST "https://api.cloudflare.com/client/v4/zones/ZONE_ID/purge_cache" \
  -H "Authorization: Bearer API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"purge_everything":true}'

# Purge specific files
curl -X POST "https://api.cloudflare.com/client/v4/zones/ZONE_ID/purge_cache" \
  -H "Authorization: Bearer API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"files":["https://yourdomain.com/static/app.js"]}'
```

### AWS CloudFront Invalidation

```bash
# Create invalidation
aws cloudfront create-invalidation \
  --distribution-id DISTRIBUTION_ID \
  --paths "/static/*" "/index.html"

# Invalidate specific files
aws cloudfront create-invalidation \
  --distribution-id DISTRIBUTION_ID \
  --paths "/static/app.js" "/static/main.css"
```

## Cache Busting Strategy

### Version-Based Caching

Use version numbers in asset URLs:

```html
<!-- Instead of -->
<link rel="stylesheet" href="/static/main.css">

<!-- Use -->
<link rel="stylesheet" href="/static/v1.2.3/main.css">
```

### Hash-Based Caching

Use content hash in filenames (Vite/Webpack):

```html
<!-- Vite automatically adds hashes -->
<link rel="stylesheet" href="/static/main.abc123.css">
<script src="/static/app.def456.js"></script>
```

### Query String Caching

Add version as query parameter:

```html
<link rel="stylesheet" href="/static/main.css?v=1.2.3">
<script src="/static/app.js?v=1.2.3"></script>
```

## Monitoring and Analytics

### Cloudflare Analytics

Access at: https://dash.cloudflare.com/analytics

Key metrics to monitor:
- **Bandwidth saved**: Amount served from cache
- **Cache hit ratio**: Percentage of requests served from cache
- **Top URLs**: Most requested assets
- **Geographic distribution**: Where requests come from

### AWS CloudWatch Metrics

For CloudFront distributions:

```bash
# Get cache statistics
aws cloudwatch get-metric-statistics \
  --namespace AWS/CloudFront \
  --metric-name CacheHitRate \
  --dimensions Name=DistributionId,Value=DISTRIBUTION_ID \
  --start-time 2024-01-01 \
  --end-time 2024-01-02 \
  --period 86400 \
  --statistics Average
```

## Security Considerations

### 1. HTTPS Only

Ensure CDN forces HTTPS:

```nginx
# Cloudflare: Always Use HTTPS = ON
# CloudFront: Viewer Protocol Policy = Redirect to HTTPS
```

### 2. CORS Configuration

For cross-origin requests:

```nginx
add_header Access-Control-Allow-Origin "https://yourdomain.com";
add_header Access-Control-Allow-Methods "GET, OPTIONS";
add_header Access-Control-Allow-Headers "Origin, X-Requested-With, Content-Type, Accept";
add_header Access-Control-Max-Age "86400";
```

### 3. Hotlink Protection

Prevent other sites from using your assets:

```nginx
# Valid referrers
valid_referers none blocked yourdomain.com *.yourdomain.com;

# Block invalid referrers
location ~* \.(gif|jpg|jpeg|png|webp|svg)$ {
    if ($invalid_referer) {
        return 403;
    }
}
```

### 4. Rate Limiting

Apply rate limits to CDN:

```nginx
# Cloudflare: Rate limiting rules
# CloudFront: Use WAF rules
```

## Performance Optimization

### 1. Image Optimization

- Use WebP format (smaller than PNG/JPEG)
- Implement responsive images with srcset
- Lazy load images below fold

### 2. Font Optimization

- Use WOFF2 format (smallest)
- Subset fonts to include only used characters
- Use font-display: swap for faster rendering

### 3. Code Optimization

- Minify JavaScript and CSS
- Use tree shaking to remove unused code
- Implement code splitting for lazy loading

### 4. Compression

Enable compression at CDN:

```nginx
# Cloudflare: Auto Minify = ON
# CloudFront: Compress = Yes
# Nginx: gzip_static on; brotli_static on;
```

## Testing

### Test CDN Configuration

```bash
# Check cache headers
curl -I https://cdn.yourdomain.com/static/app.js

# Expected output should include:
# Cache-Control: public, max-age=31536000, immutable
# X-Cache: HIT (or MISS)

# Test from multiple locations
curl -I https://cdn.yourdomain.com/static/app.js \
  -H "Origin: https://yourdomain.com" \
  -H "Access-Control-Request-Method: GET" \
  -v
```

### Performance Testing

Use tools to measure CDN performance:

- **WebPageTest**: https://www.webpagetest.org/
- **GTmetrix**: https://gtmetrix.com/
- **Google PageSpeed Insights**: https://pagespeed.web.dev/

## Cost Optimization

### Cloudflare Free Tier

- Unlimited bandwidth
- Basic DDoS protection
- SSL/TLS included
- 3 Page Rules

### AWS CloudFront Pricing

- **Data Transfer Out**: $0.085/GB (US)
- **Requests**: $0.0075/10,000 requests
- **Free Tier**: 1TB data transfer/month for 12 months

### Cost Saving Tips

1. Use Cloudflare for free CDN (up to unlimited bandwidth)
2. Enable compression to reduce data transfer
3. Use longer cache times to reduce origin requests
4. Optimize images before uploading
5. Use regional CDNs if traffic is localized

## Troubleshooting

### CDN Not Serving Latest Content

**Problem**: Changes not visible after deployment

**Solutions**:
1. Clear browser cache (Ctrl+Shift+R)
2. Purge CDN cache
3. Verify cache headers
4. Use cache busting (version/hash)

### CORS Errors

**Problem**: Browser blocks CDN resources

**Solutions**:
1. Add CORS headers to origin server
2. Configure CDN to forward CORS headers
3. Use same domain for API and assets

### High CDN Costs

**Problem**: Unexpected bandwidth costs

**Solutions**:
1. Enable compression
2. Optimize images and videos
3. Increase cache TTL
4. Use free tier CDN (Cloudflare)

## Production Checklist

- [ ] CDN configured and DNS updated
- [ ] SSL/TLS certificates installed
- [ ] Cache rules configured
- [ ] CORS headers set correctly
- [ ] Cache invalidation process documented
- [ ] Monitoring and alerts configured
- [ ] Cost limits set (if applicable)
- [ ] Backup origin configured
- [ ] Test failover to origin
- [ ] Performance baseline established

## Additional Resources

- [Cloudflare CDN Documentation](https://developers.cloudflare.com/cdn/)
- [AWS CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)
- [Google Cloud CDN Documentation](https://cloud.google.com/cdn/docs)
- [MDN Web Performance](https://developer.mozilla.org/en-US/docs/Web/Performance)
