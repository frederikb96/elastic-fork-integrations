#!/usr/bin/env python3
"""
Check GITLAB_TOKEN expiration and create issue if expiring soon.

This script monitors the GITLAB_TOKEN used for pipeline automation:
1. Queries GitLab API to get token metadata
2. Checks expiration date
3. Creates issue if token expires within 30 days
4. Pipeline fails intentionally to trigger notification

Usage: python3 ci/check_token_expiry.py
Exit codes: 0 (ok), 1 (error), 2 (expiring, issue created)
"""

import sys

# Force unbuffered output for CI visibility
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

import os
import requests
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Dict

# Constants
REPO_ROOT = Path(__file__).parent.parent
EXPIRY_WARNING_DAYS = int(os.getenv("EXPIRY_WARNING_DAYS", "30"))
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))

# CI environment variables
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN", "")
CI_API_V4_URL = os.getenv("CI_API_V4_URL", "")
CI_PROJECT_ID = os.getenv("CI_PROJECT_ID", "")
CI_PROJECT_URL = os.getenv("CI_PROJECT_URL", "")
CI_PIPELINE_URL = os.getenv("CI_PIPELINE_URL", CI_PROJECT_URL)  # Fallback to project URL

# Template path
ISSUE_TEMPLATE = REPO_ROOT / "ci" / "templates" / "token-expiry-issue.md"


def fetch_token_info() -> Dict:
    """Fetch token metadata from GitLab API.

    Returns:
        Token metadata dict with 'expires_at' field

    Raises:
        RuntimeError: If API request fails
    """
    print("\n🔍 Fetching token metadata from GitLab API...")

    if not GITLAB_TOKEN:
        raise ValueError("GITLAB_TOKEN environment variable not set")
    if not CI_API_V4_URL:
        raise ValueError("CI_API_V4_URL environment variable not set")
    if not CI_PROJECT_ID:
        raise ValueError("CI_PROJECT_ID environment variable not set")

    url = f"{CI_API_V4_URL}/personal_access_tokens/self"
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}

    try:
        response = requests.get(url, headers=headers, timeout=API_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        print(f"✓ Token metadata retrieved")
        print(f"   Name: {data.get('name', 'N/A')}")
        print(f"   Active: {data.get('active', 'N/A')}")
        print(f"   Expires: {data.get('expires_at', 'Never (service account)')}")

        return data

    except requests.exceptions.RequestException as e:
        if hasattr(e, "response") and e.response is not None:
            if e.response.status_code == 401:
                raise RuntimeError(
                    "Token authentication failed (401). Token may be invalid or revoked."
                )
            elif e.response.status_code == 404:
                raise RuntimeError(
                    "Token introspection endpoint not found (404). "
                    "GitLab instance may be older than 15.5."
                )
        raise RuntimeError(f"Failed to fetch token metadata: {e}")


def calculate_days_until_expiry(expires_at: Optional[str]) -> Optional[int]:
    """Calculate days until token expiration.

    Args:
        expires_at: ISO date string (YYYY-MM-DD) or None

    Returns:
        Days until expiry (negative if expired), None if no expiration

    Raises:
        ValueError: If date format invalid
    """
    if expires_at is None or expires_at == "":
        print("\n✓ Token has no expiration (service account or permanent token)")
        return None

    print(f"\n📅 Calculating days until expiration...")

    try:
        # Parse ISO date (YYYY-MM-DD)
        expiry_date = datetime.strptime(expires_at, "%Y-%m-%d").date()
        today = date.today()
        days_left = (expiry_date - today).days

        print(f"   Today: {today}")
        print(f"   Expires: {expiry_date}")
        print(f"   Days remaining: {days_left}")

        return days_left

    except ValueError as e:
        raise ValueError(f"Invalid date format for expires_at '{expires_at}': {e}")


def get_existing_issue() -> Optional[Dict]:
    """Check if expiry warning issue already exists.

    Returns:
        Issue dict if exists, None otherwise
    """
    print("\nChecking if expiry warning issue already exists...")

    if not GITLAB_TOKEN or not CI_API_V4_URL or not CI_PROJECT_ID:
        print("⚠️  WARNING: Missing GitLab variables, skipping issue check")
        return None

    url = f"{CI_API_V4_URL}/projects/{CI_PROJECT_ID}/issues"
    params = {
        "state": "opened",
        "labels": "token-expiry",  # More specific than text search
    }
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}

    try:
        response = requests.get(
            url, params=params, headers=headers, timeout=API_TIMEOUT
        )
        response.raise_for_status()
        issues = response.json()

        if issues:
            issue = issues[0]  # Take first match
            print("✓ Expiry warning issue already exists")
            print(f"   Issue: {issue.get('web_url', 'N/A')}")
            return issue
        else:
            print("✓ No existing issue found - will create if needed")
            return None

    except requests.exceptions.RequestException as e:
        print(f"⚠️  WARNING: Failed to check for existing issue: {e}")
        return None


def close_existing_issue(issue: Dict) -> bool:
    """Close an existing expiry warning issue.

    Args:
        issue: Issue dict with 'iid' field

    Returns:
        True if closed successfully, False otherwise
    """
    print("\nClosing resolved expiry warning issue...")

    issue_iid = issue.get("iid")
    if not issue_iid:
        print("⚠️  WARNING: Issue missing 'iid', cannot close")
        return False

    url = f"{CI_API_V4_URL}/projects/{CI_PROJECT_ID}/issues/{issue_iid}"
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
    data = {"state_event": "close"}

    try:
        response = requests.put(url, headers=headers, json=data, timeout=API_TIMEOUT)
        response.raise_for_status()

        print(f"✓ Closed issue #{issue_iid} (token expiry resolved)")
        return True

    except requests.exceptions.RequestException as e:
        print(f"⚠️  WARNING: Failed to close issue: {e}")
        return False


