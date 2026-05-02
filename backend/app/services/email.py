"""
Email notification service using Python's built-in smtplib.
Uses SMTP with STARTTLS – compatible with Gmail, SendGrid, Mailgun free tiers.

For production: swap SMTP credentials in .env.
Gmail: generate an App Password (2FA must be on).
SendGrid: use api_key as password, "apikey" as user, smtp.sendgrid.net:587.
"""

import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

import structlog

from app.core.config import settings

log = structlog.get_logger()


def _send_email_sync(to: List[str], subject: str, html_body: str) -> None:
    """Blocking SMTP send – run in executor from async context."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        log.warning("email.skipped", reason="SMTP credentials not configured", subject=subject)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = ", ".join(to)
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to, msg.as_string())
        log.info("email.sent", to=to, subject=subject)
    except Exception as exc:
        log.error("email.failed", to=to, subject=subject, exc=str(exc))


async def send_email(to: List[str], subject: str, html_body: str) -> None:
    """Non-blocking async wrapper around blocking SMTP send."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _send_email_sync, to, subject, html_body)


# ---------------------------------------------------------------------------
# Templated notifications
# ---------------------------------------------------------------------------

async def notify_new_quiz(recipients: List[str], quiz_title: str, quiz_id: int) -> None:
    subject = f"New quiz available: {quiz_title}"
    html = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
      <h2 style="color: #3b3b8f;">New Quiz on TrainMaster 🎓</h2>
      <p>A new quiz has just been published:</p>
      <h3 style="color: #1a1a1a;">{quiz_title}</h3>
      <a href="{_app_url()}/quizzes/{quiz_id}"
         style="display:inline-block;padding:12px 24px;background:#3b3b8f;color:#fff;
                border-radius:6px;text-decoration:none;font-weight:600;">
        Take the quiz
      </a>
      <p style="color:#666;font-size:12px;margin-top:24px;">
        You received this because you are registered on TrainMaster.
      </p>
    </div>
    """
    await send_email(recipients, subject, html)


async def notify_flag_reviewed(
    recipient: str, question_prompt: str, status: str
) -> None:
    subject = f"Your flag has been {status}"
    html = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
      <h2>Flag Review Result</h2>
      <p>Your flagged question:</p>
      <blockquote style="border-left:3px solid #ccc;padding-left:12px;color:#444;">
        {question_prompt}
      </blockquote>
      <p>Decision: <strong>{status.upper()}</strong></p>
      <p>{"Points have been awarded to your account." if status == "accepted" else "No changes were made."}</p>
    </div>
    """
    await send_email([recipient], subject, html)


def _app_url() -> str:
    return "https://trainmaster.app"  # override in config as needed
