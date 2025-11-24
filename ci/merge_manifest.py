#!/usr/bin/env python3
"""Custom git merge driver for manifest.yml files.

SAFETY POLICY:
This driver ONLY resolves conflicts when the conflict is EXACTLY:
- Local modification: title field has "(⚠️ SVA RESTRICTED)" marker added
- Upstream change: version field bumped to new version
- No other conflicting changes

For ANY other conflict scenario, this driver FAILS (exits non-zero)
to let git abort the merge for manual resolution.

Git invokes this driver ONLY when a merge conflict is detected.

Arguments from git:
  %O (sys.argv[1]) - Base version (common ancestor)
  %A (sys.argv[2]) - Current version (ours - local fork)
  %B (sys.argv[3]) - Other version (theirs - upstream)
  %L (sys.argv[4]) - Conflict marker size
"""

import sys
import yaml
from pathlib import Path


def load_yaml_safe(file_path: str) -> dict:
    """Load YAML file safely, return empty dict if fails."""
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
            return data if data else {}
    except Exception as e:
        print(f"❌ ERROR: Failed to parse YAML from {file_path}: {e}", file=sys.stderr)
        return {}


def is_safe_title_version_conflict(base: dict, current: dict, other: dict) -> tuple:
    """Check if this is a safe title+version conflict that we can auto-resolve.

    Returns:
        (bool, str): (is_safe, reason_message)

    Safe conditions (ALL must be true):
    1. Title was modified locally (current != base)
    2. Title conflicts with upstream (current != other)
    3. Version was bumped upstream (other != base) [OPTIONAL if no version field]
    4. Version NOT conflicting (current == base OR current == other) [OPTIONAL if no version field]
       - Allows: version not modified locally (current == base)
       - Allows: both sides bumped to same value (current == other)
       - Rejects: both sides bumped to different values
    5. No other fields were modified locally (except title and version)

    Returns True ONLY if all conditions met.

    Note: Data stream manifests don't have version fields, so conditions 3 & 4 are skipped for them.
    """
    # Check 1: Title modified locally?
    base_title = base.get('title', '')
    current_title = current.get('title', '')
    other_title = other.get('title', '')

    if current_title == base_title:
        return False, "Title was not modified locally (no SVA RESTRICTED marker)"

    # Check 2: Title conflicts with upstream?
    if current_title == other_title:
        return False, "Title does not conflict (both sides have same value)"

    # Check 3 & 4: Version handling (optional - data stream manifests don't have version)
    base_version = base.get('version', '')
    current_version = current.get('version', '')
    other_version = other.get('version', '')

    has_version = bool(base_version or current_version or other_version)

    if has_version:
        # Package manifest with version field - validate version changes
        # Check 3: Version bumped upstream?
        if other_version == base_version:
            return False, "Version was not bumped upstream"

        # Check 4: Version conflicts (both sides modified to DIFFERENT values)?
        # Allow: version not modified locally (current == base)
        # Allow: version modified locally to SAME value as upstream (current == other)
        # Reject: version modified locally to DIFFERENT value than upstream
        if current_version != base_version and current_version != other_version:
            return False, "Version conflicts (both sides bumped to different values)"
    # else: Data stream manifest without version field - skip version checks, only title matters

    # Check 5: No other fields modified locally (except title)?
    # Compare all keys between base and current
    current_keys = set(current.keys())
    base_keys = set(base.keys())

    # Check for added/removed keys
    added_keys = current_keys - base_keys
    removed_keys = base_keys - current_keys

    if added_keys:
        return False, f"Local changes added new fields: {added_keys}"
    if removed_keys:
        return False, f"Local changes removed fields: {removed_keys}"

    # Check for modified values (excluding title and version which we already checked)
    for key in base_keys:
        if key in ('title', 'version'):
            continue  # Already validated above

        if current.get(key) != base.get(key):
            return False, f"Field '{key}' was modified locally (not just title)"

    # All safety checks passed!
    # Determine the exact scenario for logging
    if not has_version:
        scenario = "title modified locally (data stream manifest, no version field)"
    elif current_version == base_version:
        scenario = "title modified locally, version bumped upstream"
    else:
        scenario = "title modified locally, version bumped by both sides to same value"

    return True, f"Safe to merge: {scenario}"


def merge_manifest(base_file: str, current_file: str, other_file: str, marker_size: str) -> int:
    """Merge manifest files with strict safety validation.

    Returns:
        0: Merge successful (safe scenario)
        1: Merge failed (unsafe scenario or error)
    """
    print(f"\n{'='*70}")
    print("Custom Manifest Merge Driver")
    print(f"{'='*70}")
    print(f"Base:    {Path(base_file).name}")
    print(f"Current: {Path(current_file).name}")
    print(f"Other:   {Path(other_file).name}")
    print("")

    # Load all three versions
    base = load_yaml_safe(base_file)
    current = load_yaml_safe(current_file)
    other = load_yaml_safe(other_file)

    if not base or not current or not other:
        print("❌ ABORT: Failed to parse one or more YAML files")
        print("   Merge conflict requires manual resolution")
        return 1

    # Safety check: Is this the exact scenario we can auto-resolve?
    is_safe, reason = is_safe_title_version_conflict(base, current, other)

    if not is_safe:
        print("❌ ABORT: This conflict is NOT the safe title+version scenario")
        print(f"   Reason: {reason}")
        print("")
        print("   This merge conflict requires manual resolution.")
        print("   Only auto-resolving when:")
        print("     - Local change: title field only")
        print("     - Upstream change: version field only")
        return 1

    # Safe to merge! Combine local title + upstream version
    print("✅ SAFE MERGE DETECTED")
    print(f"   {reason}")
    print("")

    # Start with upstream version (other) - gets all their changes
    result = other.copy()

    # Preserve local title modification
    result['title'] = current['title']

    print("Merged values:")
    print(f"  title (local):    {current['title']}")
    print(f"  version (upstream): {other['version']}")
    print("")

    # Write merged result to current file
    try:
        with open(current_file, 'w') as f:
            yaml.dump(result, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        print("✅ Merge successful - wrote combined manifest")
        return 0
    except Exception as e:
        print(f"❌ ERROR: Failed to write merged file: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point."""
    if len(sys.argv) != 5:
        print("ERROR: Expected 4 arguments from git", file=sys.stderr)
        print("Usage: merge_manifest.py %O %A %B %L", file=sys.stderr)
        return 1

    base_file = sys.argv[1]      # %O
    current_file = sys.argv[2]   # %A
    other_file = sys.argv[3]     # %B
    marker_size = sys.argv[4]    # %L

    return merge_manifest(base_file, current_file, other_file, marker_size)


if __name__ == '__main__':
    sys.exit(main())
