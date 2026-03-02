# Elastic Integrations - SOC Fork

Fork of [elastic/integrations](https://github.com/elastic/integrations) for SVA SOC multi-tenant deployments.

**Related repo:** [elastic-epr-soc](https://codehub.sva.de/sva-soc/soc-infrastructure/elastic/soc-cloud/elastic-epr-soc) (EPR deployment)

## Overview

**Purpose:** Enable Elastic integrations in multi-tenant environments where standard packages break namespace isolation.

**Problem:** Upstream integrations use `dynamic_dataset: true` flags that generate wildcard API keys (`logs-*-*`), allowing tenants to access each other's data.

**Solution:** Automated pipeline removes dynamic flags, marks affected integrations in Fleet UI, deploys patched packages to custom EPR.

**System flow:**
- Daily merge from upstream Elastic integrations
- Automated detection and removal of dynamic flags
- Modified packages deployed to staging and production EPR
- Integrations marked with `(⚠️ SVA RESTRICTED)` prefix in Kibana Fleet

**Tracking:** All modifications tracked in [DYNAMIC_DATASET_MODIFICATIONS.md](DYNAMIC_DATASET_MODIFICATIONS.md)

## Multi-Environment Architecture

Packages deploy to staging and production EPR environments:
- **Staging:** Test package changes before production rollout
- **Production:** Serves all production Elastic clusters

Deploy pipeline runs automatically for both environments when packages change.

## Pipelines

### Merge Pipeline

**Trigger:** Scheduled daily (09:00 UTC) or manual

**What it does:**
- Fetches latest from upstream `elastic/integrations`
- Merges into `main` branch (conflicts fail pipeline)
- Preserves `README.md` using git merge strategy
- Scans packages for `dynamic_dataset` and `dynamic_namespace` flags
- Invokes auto-fix script if flags detected
- Validates cleanup (fails if flags remain)
- Commits all changes (merge + flag removals)
- Triggers deploy pipeline automatically

**Auto-fix actions when flags detected:**
- Creates fix branch (`auto-fix-dynamic-flags`)
- Removes dynamic flags from data stream manifests
- Prepends `(⚠️ SVA RESTRICTED)` to integration and data stream titles
- Updates tracking file with affected integrations
- Preserves other elasticsearch settings (index templates, mappings, etc)
- Creates merge request for manual review
- **Pipeline fails intentionally** to prevent auto-merge

**Customer Center notification:**
- Pipeline failure triggers notification via GitLab "Pipeline status emails" integration
- Customer Center receives email with link to failed pipeline
- Pipeline output clearly states: "Dynamic flags detected and fixed, MR created for review"
- MR link provided in output for easy navigation
- Customer Center reviews and merges MR to complete sync

**Result:** Patched packages ready for deployment after manual MR approval

### Deploy Pipeline

**Trigger:** Package changes on `main` branch

**What it does:**
- Builds changed packages only (not all 300+)
- Deploys to staging EPR, then production EPR
- Restarts EPR containers

**Force rebuild:** `ci/force-rebuild.yml` can list packages to rebuild regardless of version changes (auto-created by merge pipeline, manually editable, auto-deleted after successful deploy)

```yaml
packages:
  - package_name_1
  - package_name_2
```

## Setup

### SOPS Encryption

SSH deploy key is encrypted using SOPS with age keys.

**Full SOPS documentation:** [elastic-clusters README - SOPS Multi-Recipient Encryption](https://codehub.sva.de/sva-soc/soc-infrastructure/elastic/soc-cloud/elastic-clusters#sops-multi-recipient-encryption)

### CI/CD Variables

Both variables are configured as **group variables** - no per-repo setup needed:
- `SOPS_AGE_KEY`: For SOPS decryption
- `GITLAB_TOKEN`: For API operations (auto-rotated)

See [elastic-clusters README - GitLab Token Auto-Rotation](https://codehub.sva.de/sva-soc/soc-infrastructure/elastic/soc-cloud/elastic-clusters#gitlab-token-auto-rotation) for token setup.

Server config is in `ci/deploy_config.py`.

### Pipeline Notifications

This repo uses the shared SOC notification infrastructure — see [elastic-clusters README - Pipeline Notification Setup](https://codehub.sva.de/sva-soc/soc-infrastructure/elastic/soc-cloud/elastic-clusters#pipeline-notification-setup) for full architecture and `SMTP_CONFIG` variable setup.

**Local specifics:**
- `merge:upstream` and `deploy:*` jobs send failure emails via `ci/notify.py`
- Severity: LOW — integration failures don't affect running clusters
- `ci/notify.py` is identical to the clusters repo version; sync changes across all three repos

### Pipeline Schedules

**Daily upstream merge:** `0 9 * * *` on main
