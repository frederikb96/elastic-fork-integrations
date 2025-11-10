#!/bin/bash
# Detect changed Elastic integration packages and deploy to EPR server
# Used in GitLab CI pipeline for selective package building
#
# Environment variables required:
#   SSH_HOST_EPR       - EPR server hostname/IP
#   SSH_USER_EPR       - SSH username for EPR server
#   EPR_DEPLOY_PATH    - Deployment path on EPR server (e.g., /opt/sva-soc-epr/packages)
#
# Assumes SSH key is already configured at ~/.ssh/epr_deploy_key with host alias "epr-server"

set -e  # Exit immediately on any error
set -o pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "================================================================"
echo "Elastic Integration Packages - Selective Build and Deploy"
echo "================================================================"
echo ""

# ============================================================================
# STEP 0: Test SSH connectivity (fail fast if broken)
# ============================================================================
echo "[0/4] Testing SSH connectivity to EPR server..."

if ! ssh -o ConnectTimeout=10 epr-server "echo 'SSH connection successful'" >/dev/null 2>&1; then
    echo "❌ ERROR: Cannot connect to EPR server via SSH"
    echo ""
    echo "Troubleshooting checklist:"
    echo "  1. Check CI/CD variables are set:"
    echo "     - SSH_HOST_EPR (EPR server IP/hostname)"
    echo "     - SSH_USER_EPR (SSH username)"
    echo "     - SSH_KEY_EPR (private key content)"
    echo "  2. Verify EPR server is reachable from GitLab runner"
    echo "  3. Check firewall allows SSH from runner to EPR server"
    echo "  4. Verify SSH key has correct permissions (600)"
    echo "  5. Test manually: ssh -i ~/.ssh/epr_deploy_key \${SSH_USER_EPR}@\${SSH_HOST_EPR}"
    echo ""
    exit 1
fi

echo "✓ SSH connectivity confirmed"
echo ""

# ============================================================================
# STEP 1: Get deployed package versions from EPR server
# ============================================================================
echo "[1/4] Querying EPR server for currently deployed packages..."

DEPLOYED_VERSIONS=$(mktemp)
trap "rm -f $DEPLOYED_VERSIONS" EXIT

# SSH to EPR server and list all .zip files
# Format expected: packagename-1.2.3.zip
if ssh epr-server "ls ${EPR_DEPLOY_PATH}/*.zip 2>/dev/null" > "$DEPLOYED_VERSIONS" 2>&1; then
    DEPLOYED_COUNT=$(wc -l < "$DEPLOYED_VERSIONS" | tr -d ' ')
    echo "✓ Found $DEPLOYED_COUNT deployed packages on EPR server"
else
    echo "⚠ Warning: Could not access EPR server or no packages deployed yet"
    echo "  Will build all packages (first run?)"
    : > "$DEPLOYED_VERSIONS"  # Empty file
fi

echo ""

# ============================================================================
# STEP 2: Compare versions and detect changed packages
# ============================================================================
echo "[2/4] Detecting packages with version changes..."

CHANGED_PACKAGES=()
TOTAL_PACKAGES=0
SKIPPED_PACKAGES=0

# Temporarily disable exit-on-error for package iteration
# We want to skip problematic packages, not fail the entire job
set +e

