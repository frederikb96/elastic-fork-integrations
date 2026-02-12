#!/usr/bin/env python3
"""
Merge upstream Elastic integrations and manage dynamic_dataset flags.

This script orchestrates the full merge workflow:
1. Fetches and merges upstream Elastic integrations
2. Checks for dynamic_dataset/dynamic_namespace flags
3. Creates MR for manual review if flags detected
4. Direct merge if no flags

Usage: python3 ci/merge_upstream.py
Exit codes: 0 (success), 1 (failure), 2 (flags detected, MR created)
"""

import sys

# Force unbuffered output for CI visibility
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

import os
import subprocess
import requests
from pathlib import Path
from typing import Optional, Dict

# Add parent directory to path for importing remove_dynamic_flags
sys.path.insert(0, str(Path(__file__).parent))
from remove_dynamic_flags import main as remove_flags_main


# Constants (can be overridden by environment variables)
REPO_ROOT = Path(__file__).parent.parent
FIX_BRANCH = os.getenv("FIX_BRANCH", "auto-fix-dynamic-flags")
MR_TARGET = os.getenv("MR_TARGET", "main")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))

# CI environment variables
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN", "")
CI_SERVER_HOST = os.getenv("CI_SERVER_HOST", "")
CI_PROJECT_PATH = os.getenv("CI_PROJECT_PATH", "")
CI_API_V4_URL = os.getenv("CI_API_V4_URL", "")
CI_PROJECT_ID = os.getenv("CI_PROJECT_ID", "")
CI_PROJECT_URL = os.getenv("CI_PROJECT_URL", "")
CI_PIPELINE_SOURCE = os.getenv("CI_PIPELINE_SOURCE", "schedule")

# Template paths
COMMIT_MSG_TEMPLATE = REPO_ROOT / "ci" / "templates" / "auto-fix-commit-message.txt"
MR_TEMPLATE = REPO_ROOT / "ci" / "templates" / "auto-fix-merge-request.md"


def run_command(
    cmd: list, check: bool = True, capture_output: bool = False
) -> subprocess.CompletedProcess:
    """Run shell command with error handling.

    Args:
        cmd: Command as list of strings
        check: Raise exception on non-zero exit
        capture_output: Capture stdout/stderr

    Returns:
        CompletedProcess instance

    Raises:
        subprocess.CalledProcessError: If command fails and check=True
    """
    print(f"→ Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd, check=check, capture_output=capture_output, text=True, cwd=REPO_ROOT
    )
    return result


def configure_git() -> None:
    """Configure git identity and authentication."""
    print("\nConfiguring git identity and authentication...")

    # Validate required environment variables
    if not GITLAB_TOKEN:
        raise ValueError("GITLAB_TOKEN environment variable not set")
    if not CI_SERVER_HOST:
        raise ValueError("CI_SERVER_HOST environment variable not set")
    if not CI_PROJECT_PATH:
        raise ValueError("CI_PROJECT_PATH environment variable not set")

    # Configure identity
    run_command(["git", "config", "user.email", "ci@sva.de"])
    run_command(["git", "config", "user.name", "SOC-CI"])

    # Setup authentication (GITLAB_TOKEN required for write access to protected main)
    git_url = f"https://ci:{GITLAB_TOKEN}@{CI_SERVER_HOST}/{CI_PROJECT_PATH}.git"
    print(f"→ Running: git remote set-url origin https://ci:****@{CI_SERVER_HOST}/{CI_PROJECT_PATH}.git")
    subprocess.run(
        ["git", "remote", "set-url", "origin", git_url],
        check=True, text=True, cwd=REPO_ROOT,
    )

    print("✓ Git configured")


def fetch_upstream() -> None:
    """Add and fetch upstream Elastic integrations repository."""
    print("\nFetching upstream Elastic integrations...")

    # Add upstream remote (ignore if exists)
    run_command(
        [
            "git",
            "remote",
            "add",
            "upstream",
            "https://github.com/elastic/integrations.git",
        ],
        check=False,
    )

    # Fetch both remotes
    run_command(["git", "fetch", "upstream", "main"])
    run_command(["git", "fetch", "origin", "main"])

    print("✓ Fetched upstream and origin")


def checkout_main() -> None:
    """Ensure we're on our main branch."""
    print("\nChecking out our main branch from origin...")
    run_command(["git", "checkout", "-B", "main", "origin/main"])
    print("✓ On main branch")


