from __future__ import annotations

from app.access import get_admin_emails, is_admin_email


def test_get_admin_emails_normalizes_and_filters(monkeypatch):
    monkeypatch.setenv('ADMIN_EMAILS', ' Admin@Mail.com, ,SECOND@MAIL.COM  ,third@mail.com ')

    assert get_admin_emails() == {
        'admin@mail.com',
        'second@mail.com',
        'third@mail.com',
    }


def test_is_admin_email_case_and_spaces(monkeypatch):
    monkeypatch.setenv('ADMIN_EMAILS', 'admin@mail.com,second@mail.com')

    assert is_admin_email('  ADMIN@mail.com ') is True
    assert is_admin_email('unknown@mail.com') is False

