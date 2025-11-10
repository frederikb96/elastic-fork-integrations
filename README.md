# Elastic Integrations - SOC Fork

Fork of [elastic/integrations](https://github.com/elastic/integrations) maintained for SVA SOC multi-tenant deployments. This repository contains patched integration packages that enforce namespace isolation by removing `dynamic_dataset` flags and allowing custom integrations.

**EPR Deployment:** [elastic-epr-soc](https://codehub.sva.de/sva-soc/soc-infrastructure/elastic/elastic-epr-soc)

## Purpose

Standard Elastic integrations with `dynamic_dataset: true` generate wildcard API keys (`logs-*-*`) that break namespace boundaries in multi-tenant environments. This fork provides patched versions where:

- `dynamic_dataset` and `dynamic_namespace` flags are removed from manifests
- Integrations adjusted to support customer namespaces
- Custom Integrations can be added as needed

## Architecture

- **Branch:** `main` (tracks upstream `main` + SOC patches)
- **Upstream:** [elastic/integrations](https://github.com/elastic/integrations)
- **Deployment:** GitLab CI builds packages → deploys to custom EPR

## Automated Sync Pipeline

**Daily Schedule (09:00):** Automatically merges upstream Elastic integrations and deploys to EPR.

**Pipeline Stages:**
1. **Merge:** Pull latest from elastic/integrations `main` → merge into `main`
2. **Deploy:** Build all packages → rsync to EPR server

**How it works:**
- Upstream changes automatically merged (conflicts fail pipeline for manual resolution)
- `README.md` always preserved from `main` branch (via ephemeral `.gitattributes` created in pipeline)
- All packages built with `elastic-package`
- Deployed to `/opt/sva-soc-epr/packages/` on EPR server

## CI/CD Setup

### Required CI/CD Variables

Go to **Settings → CI/CD → Variables** and add:

1. **GITLAB_TOKEN**
   - Type: Variable
   - Value: The GitLab Personal Access Token created below
   - Flags: ✅ Protect variable, ✅ Mask variable

2. **SSH_KEY_EPR**
   - Type: Variable
   - Value: Private SSH key for EPR server access

3. **SSH_USER_EPR**

4. **SSH_HOST_EPR**

### GitLab Token Setup

1. Go to **Settings → Access Tokens**
2. Create new token:
   - Name: `CI Pipeline Token`
   - Scopes: Select **all available scopes** (to avoid permission issues)
   - Expiration: Set to maximum allowed
3. Copy token immediately
4. Add to **Settings → CI/CD → Variables** as `GITLAB_TOKEN`

### Pipeline Schedule Setup

1. Go to **CI/CD → Schedules**
2. Click **New schedule**
3. Configure:
   - Description: `Daily upstream sync and EPR deployment`
   - Interval pattern: `0 9 * * *` (09:00 UTC daily)
   - Cron timezone: UTC
   - Target branch: `main`
   - Activated: ✅
4. Save schedule

## Local Development

### Prerequisites

- Docker
- `elastic-package` CLI ([installation](https://github.com/elastic/elastic-package))

### Build Single Package

```bash
cd packages/azure
elastic-package build
```

### Build All Packages

```bash
./ci/build-all-packages.sh
```

### Deploy to EPR Manually

```bash
# After building packages
rsync -avz build/packages/ $SSH_USER_EPR@$SSH_HOST_EPR:/opt/sva-soc-epr/packages/
```