def create_expiry_issue(days_left: int, expires_at: str) -> Optional[str]:
    """Create GitLab issue for token expiration warning.

    Args:
        days_left: Days until token expires
        expires_at: Expiration date (YYYY-MM-DD)

    Returns:
        Issue web URL if created, None otherwise
    """
    print("\nCreating token expiry warning issue...")

    if not GITLAB_TOKEN or not CI_API_V4_URL or not CI_PROJECT_ID:
        print("⚠️  WARNING: Missing GitLab variables, cannot create issue")
        return None

    # Validate template exists
    if not ISSUE_TEMPLATE.exists():
        print(f"❌ ERROR: Issue template not found: {ISSUE_TEMPLATE}")
        return None

    # Load and format issue description
    issue_body = ISSUE_TEMPLATE.read_text().format(
        days_left=days_left, expires_at=expires_at, pipeline_url=CI_PIPELINE_URL or "N/A"
    )

    # Determine title based on urgency
    if days_left < 0:
        title = f"🚨 URGENT: GITLAB_TOKEN expired {abs(days_left)} days ago ({expires_at})"
    elif days_left == 0:
        title = f"🚨 URGENT: GITLAB_TOKEN expires TODAY ({expires_at})"
    else:
        title = f"🔐 GITLAB_TOKEN expires in {days_left} days ({expires_at})"

    # Create issue via API
    url = f"{CI_API_V4_URL}/projects/{CI_PROJECT_ID}/issues"
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN, "Content-Type": "application/json"}
    data = {
        "title": title,
        "description": issue_body,
        "labels": ["automation", "token-expiry"],
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=API_TIMEOUT)
        response.raise_for_status()
        issue = response.json()

        web_url = issue.get("web_url")
        iid = issue.get("iid")

        if web_url:
            print(f"✅ Issue created: {web_url}")
            return web_url
        elif iid:
            web_url = f"{CI_PROJECT_URL}/-/issues/{iid}"
            print(f"✅ Issue created: {web_url}")
            return web_url
        else:
            print("⚠️  WARNING: Issue created but no URL in response")
            return None

    except requests.exceptions.RequestException as e:
        print(f"⚠️  WARNING: Failed to create issue via API: {e}")
        print(f"   Please create issue manually in project")
        return None


def handle_expiring_token(days_left: int, expires_at: str, issue_web_url: str) -> int:
    """Handle pipeline failure for expiring token.

    Args:
        days_left: Days until expiry
        expires_at: Expiration date
        issue_web_url: URL to created issue

    Returns:
        Exit code (2 to trigger notification)
    """
    print("")
    print("=" * 70)
    print("❌ PIPELINE FAILED (BY DESIGN)")
    print("=" * 70)
    print("")

    if days_left <= 0:
        print(f"🚨 URGENT: GITLAB_TOKEN has EXPIRED (expired {abs(days_left)} days ago)")
    else:
        print(f"⚠️  Warning: GITLAB_TOKEN expires in {days_left} days ({expires_at})")

    print("")
    print("An issue has been created with token rotation instructions.")
    print("")
    print("👉 Follow the rotation guide in the issue:")
    if issue_web_url:
        print(f"   {issue_web_url}")
    else:
        print(f"   Check: {CI_PROJECT_URL}/-/issues")
        print(f"   Look for: 'GITLAB_TOKEN expires'")
    print("")
    print("This pipeline failure is INTENTIONAL to trigger notification.")
    print("=" * 70)

    return 2  # Exit code 2 = expiring, issue created


def main() -> int:
    """Main entry point.

    Returns:
        Exit code
    """
    print("=" * 70)
    print("Checking GITLAB_TOKEN expiration")
    print("=" * 70)

    try:
        # Fetch token metadata
        token_info = fetch_token_info()
        expires_at = token_info.get("expires_at")

        # Calculate days until expiry
        days_left = calculate_days_until_expiry(expires_at)

        # Check if already warned about expiry
        existing_issue = get_existing_issue()

        # If no expiration (service account), close any existing issue and exit
        if days_left is None:
            print("\n✅ Token has no expiration - no action needed")

            if existing_issue:
                print("   Token migrated to service account - closing old expiry warning")
                close_existing_issue(existing_issue)

            return 0

        # If token healthy (> 30 days), close any existing issue
        if days_left > EXPIRY_WARNING_DAYS:
            print(f"\n✅ Token expires in {days_left} days - healthy (> {EXPIRY_WARNING_DAYS} days)")

            if existing_issue:
                close_existing_issue(existing_issue)

            return 0

        # Token expiring soon (< 30 days) or expired
        print(
            f"\n⚠️  Token expires in {days_left} days - WARNING (< {EXPIRY_WARNING_DAYS} days)"
        )

        # If issue already exists, don't create duplicate
        if existing_issue:
            print("\n✓ Expiry warning issue already exists - notification already sent")
            print(f"   Issue: {existing_issue.get('web_url', 'N/A')}")
            return 0

        # Create new issue
        issue_web_url = create_expiry_issue(days_left, expires_at)

        # Fail pipeline to trigger notification
        return handle_expiring_token(days_left, expires_at, issue_web_url)

    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