for package_dir in packages/*/; do
    TOTAL_PACKAGES=$((TOTAL_PACKAGES + 1))
    pkg_name=$(basename "$package_dir")
    manifest="$package_dir/manifest.yml"

    # Debug: Show which package we're processing
    if [[ $((TOTAL_PACKAGES % 50)) -eq 0 ]]; then
        echo "  ... processed $TOTAL_PACKAGES packages so far"
    fi

    if [[ ! -f "$manifest" ]]; then
        echo "  ⚠ Skipping $pkg_name (no manifest.yml)"
        SKIPPED_PACKAGES=$((SKIPPED_PACKAGES + 1))
        continue
    fi

    # Extract version from manifest.yml
    # Format: "version: 1.2.3" or "version: \"1.2.3\""
    repo_version=$(grep -E '^version:' "$manifest" 2>/dev/null | head -1 | sed -E 's/^version:\s*"?([^"]+)"?/\1/' | tr -d ' ') || {
        echo "  ⚠ Skipping $pkg_name (failed to extract version from manifest)"
        SKIPPED_PACKAGES=$((SKIPPED_PACKAGES + 1))
        continue
    }

    if [[ -z "$repo_version" ]]; then
        echo "  ⚠ Skipping $pkg_name (no version in manifest)"
        SKIPPED_PACKAGES=$((SKIPPED_PACKAGES + 1))
        continue
    fi

    # Check if package is deployed and get its version
    deployed_version=""
    if [[ -s "$DEPLOYED_VERSIONS" ]]; then
        # Extract version from deployed filename: packagename-1.2.3.zip
        deployed_version=$(grep -o "/${pkg_name}-[0-9][^/]*\.zip" "$DEPLOYED_VERSIONS" 2>/dev/null | sed -E "s|/${pkg_name}-([0-9][^/]*)\.zip|\1|" | head -1) || true
    fi

    # Compare versions (simple equality check)
    if [[ -z "$deployed_version" ]]; then
        echo "  + $pkg_name: NEW (not deployed yet)"
        CHANGED_PACKAGES+=("$pkg_name")
    elif [[ "$repo_version" != "$deployed_version" ]]; then
        echo "  + $pkg_name: $deployed_version → $repo_version"
        CHANGED_PACKAGES+=("$pkg_name")
    fi
done

# Re-enable exit-on-error for subsequent steps
set -e

echo ""
echo "Summary:"
echo "  Total packages in repo: $TOTAL_PACKAGES"
echo "  Skipped packages: $SKIPPED_PACKAGES"
echo "  Changed packages: ${#CHANGED_PACKAGES[@]}"

if [[ ${#CHANGED_PACKAGES[@]} -eq 0 ]]; then
    echo ""
    echo "✅ No packages changed - nothing to build or deploy!"
    exit 0
fi

echo ""
echo "Packages to build:"
for pkg in "${CHANGED_PACKAGES[@]}"; do
    echo "  - $pkg"
done

echo ""

# ============================================================================
# STEP 3: Build changed packages
# ============================================================================
echo "[3/4] Building changed packages..."
echo ""

BUILT_PACKAGES=()
FAILED_PACKAGES=()
BUILD_COUNT=0

for pkg_name in "${CHANGED_PACKAGES[@]}"; do
    BUILD_COUNT=$((BUILD_COUNT + 1))
    echo "[$BUILD_COUNT/${#CHANGED_PACKAGES[@]}] Building $pkg_name..."

    # Build package and capture output
    if elastic-package build -C "packages/$pkg_name" 2>&1 | tee "/tmp/build-${pkg_name}.log"; then
        echo "  ✓ $pkg_name built successfully"
        BUILT_PACKAGES+=("$pkg_name")
    else
        echo "  ✗ $pkg_name FAILED"
        FAILED_PACKAGES+=("$pkg_name")
        echo ""
        echo "  Error details (last 20 lines):"
        tail -n 20 "/tmp/build-${pkg_name}.log" || true
        echo ""
        # Continue building other packages despite failure
    fi
    echo ""
done

echo "Build summary:"
echo "  Successfully built: ${#BUILT_PACKAGES[@]}"
echo "  Failed: ${#FAILED_PACKAGES[@]}"

if [[ ${#FAILED_PACKAGES[@]} -gt 0 ]]; then
    echo ""
    echo "❌ Failed packages:"
    for pkg in "${FAILED_PACKAGES[@]}"; do
        echo "  - $pkg"
    done
    echo ""
    echo "Check logs in /tmp/build-*.log for details"
    exit 1
fi

echo ""

# ============================================================================
# STEP 4: Deploy all built packages to EPR server
# ============================================================================
echo "[4/4] Deploying packages to EPR server..."
echo ""

if [[ ${#BUILT_PACKAGES[@]} -eq 0 ]]; then
    echo "⚠ No packages successfully built - nothing to deploy"
    exit 1
fi

# Rsync all built packages to EPR server
# Permission flags ensure no conflicts between different users (SSH user, root, etc)
echo "Syncing ${#BUILT_PACKAGES[@]} packages to epr-server:${EPR_DEPLOY_PATH}..."
if rsync -avh --stats \
    --chmod=D777,F666 \
    --no-owner --no-group \
    build/packages/ \
    "epr-server:${EPR_DEPLOY_PATH}/"; then
    echo ""
    echo "✅ Successfully deployed packages to EPR server!"
else
    echo ""
    echo "❌ ERROR: Failed to deploy packages to EPR server"
    exit 1
fi

echo ""
echo "================================================================"
echo "DEPLOYMENT COMPLETE"
echo "================================================================"
echo "Built and deployed ${#BUILT_PACKAGES[@]} integration packages:"
for pkg in "${BUILT_PACKAGES[@]}"; do
    echo "  ✓ $pkg"
done
echo ""
