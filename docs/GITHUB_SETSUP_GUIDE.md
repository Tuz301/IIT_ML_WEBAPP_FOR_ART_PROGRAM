# GitHub Actions Deployment Setup Guide

This guide explains how to configure GitHub secrets for your CI/CD pipelines to work correctly.

## Overview

Your project uses GitHub Actions workflows that require authentication credentials for:
- Docker Hub (for pushing container images)
- AWS (for deployment to ECS - optional, for production)
- Slack (for deployment notifications - optional)

## Required GitHub Secrets

### 1. Docker Hub Secrets (Required for CI/CD)

The workflows need Docker Hub credentials to push images.

#### Step 1: Create a Docker Hub Account
1. Go to [https://hub.docker.com/](https://hub.docker.com/)
2. Sign up for a free account if you don't have one

#### Step 2: Create an Access Token (Recommended)
Instead of using your password, create an access token:

1. Log in to Docker Hub
2. Click your username → **Account Settings**
3. Click **Security** → **New Access Token**
4. Enter a description (e.g., "GitHub Actions CI/CD")
5. Click **Generate**
6. **Copy the token immediately** - you won't see it again!

#### Step 3: Add Secrets to GitHub Repository

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following secrets:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `DOCKER_USERNAME` | Your Docker Hub username | Your Docker Hub ID |
| `DOCKER_PASSWORD` | Your Docker Hub access token | The token created in Step 2 |

5. Click **Add secret** for each one

### 2. AWS Secrets (Optional - For Production Deployment)

If you're using AWS ECS for deployment, configure these secrets:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS Access Key | IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | AWS Secret Key | IAM user secret key |
| `STAGING_SUBNETS` | Subnet IDs (comma-separated) | VPC subnet IDs for staging |
| `STAGING_SECURITY_GROUP` | Security Group ID | Security group for staging |

#### Creating AWS Credentials:
1. Go to AWS IAM Console
2. Create a new IAM user with programmatic access
3. Attach policies for ECS, EC2, and RDS access
4. Save the access key and secret key

### 3. Slack Secrets (Optional - For Notifications)

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `SLACK_WEBHOOK_URL` | Slack webhook URL | Incoming webhook URL |

#### Creating Slack Webhook:
1. Go to Slack App Directory
2. Create a new Incoming Webhooks app
3. Activate incoming webhooks
4. Copy the webhook URL

## Verifying Your Setup

After adding secrets, verify they're configured:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. You should see all secrets listed
3. Values are hidden (shown as `****`)

## Testing the Workflow

Push a commit to trigger the workflow:

```bash
git add .
git commit -m "test: trigger CI/CD workflow"
git push origin main
```

Then check the Actions tab to see if the workflow runs successfully.

## Troubleshooting

### Error: "Username and password required"
- **Cause**: `DOCKER_USERNAME` or `DOCKER_PASSWORD` secrets are missing
- **Fix**: Add both secrets in GitHub repository settings

### Error: "unauthorized: authentication required"
- **Cause**: Invalid Docker credentials or token expired
- **Fix**: Regenerate Docker Hub access token and update `DOCKER_PASSWORD` secret

### Error: "denied: requested access to the resource is denied"
- **Cause**: Docker Hub username doesn't match the image tag
- **Fix**: Ensure the image tag uses your Docker Hub username:
  ```yaml
  tags: ${{ secrets.DOCKER_USERNAME }}/iit-ml-service:latest
  ```

### Error: "no basic auth credentials"
- **Cause**: Docker login failed
- **Fix**: Verify secrets are correctly named and have valid values

## Security Best Practices

1. **Never commit secrets to your repository** - Always use GitHub Secrets
2. **Use access tokens instead of passwords** - Tokens can be revoked
3. **Rotate credentials regularly** - Update tokens every 90 days
4. **Limit token permissions** - Only grant necessary access
5. **Monitor usage** - Check Docker Hub activity logs

## Workflow Files Reference

Your project has three workflow files:

| File | Purpose | Docker Secrets Required |
|------|---------|------------------------|
| `.github/workflows/ci.yml` | CI Pipeline (lint, test) | No |
| `.github/workflows/cd.yml` | CD Pipeline (deploy) | Yes |
| `.github/workflows/ci-cd.yml` | Combined CI/CD | Yes |

## Quick Start Checklist

- [ ] Create Docker Hub account
- [ ] Generate Docker Hub access token
- [ ] Add `DOCKER_USERNAME` secret to GitHub
- [ ] Add `DOCKER_PASSWORD` secret to GitHub
- [ ] Push a commit to test the workflow
- [ ] Verify workflow runs successfully in Actions tab

## Additional Resources

- [GitHub Actions Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Docker Hub Access Tokens](https://docs.docker.com/security/for-developers/access-tokens/)
- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
