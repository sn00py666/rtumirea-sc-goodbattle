from __future__ import annotations

import os


def get_admin_emails() -> set[str]:
    raw_emails = os.getenv('ADMIN_EMAILS', '')
    emails = {email.strip().lower() for email in raw_emails.split(',') if email.strip()}
    return emails


def is_admin_email(email: str) -> bool:
    return email.strip().lower() in get_admin_emails()