def prepare_fix_branch() -> bool:
    """Prepare fix branch before merge (if exists).

    Checks if fix branch exists and handles appropriately:
    - If exists and not fully merged: checkout fix branch
    - If exists and fully merged: delete it
    - If doesn't exist: stay on main

    Returns:
        True if we switched to existing fix branch, False if staying on main
    """
    print("\nChecking if fix branch exists (before merge)...")

    # Check if branch exists on remote
    result = run_command(
        ["git", "ls-remote", "--heads", "--exit-code", "origin", FIX_BRANCH],
        check=False,
        capture_output=True,
    )

    if result.returncode != 0:
        print(f"✓ Branch {FIX_BRANCH} does not exist - will stay on main")
        return False

    print(f"✓ Branch {FIX_BRANCH} exists - checking if merged...")
    run_command(["git", "fetch", "origin", FIX_BRANCH])

    # Check if branch is fully merged into target
    merge_base_result = run_command(
        ["git", "merge-base", f"origin/{MR_TARGET}", f"origin/{FIX_BRANCH}"],
        capture_output=True,
    )
    merge_base = merge_base_result.stdout.strip()

    fix_head_result = run_command(
        ["git", "rev-parse", f"origin/{FIX_BRANCH}"], capture_output=True
    )
    fix_head = fix_head_result.stdout.strip()

    if merge_base == fix_head:
        print("✓ Branch is fully merged - deleting and staying on main...")
        run_command(["git", "push", "origin", "--delete", FIX_BRANCH], check=False)
        return False
    else:
        print("✓ Branch not fully merged - checking out fix branch...")
        run_command(["git", "checkout", "-B", FIX_BRANCH, f"origin/{FIX_BRANCH}"])
        print(f"✓ Now on {FIX_BRANCH} branch")
        return True


def merge_upstream() -> bool:
    """Merge upstream/main into current branch.

    Returns:
        True if merge successful, False if conflicts
    """
    print("\nMerging upstream/main into current branch...")

    # Perform merge with --no-commit to allow README.md checkout
    result = run_command(
        ["git", "merge", "--no-commit", "--no-ff", "upstream/main"], check=False
    )

    if result.returncode != 0:
        print("❌ ERROR: Merge conflict detected!")
        print("\nConflicting files:")
        run_command(["git", "status", "--short"], check=False)
        run_command(["git", "merge", "--abort"])
        return False

    print("✓ Merge successful (no conflicts or resolved by .gitattributes)")

    # Force checkout our README.md
    print("Ensuring README.md stays ours...")
    run_command(["git", "checkout", "HEAD", "--", "README.md"])

    return True


def check_dynamic_flags() -> bool:
    """Check if dynamic flags exist in packages.

    Returns:
        True if flags found, False otherwise
    """
    print("\n" + "=" * 70)
    print("Checking for dynamic_dataset/dynamic_namespace flags...")
    print("=" * 70)

    result = run_command(
        ["grep", "-r", "dynamic_dataset.*true", "packages/"],
        check=False,
        capture_output=True,
    )

    if result.returncode == 0:
        return True

    result = run_command(
        ["grep", "-r", "dynamic_namespace.*true", "packages/"],
        check=False,
        capture_output=True,
    )

    return result.returncode == 0


def get_existing_mr() -> Optional[Dict]:
    """Check if MR already exists for fix branch.

    Returns:
        MR dict if exists, None otherwise
    """
    print("\nChecking if merge request already exists...")

    if not GITLAB_TOKEN:
        print("⚠️  WARNING: GITLAB_TOKEN not set, skipping MR check")
        return None

    url = f"{CI_API_V4_URL}/projects/{CI_PROJECT_ID}/merge_requests"
    params = {
        "state": "opened",
        "source_branch": FIX_BRANCH,
        "target_branch": MR_TARGET,
    }
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}

    try:
        response = requests.get(
            url, params=params, headers=headers, timeout=API_TIMEOUT
        )
        response.raise_for_status()
        mrs = response.json()

        if mrs:
            mr = mrs[0]
            print("✓ Merge request already exists - will update it with new changes")
            print(f"   MR: {mr.get('web_url', 'N/A')}")
            return mr
        else:
            print("✓ No existing merge request found - will create new one")
            return None

    except requests.exceptions.RequestException as e:
        print(f"⚠️  WARNING: Failed to check for existing MR: {e}")
        return None


def manage_fix_branch(mr_exists: bool) -> None:
    """Create fix branch if doesn't exist.

    This is called after merge when flags are detected. By this point,
    we're either on main (new branch needed) or already on fix branch
    (from prepare_fix_branch).

    Args:
        mr_exists: Whether MR already exists (unused now, kept for compatibility)
    """
    # Check current branch
    result = run_command(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True
    )
    current_branch = result.stdout.strip()

    if current_branch == FIX_BRANCH:
        print(f"\n✓ Already on {FIX_BRANCH} branch (prepared before merge)")
        return

    # We're on main, need to create new fix branch
    print(f"\nCreating new {FIX_BRANCH} branch...")
    run_command(["git", "checkout", "-b", FIX_BRANCH])


