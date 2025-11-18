# Elastic Integrations - SOC Fork

Fork of [elastic/integrations](https://github.com/elastic/integrations) for SVA SOC multi-tenant deployments.

**Related repo:** [elastic-epr-soc](https://codehub.sva.de/sva-soc/soc-infrastructure/elastic/elastic-epr-soc) (EPR deployment)

## Overview

**Purpose:** Enable Elastic integrations in multi-tenant environments where standard packages break namespace isolation.

**Problem:** Upstream integrations use `dynamic_dataset: true` flags that generate wildcard API keys (`logs-*-*`), allowing tenants to access each other's data.

**Solution:** Automated pipeline removes dynamic flags, marks affected integrations in Fleet UI, deploys patched packages to custom EPR.

**System flow:**
- Daily merge from upstream Elastic integrations
- Automated detection and removal of dynamic flags
- Modified packages deployed to EPR
- Integrations marked with `(⚠️ SVA RESTRICTED)` prefix in Kibana Fleet

**Tracking:** All modifications tracked in [DYNAMIC_DATASET_MODIFICATIONS.md](DYNAMIC_DATASET_MODIFICATIONS.md)

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

**Auto-fix actions:**
- Removes dynamic flags from data stream manifests
- Prepends `(⚠️ SVA RESTRICTED)` to integration and data stream titles
- Updates tracking file with affected integrations
- Preserves other elasticsearch settings (index templates, mappings, etc)

**Result:** Patched packages ready for deployment, changes visible in git history

### Deploy Pipeline

**Trigger:** Package changes on `main` branch (NOT scheduled)

**What it does:**
- Detects which packages changed since last deployment
- Builds changed packages using `elastic-package`
- Deploys to EPR server via rsync
- Restarts EPR container to load new packages

**Optimization:** Only rebuilds changed packages (not all 300+ integrations)

**Result:** EPR serves updated integration packages to Fleet

## Details

### CI/CD Setup

Required GitLab CI/CD variables (Settings → CI/CD → Variables):

- `GITLAB_TOKEN` - Personal Access Token with all scopes (for git push operations)
- `SSH_KEY_EPR` - Private SSH key for EPR server access
- `SSH_USER_EPR` - SSH username for EPR server
- `SSH_HOST_EPR` - EPR server hostname/IP

**GitLab token creation:**
- Settings → Access Tokens → New token
- Scopes: All available
- Expiration: Maximum allowed
- Add as `GITLAB_TOKEN` variable with Protect + Mask flags

**Pipeline schedule:**
- CI/CD → Schedules → New schedule
- Pattern: `0 9 * * *` (daily 09:00 UTC)
- Target: `main` branch

### Local Development

**Prerequisites:** Docker, `elastic-package` CLI ([install guide](https://github.com/elastic/elastic-package))

**Build single package:**
```bash
cd packages/<package-name>
elastic-package build
```

**Build all packages:**
```bash
./ci/build-all-packages.sh
```

**Test package locally:**
```bash
cd packages/<package-name>
elastic-package test pipeline
elastic-package test static
```

**Deploy manually:**
```bash
# After building packages
rsync -avz build/packages/ $SSH_USER_EPR@$SSH_HOST_EPR:/opt/sva-soc-epr/packages/
```

### Troubleshooting

**Pipeline fails after merge:**
- Check pipeline logs for merge conflicts
- Resolve manually: `git fetch origin && git merge upstream/main`
- Update `.gitattributes` if new files need "ours" strategy

**Auto-fix script fails:**
- Check `ci/remove-dynamic-flags.py` error output
- Verify YAML structure in affected package manifests
- Common issue: Malformed elasticsearch section

**Flags remain after auto-fix:**
- Pipeline will fail with specific error
- Investigate affected package manually

**Deploy pipeline skips packages:**
- Check `ci/detect-and-deploy.py` logic
- Verify git history shows package changes
- May need to force rebuild specific package

**EPR doesn't serve new packages:**
- Verify rsync completed successfully
- Check EPR container logs: `docker logs elastic-package-registry-soc`
- Restart EPR manually if needed
