# CI/CD Pipeline Documentation

## Overview

This project uses GitHub Actions for continuous integration and deployment. The CI/CD pipeline automates testing, building, security scanning, and deployment of the Django Student Management System microservices.

## Workflows

### 1. CI/CD Pipeline (`ci-cd.yml`)

**Triggers:**
- Push to `main`, `master`, or `develop` branches
- Pull requests to `main`, `master`, or `develop` branches

**Jobs:**

#### Lint (Code Quality Checks)
- Runs Black for code formatting
- Runs isort for import sorting
- Runs Flake8 for linting
- Python version: 3.11

#### Test Services
- Runs unit tests for all 8 microservices
- Uses pytest with coverage reporting
- Matrix strategy for parallel testing
- Python versions: 3.10, 3.11

#### Build Images
- Builds Docker images for all services
- Pushes to GitHub Container Registry (ghcr.io)
- Only runs on push events
- Uses Docker BuildKit with layer caching
- Tags: branch name, commit SHA, and `latest`

#### Security Scan
- Runs Trivy vulnerability scanner
- Scans filesystem and dependencies
- Uploads results to GitHub Security tab
- Generates SARIF reports

#### Integration Tests
- Spins up PostgreSQL and Redis services
- Runs full docker-compose stack
- Tests service connectivity
- Validates health endpoints

#### Deploy to Staging
- Triggers on push to `develop` branch
- Deploys to staging environment
- Requires manual approval

#### Deploy to Production
- Triggers on push to `main` branch
- Deploys to production environment
- Requires manual approval
- Creates deployment notification

---

### 2. Docker Image Publishing (`docker-publish.yml`)

**Triggers:**
- Release published
- Manual workflow dispatch

**Features:**
- Multi-platform builds (amd64, arm64)
- Publishes to GitHub Container Registry
- Generates SBOM (Software Bill of Materials)
- Creates deployment manifest with image versions
- Semantic versioning support

**Published Images:**
```
ghcr.io/<owner>/student-management-user-management:latest
ghcr.io/<owner>/student-management-academic:latest
ghcr.io/<owner>/student-management-attendance:latest
ghcr.io/<owner>/student-management-notification:latest
ghcr.io/<owner>/student-management-leave-management:latest
ghcr.io/<owner>/student-management-feedback:latest
ghcr.io/<owner>/student-management-assessment:latest
ghcr.io/<owner>/student-management-financial:latest
ghcr.io/<owner>/student-management-api-gateway:latest
ghcr.io/<owner>/student-management-frontend:latest
```

---

### 3. Deployment Workflow (`deploy.yml`)

**Triggers:**
- Manual workflow dispatch only

**Inputs:**
- `environment`: staging or production
- `version`: tag or branch to deploy

**Process:**
1. Sets up SSH connection to server
2. Copies docker-compose.yml to server
3. Pulls latest images
4. Stops existing containers
5. Starts new containers
6. Performs health checks
7. Rolls back on failure
8. Sends Slack notification

---

### 4. Pull Request Checks (`pr-checks.yml`)

**Triggers:**
- Pull request opened, synchronized, or reopened

**Jobs:**

#### Code Quality
- Black formatting check
- isort import sorting
- Flake8 linting
- Pylint static analysis
- Bandit security scanning
- Safety dependency vulnerability check

#### Unit Tests
- Runs on Python 3.10 and 3.11
- Generates coverage reports
- Uploads to Codecov

#### Docker Build Test
- Tests Docker builds for all services
- Ensures Dockerfiles are valid
- Uses build cache

#### Integration Tests
- Starts full stack with docker-compose
- Tests service health endpoints
- Validates API connectivity

#### PR Size Check
- Warns if PR is too large (>50 files or >1000 lines)
- Encourages smaller, focused PRs

#### PR Summary Comment
- Posts CI/CD status summary to PR
- Lists all check results

---

## Required Secrets

Configure these secrets in your GitHub repository settings:

### Docker Registry
- `GITHUB_TOKEN` - Automatically provided by GitHub Actions

### Deployment
- `SSH_PRIVATE_KEY` - SSH private key for server access
- `SERVER_HOST` - Deployment server hostname/IP
- `SERVER_USER` - SSH username for deployment
- `DEPLOY_PATH` - Path on server where application is deployed

### Notifications
- `SLACK_WEBHOOK` - Slack webhook URL for deployment notifications

---

## Environment Configuration

### Staging Environment
- URL: https://staging.example.com
- Branch: `develop`
- Auto-deploy: Yes (with approval)

### Production Environment
- URL: https://example.com
- Branch: `main`
- Auto-deploy: Yes (with approval)

---

## Local Testing

### Run Linting Locally
```bash
# Install dependencies
pip install black isort flake8

# Run checks
black --check microservices/ student_management_app/
isort --check-only microservices/ student_management_app/
flake8 microservices/ student_management_app/ --config=.flake8
```

### Run Tests Locally
```bash
cd microservices/<service-name>
pip install -r requirements.txt
pytest --cov=. --cov-report=term
```

### Build Docker Images Locally
```bash
cd microservices
docker compose build
```

### Run Integration Tests Locally
```bash
cd microservices
docker compose up -d
sleep 30
curl http://localhost:8080/health
curl http://localhost:9000/
docker compose down
```

---

## Deployment Process

### Automatic Deployment
1. Merge PR to `develop` → Deploys to staging
2. Merge PR to `main` → Deploys to production

### Manual Deployment
1. Go to Actions tab in GitHub
2. Select "Deploy to Server" workflow
3. Click "Run workflow"
4. Choose environment and version
5. Click "Run workflow" button

### Rollback
If deployment fails, the workflow automatically attempts rollback. For manual rollback:
1. Run deployment workflow with previous version tag
2. Or SSH to server and run: `docker compose down && docker compose up -d`

---

## Monitoring and Logs

### View Workflow Runs
- GitHub → Actions tab
- Click on workflow run to see details
- View logs for each job

### View Container Logs
```bash
# On deployment server
cd /path/to/deployment
docker compose logs -f <service-name>
```

### Health Checks
- API Gateway: http://your-server:8080/health
- Frontend: http://your-server:9000/
- Individual services: http://your-server:<port>/health

---

## Best Practices

1. **Always create PRs** - Don't push directly to main/develop
2. **Keep PRs small** - Easier to review and test
3. **Write tests** - Maintain high code coverage
4. **Update documentation** - Keep this file current
5. **Tag releases** - Use semantic versioning (v1.0.0)
6. **Monitor deployments** - Check logs after deployment
7. **Test locally first** - Run tests and builds before pushing

---

## Troubleshooting

### Build Failures
- Check Dockerfile syntax
- Verify all dependencies in requirements.txt
- Ensure base image is accessible

### Test Failures
- Run tests locally first
- Check database migrations
- Verify environment variables

### Deployment Failures
- Check server SSH access
- Verify Docker is running on server
- Check disk space on server
- Review docker-compose.yml syntax

### Image Pull Failures
- Verify GitHub Container Registry access
- Check image tags are correct
- Ensure GITHUB_TOKEN has packages:read permission

---

## Support

For issues with CI/CD pipeline:
1. Check workflow logs in GitHub Actions
2. Review this documentation
3. Contact DevOps team
4. Create an issue in the repository

---

## Changelog

- **2025-10-20**: Initial CI/CD pipeline setup
  - Added main CI/CD workflow
  - Added Docker publishing workflow
  - Added deployment workflow
  - Added PR checks workflow