def run_auto_fix() -> int:
    """Run auto-fix script to remove dynamic flags.

    Returns:
        Exit code from remove_flags_main()
    """
    print("\n" + "Running auto-fix script on " + FIX_BRANCH + "...")
    print("")

    return remove_flags_main()


def validate_cleanup() -> bool:
    """Validate that all flags were removed.

    Returns:
        True if no flags remain, False otherwise
    """
    print("\nValidating cleanup...")

    result = run_command(
        ["grep", "-rq", "dynamic_dataset.*true", "packages/"], check=False
    )

    if result.returncode == 0:
        return False

    result = run_command(
        ["grep", "-rq", "dynamic_namespace.*true", "packages/"], check=False
    )

    return result.returncode != 0


def commit_and_push() -> bool:
    """Commit changes and push to fix branch.

    Returns:
        True if successful, False otherwise
    """
    # Stage modifications
    print("\nStaging modified files...")
    run_command(["git", "add", "packages/", "DYNAMIC_DATASET_MODIFICATIONS.md"])

    # Stage force-rebuild file if exists
    force_rebuild_file = REPO_ROOT / "ci" / "force-rebuild.yml"
    if force_rebuild_file.exists():
        print("  ✓ Including force-rebuild.yml")
        run_command(["git", "add", str(force_rebuild_file)])

    # Commit using template
    print(f"\nCommitting changes on {FIX_BRANCH}...")
    if not COMMIT_MSG_TEMPLATE.exists():
        raise FileNotFoundError(
            f"Commit message template not found: {COMMIT_MSG_TEMPLATE}"
        )

    result = run_command(["git", "commit", "-F", str(COMMIT_MSG_TEMPLATE)], check=False)

    if result.returncode != 0:
        print("✓ No changes to commit (already up to date)")
        return False

    print("✓ Changes committed successfully")

    # Push to fix branch
    print(f"\nPushing to origin/{FIX_BRANCH}...")
    result = run_command(["git", "push", "origin", FIX_BRANCH], check=False)

    if result.returncode != 0:
        raise RuntimeError(f"Failed to push to {FIX_BRANCH}")

    print(f"✅ Successfully pushed changes to {FIX_BRANCH}")
    return True


def create_mr() -> Optional[str]:
    """Create merge request via GitLab API.

    Returns:
        MR web URL if created, None otherwise
    """
    print("\nCreating merge request...")

    if not GITLAB_TOKEN:
        print("⚠️  WARNING: GITLAB_TOKEN not set, cannot create MR via API")
        return None

    # Validate template file exists
    if not MR_TEMPLATE.exists():
        print(f"❌ ERROR: MR template not found: {MR_TEMPLATE}")
        return None

    # Load MR description from template
    mr_description = MR_TEMPLATE.read_text()

    # Create MR via API
    url = f"{CI_API_V4_URL}/projects/{CI_PROJECT_ID}/merge_requests"
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN, "Content-Type": "application/json"}
    data = {
        "source_branch": FIX_BRANCH,
        "target_branch": MR_TARGET,
        "title": "⚠️  Auto-fix: Remove dynamic_dataset flags from upstream merge",
        "description": mr_description,
        "remove_source_branch": True,
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=API_TIMEOUT)
        response.raise_for_status()
        mr = response.json()

        web_url = mr.get("web_url")
        iid = mr.get("iid")

        if web_url:
            print(f"✅ Merge request created: {web_url}")
            return web_url
        elif iid:
            web_url = f"{CI_PROJECT_URL}/-/merge_requests/{iid}"
            print(f"✅ Merge request created: {web_url}")
            return web_url
        else:
            print("⚠️  WARNING: MR created but no URL in response")
            return None

    except requests.exceptions.RequestException as e:
        print(f"⚠️  WARNING: Failed to create merge request via API: {e}")
        print(f"   Please create MR manually from {FIX_BRANCH} to {MR_TARGET}")
        return None


def commit_merge_first() -> None:
    """Commit the merge before creating fix branch.

    This preserves MERGE_HEAD (2 parents) so git knows we merged upstream.
    Must be called BEFORE switching branches, as checkout clears MERGE_HEAD.
    """
    print("\nCommitting merge first (preserving merge history)...")

    # All merge changes are already staged by git merge --no-commit.
    # README.md was re-staged by git checkout HEAD -- README.md.
    # No git add needed — commit directly from the index.

    # Commit with merge message - this creates a proper merge commit with 2 parents
    result = run_command(
        [
            "git",
            "commit",
            "-m",
            f"Merge upstream Elastic integrations ({CI_PIPELINE_SOURCE})",
        ],
        check=False,
    )

    if result.returncode != 0:
        print("✓ No changes to commit (already up to date)")
    else:
        print("✓ Merge committed (with upstream as second parent)")


