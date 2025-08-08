# Scripts Directory

This directory contains utility scripts for deployment, testing, and maintenance.

## Deployment Scripts

- **[validate-deployment.py](validate-deployment.py)** - Validates deployment configuration and components
- **[integrate-components.py](integrate-components.py)** - Integrates and tests component communication
- **[final-integration-test.py](final-integration-test.py)** - Comprehensive integration testing

## Usage

### Validate Deployment
```bash
python3 scripts/validate-deployment.py --components all
```

### Integrate Components
```bash
python3 scripts/integrate-components.py --components all
```

### Run Integration Tests
```bash
python3 scripts/final-integration-test.py
```

## Root Level Scripts

The following scripts are available in the project root:

- **[install.sh](../install.sh)** - Installation script for server and client
- **[deploy.sh](../deploy.sh)** - Docker deployment script
- **[setup.py](../setup.py)** - Python setup and configuration script
- **[build-and-push.sh](../build-and-push.sh)** - Docker image build and push
- **[test-docker.sh](../test-docker.sh)** - Docker functionality testing
- **[validate-docker.sh](../validate-docker.sh)** - Docker configuration validation
- **[ghcr-login.sh](../ghcr-login.sh)** - GitHub Container Registry login
- **[healthcheck.sh](../healthcheck.sh)** - Container health check script