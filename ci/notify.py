#!/usr/bin/env python3
"""
Send email notifications via SMTP relay.

Reusable notification script for CI/CD pipelines. Self-contained,
stdlib-only, designed to be copied across repositories.

SMTP credentials are read from the SMTP_CONFIG environment variable
(JSON: {"user": "...", "password": "..."}).

Usage:
  python3 ci/notify.py --subject "Title" --body "Message body"
  python3 ci/notify.py --subject "Title" --body "Error details" --severity critical
  python3 ci/notify.py --subject "Title" --body "Test" --dry-run

Exit codes: 0 (sent/dry-run ok), 1 (config error), 2 (SMTP error)
"""

import argparse
import json
import os
import smtplib
import ssl
import sys
import time
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

SMTP_HOST = "217.194.138.30"
SMTP_PORT = 587
SMTP_FROM = "soc@sva.de"
SMTP_TO = "soc-servicedesk@sva.de"

SEVERITY_LABELS = {
    "low": "[LOW]",
    "normal": "[NORMAL]",
    "high": "[HIGH]",
    "critical": "[CRITICAL]",
}


def parse_smtp_config() -> dict:
    """Parse SMTP credentials from SMTP_CONFIG env var.

    Returns:
        Dict with 'user' and 'password' keys

    Raises:
        ValueError: If env var missing, empty, or malformed
    """
    raw = os.getenv("SMTP_CONFIG")
    if not raw:
        raise ValueError("SMTP_CONFIG environment variable is not set or empty")

    try:
        config = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"SMTP_CONFIG is not valid JSON: {e}")

    if not config.get("user") or not config.get("password"):
        raise ValueError("SMTP_CONFIG JSON must contain non-empty 'user' and 'password' fields")

    return config


def build_message(subject: str, body: str, severity: str) -> MIMEMultipart:
    """Build email message with metadata footer.

    Args:
        subject: Email subject line
        body: Main message body
        severity: Severity level (low/normal/high/critical)

    Returns:
        Constructed MIMEMultipart message
    """
    msg = MIMEMultipart()
    msg["From"] = SMTP_FROM
    msg["To"] = SMTP_TO

    if severity != "normal":
        msg["Subject"] = f"{SEVERITY_LABELS[severity]} {subject}"
    else:
        msg["Subject"] = subject

    parts = []
    parts.append(body)
    parts.append("")
    parts.append("---")

    pipeline_url = os.getenv("CI_PIPELINE_URL")
    if pipeline_url:
        parts.append(f"Pipeline: {pipeline_url}")

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    parts.append(f"Timestamp: {timestamp}")

    msg.attach(MIMEText("\n".join(parts), "plain"))
    return msg


def send_email(msg: MIMEMultipart, user: str, password: str) -> None:
    """Send email via SMTP with STARTTLS. One retry on transient errors.

    Args:
        msg: Email message to send
        user: SMTP username
        password: SMTP password

    Raises:
        smtplib.SMTPException: If sending fails after retry
    """
    last_error = None

    for attempt in range(2):
        if attempt > 0:
            print(f"Retrying in 5s (attempt {attempt + 1}/2)...")
            time.sleep(5)

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                server.starttls(context=context)
                server.login(user, password)
                server.send_message(msg)
            return
        except (
            smtplib.SMTPServerDisconnected,
            smtplib.SMTPConnectError,
            ConnectionError,
            TimeoutError,
        ) as e:
            last_error = e
            print(f"Transient SMTP error: {e}")
            continue
        except smtplib.SMTPAuthenticationError as e:
            raise smtplib.SMTPException(f"SMTP authentication failed: {e}")
        except smtplib.SMTPException:
            raise

    raise smtplib.SMTPException(f"SMTP send failed after 2 attempts: {last_error}")


def main() -> int:
    """Main entry point.

    Returns:
        Exit code: 0 (sent/dry-run), 1 (config error), 2 (SMTP error)
    """
    parser = argparse.ArgumentParser(description="Send email notification via SMTP relay")
    parser.add_argument("--subject", required=True, help="Email subject line")
    parser.add_argument("--body", required=True, help="Email body text")
    parser.add_argument(
        "--severity",
        choices=["low", "normal", "high", "critical"],
        default="normal",
        help="Severity level (default: normal)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config and print message without sending",
    )

    args = parser.parse_args()

    # Parse SMTP credentials
    try:
        smtp_config = parse_smtp_config()
    except ValueError as e:
        print(f"CONFIG ERROR: {e}", file=sys.stderr)
        return 1

    # Build message
    msg = build_message(args.subject, args.body, args.severity)

    if args.dry_run:
        print("=" * 70)
        print("DRY RUN - would send:")
        print("=" * 70)
        print(f"From: {SMTP_FROM}")
        print(f"To: {SMTP_TO}")
        print(f"Subject: {msg['Subject']}")
        print(f"SMTP: {SMTP_HOST}:{SMTP_PORT} (STARTTLS)")
        print(f"User: {smtp_config['user']}")
        print("-" * 70)
        print(msg.get_payload()[0].get_payload())
        print("=" * 70)
        return 0

    # Send
    try:
        send_email(msg, smtp_config["user"], smtp_config["password"])
    except smtplib.SMTPException as e:
        print(f"SMTP ERROR: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"SMTP ERROR: {e}", file=sys.stderr)
        return 2

    print(f"Email sent: {args.subject}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