def handle_flags_detected() -> int:
    """Handle workflow when dynamic flags are detected.

    Returns:
        Exit code (2 to indicate MR workflow)
    """
    print("")
    print("⚠️  Dynamic flags detected - initiating MR workflow...")
    print("")

    # CRITICAL: Commit the merge FIRST while MERGE_HEAD still exists
    # This ensures proper merge commit with 2 parents
    # Otherwise git won't know we already merged upstream
    commit_merge_first()

    # Check if MR already exists
    existing_mr = get_existing_mr()
    mr_exists = existing_mr is not None

    # Now safe to switch branches - merge is already committed
    manage_fix_branch(mr_exists)

    # Run auto-fix script
    result = run_auto_fix()
    if result != 0:
        print("")
        print("❌ ERROR: Auto-fix script failed!")
        print("   Check script output above for details.")
        return 1

    print("")
    print("✓ Auto-fix script completed successfully")

    # Validate cleanup
    if not validate_cleanup():
        print("")
        print("❌ ERROR: Dynamic flags still present after cleanup!")
        print(
            "   The script failed to remove all flags. Manual investigation required."
        )
        return 1

    print("✅ All dynamic flags removed successfully")

    # Commit and push (if there are changes)
    pushed_new_changes = commit_and_push()

    # Create MR if doesn't exist (even if no new changes - branch may already have fixes)
    mr_web_url = None
    if not mr_exists:
        print("")
        print("Creating merge request for fix branch...")
        mr_web_url = create_mr()
    else:
        print("")
        if pushed_new_changes:
            print(
                "✓ Merge request already exists - new commit will appear automatically"
            )
        else:
            print("✓ Merge request already exists - branch is up to date")
        if existing_mr:
            mr_web_url = existing_mr.get("web_url")

    # Fail pipeline to force manual review
    print("")
    print("=" * 70)
    print("❌ PIPELINE FAILED (BY DESIGN)")
    print("=" * 70)
    print("")
    print("Dynamic flags were detected and automatically fixed.")
    print("A merge request has been created/updated for manual review.")
    print("")
    print("👉 Review and merge the MR to complete upstream sync:")
    if mr_web_url:
        print(f"   {mr_web_url}")
    else:
        print(f"   Check: {CI_PROJECT_URL}/-/merge_requests")
        print(f"   Look for MR from: {FIX_BRANCH} → {MR_TARGET}")
    print("")
    print("This pipeline failure is INTENTIONAL to prevent auto-merge.")
    print("=" * 70)

    return 2  # Exit code 2 = MR created, manual review required


def handle_no_flags() -> int:
    """Handle workflow when no dynamic flags detected.

    Returns:
        Exit code (0 on success, 1 on failure)
    """
    print("✓ No dynamic flags detected - proceeding with direct merge")
    print("=" * 70)
    print("")

    # Commit the merge
    print("Committing merge...")
    result = run_command(
        [
            "git",
            "commit",
            "-m",
            f"Auto-merge upstream Elastic integrations ({CI_PIPELINE_SOURCE})",
        ],
        check=False,
    )

    if result.returncode != 0:
        print("✓ No changes to commit (already up to date)")
        return 0

    print("✓ Merge committed successfully")

    # Push to origin
    print("\nPushing merge to origin...")
    result = run_command(["git", "push", "origin", "main"], check=False)

    if result.returncode != 0:
        print("❌ ERROR: Failed to push merge to origin")
        return 1

    print("✅ Successfully merged and pushed upstream changes!")
    print("   Deploy pipeline will automatically trigger if packages changed.")

    return 0


def main() -> int:
    """Main entry point.

    Returns:
        Exit code
    """
    print("=" * 70)
    print("Merging upstream Elastic integrations into main")
    print("=" * 70)

    try:
        # Configure git
        configure_git()

        # Fetch upstream
        fetch_upstream()

        # Checkout main
        checkout_main()

        # Prepare fix branch if it exists (BEFORE merge)
        prepare_fix_branch()

        # Merge upstream (into whichever branch we're on)
        if not merge_upstream():
            print("")
            print(
                "Please resolve conflicts manually and update .gitattributes if needed."
            )
            return 1

        # Check for dynamic flags
        flags_detected = check_dynamic_flags()

        if flags_detected:
            return handle_flags_detected()
        else:
            return handle_no_flags()

    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
