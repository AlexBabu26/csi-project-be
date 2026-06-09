"""Lightweight admin notification helpers."""

import json
import logging
from typing import Optional
from urllib import error, request

from app.common.config import get_settings

logger = logging.getLogger(__name__)


def notify_admin_archived_member_concern(
    *,
    unit_name: str,
    member_name: str,
    archive_year: Optional[str],
    concern_text: str,
    recipient_email: Optional[str] = None,
) -> None:
    """Notify admins about a new archived member concern. Logs always; emails when configured."""
    subject = f"Archived member concern — {unit_name}"
    body = (
        f"A unit has raised a concern about an archived member.\n\n"
        f"Unit: {unit_name}\n"
        f"Member: {member_name}\n"
        f"Archive year: {archive_year or 'N/A'}\n\n"
        f"Concern:\n{concern_text}\n\n"
        f"Review in the admin portal under Change Requests → Archive Concerns."
    )
    logger.info("Archived member concern submitted: %s / %s", unit_name, member_name)

    settings = get_settings()
    to_email = recipient_email or settings.admin_notification_email
    api_key = settings.resend_api_key
    from_email = settings.mail_sender

    if not to_email or not api_key or not from_email:
        logger.info("Admin email notification skipped (missing mail configuration)")
        return

    payload = json.dumps({
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "text": body,
    }).encode("utf-8")

    req = request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=10) as response:
            logger.info("Admin concern notification sent (status %s)", response.status)
    except error.URLError as exc:
        logger.warning("Failed to send admin concern notification: %s", exc)
