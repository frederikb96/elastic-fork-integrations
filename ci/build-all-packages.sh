#!/bin/bash
# Build all Elastic integration packages
# Used in GitLab CI pipeline for automated package building

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TOTAL=$(ls -d packages/*/ 2>/dev/null | wc -l)
COUNT=0
FAILED=()
SUCCESS_COUNT=0

echo "================================================================"
echo "Building $TOTAL Elastic integration packages..."
echo "================================================================"
echo ""

for package_dir in packages/*/; do
    COUNT=$((COUNT + 1))
    pkg_name=$(basename "$package_dir")

    echo "[$COUNT/$TOTAL] Building $pkg_name..."

    # Build package and capture output
    if elastic-package build -C "$package_dir" 2>&1 | tee "/tmp/build-${pkg_name}.log"; then
        echo "✓ $pkg_name built successfully"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo "✗ $pkg_name FAILED"
        FAILED+=("$pkg_name")
        # Show last 20 lines of error log
        echo "Error details (last 20 lines):"
        tail -n 20 "/tmp/build-${pkg_name}.log" || true
    fi
    echo ""
done

# Print summary
echo "================================================================"
echo "BUILD SUMMARY"
echo "================================================================"
echo "Total packages: $TOTAL"
echo "Successfully built: $SUCCESS_COUNT"
echo "Failed: ${#FAILED[@]}"

if [ ${#FAILED[@]} -gt 0 ]; then
    echo ""
    echo "❌ Failed packages:"
    printf '   - %s\n' "${FAILED[@]}"
    echo ""
    echo "Check logs in /tmp/build-*.log for details"
    exit 1
fi

echo ""
echo "✅ All $TOTAL packages built successfully!"
exit 0
