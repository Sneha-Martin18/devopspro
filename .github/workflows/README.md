# GitHub Actions Workflows

This directory contains automated CI/CD workflows for the Django Student Management System.

## Quick Start

### Setup Required Secrets

Go to **Settings → Secrets and variables → Actions** and add:

```
SSH_PRIVATE_KEY=<your-ssh-private-key>
SERVER_HOST=<your-server-ip-or-domain>
SERVER_USER=<ssh-username>
DEPLOY_PATH=/path/to/deployment
SLACK_WEBHOOK=<slack-webhook-url>
```

### Enable GitHub Container Registry

1. Go to **Settings → Actions → General**
2. Under "Workflow permissions", select "Read and write permissions"
3. Check "Allow GitHub Actions to create and approve pull requests"

## Available Workflows

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| **CI/CD Pipeline** | `ci-cd.yml` | Push, PR | Main pipeline for testing and building |
| **Docker Publish** | `docker-publish.yml` | Release, Manual | Publish Docker images to registry |
| **Deploy** | `deploy.yml` | Manual | Deploy to staging/production |
| **PR Checks** | `pr-checks.yml` | Pull Request | Automated PR validation |

## Workflow Details

### CI/CD Pipeline
- ✅ Code quality checks (Black, isort, Flake8)
- ✅ Unit tests for all microservices
- ✅ Docker image builds
- ✅ Security vulnerability scanning
- ✅ Integration tests
- ✅ Auto-deploy to staging/production

### Docker Publish
- 🐳 Multi-platform builds (amd64, arm64)
- 📦 Publishes to GitHub Container Registry
- 🔒 Generates SBOM for security
- 📋 Creates deployment manifest

### Deploy
- 🚀 Manual deployment control
- 🔄 Automatic rollback on failure
- 💬 Slack notifications
- ✅ Health checks

### PR Checks
- 🔍 Comprehensive code quality checks
- 🧪 Unit and integration tests
- 🐳 Docker build validation
- 📊 Coverage reporting
- 💬 Automated PR comments

## Usage Examples

### Trigger Manual Deployment
```bash
# Via GitHub UI
1. Go to Actions tab
2. Select "Deploy to Server"
3. Click "Run workflow"
4. Choose environment and version
5. Click "Run workflow"
```

### Create a Release
```bash
# Tag and push
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# Or via GitHub UI
1. Go to Releases
2. Click "Create a new release"
3. Choose tag version
4. Add release notes
5. Publish release
```

### View Workflow Status
```bash
# Check status badge in README
# Or visit: https://github.com/<owner>/<repo>/actions
```

## Status Badges

Add these to your README.md:

```markdown
![CI/CD](https://github.com/<owner>/<repo>/workflows/CI/CD%20Pipeline/badge.svg)
![Docker](https://github.com/<owner>/<repo>/workflows/Docker%20Image%20Publishing/badge.svg)
```

## Troubleshooting

### Workflow Not Running?
- Check branch protection rules
- Verify workflow file syntax (YAML)
- Check repository permissions

### Build Failing?
- Review workflow logs
- Test locally with same commands
- Check Docker/Python versions

### Deployment Failing?
- Verify SSH access to server
- Check server has Docker installed
- Verify secrets are configured

## Documentation

For detailed documentation, see [CICD_DOCUMENTATION.md](./CICD_DOCUMENTATION.md)

## Support

- 📖 [Full Documentation](./CICD_DOCUMENTATION.md)
- 🐛 [Report Issues](../../issues)
- 💬 [Discussions](../../discussions)
