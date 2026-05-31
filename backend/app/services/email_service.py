"""SMTP email delivery service.

A thin async abstraction over the stdlib ``smtplib`` used by all transactional
email flows (verification, password reset, ...). Network I/O is delegated to a
worker thread so it never blocks the event loop.

When ``SMTP_HOST`` is not configured the service runs in *console mode*: rendered
messages are logged instead of sent, so the template works out of the box during
local development.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Sends transactional emails over SMTP (or logs them in console mode)."""

    def __init__(self) -> None:
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.use_tls = settings.SMTP_USE_TLS
        self.use_ssl = settings.SMTP_USE_SSL
        self.timeout = settings.SMTP_TIMEOUT
        self.from_address = settings.EMAIL_FROM
        self.from_name = settings.EMAIL_FROM_NAME

    @property
    def is_configured(self) -> bool:
        return bool(self.host)

    def _build_message(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: str | None,
    ) -> EmailMessage:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = formataddr((self.from_name, self.from_address))
        message["To"] = to
        message.set_content(text_body or _html_to_text(html_body))
        message.add_alternative(html_body, subtype="html")
        return message

    def _send_sync(self, message: EmailMessage) -> None:
        context = ssl.create_default_context()
        if self.use_ssl:
            with smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout, context=context) as server:
                self._authenticate_and_send(server, message)
        else:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
                if self.use_tls:
                    server.starttls(context=context)
                self._authenticate_and_send(server, message)

    def _authenticate_and_send(self, server: smtplib.SMTP, message: EmailMessage) -> None:
        if self.username and self.password:
            server.login(self.username, self.password)
        server.send_message(message)

    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> None:
        """Send an email. In console mode the message is logged instead of sent."""
        message = self._build_message(to, subject, html_body, text_body)

        if not self.is_configured:
            logger.info(
                "[email:console] SMTP not configured; message not sent.\n"
                "To: %s\nSubject: %s\n%s",
                to,
                subject,
                text_body or _html_to_text(html_body),
            )
            return

        try:
            await asyncio.to_thread(self._send_sync, message)
            logger.info("Email sent", extra={"to": to, "subject": subject})
        except Exception:  # noqa: BLE001 - log and re-raise as a clean error
            logger.exception("Failed to send email", extra={"to": to, "subject": subject})
            raise

    async def send_verification_email(self, to: str, username: str, verify_url: str) -> None:
        subject = f"Verify your {self.from_name} account"
        html_body = _render_action_email(
            heading="Confirm your email address",
            greeting=f"Hi {username},",
            body=(
                "Thanks for signing up. Please confirm your email address to "
                "activate your account. This link expires soon."
            ),
            button_label="Verify email",
            action_url=verify_url,
        )
        await self.send_email(to, subject, html_body)

    async def send_password_reset_email(self, to: str, username: str, reset_url: str) -> None:
        subject = f"Reset your {self.from_name} password"
        html_body = _render_action_email(
            heading="Reset your password",
            greeting=f"Hi {username},",
            body=(
                "We received a request to reset your password. Click the button "
                "below to choose a new one. If you didn't request this, you can "
                "safely ignore this email."
            ),
            button_label="Reset password",
            action_url=reset_url,
        )
        await self.send_email(to, subject, html_body)


def _html_to_text(html: str) -> str:
    """Very small HTML→text fallback for the plaintext alternative part."""
    import re

    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|h[1-6]|tr)>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _render_action_email(
    *,
    heading: str,
    greeting: str,
    body: str,
    button_label: str,
    action_url: str,
) -> str:
    return f"""\
<!DOCTYPE html>
<html>
  <body style="margin:0;padding:0;background:#f1f5f9;font-family:Arial,Helvetica,sans-serif;color:#0f172a;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="padding:32px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="480" cellpadding="0" cellspacing="0"
                 style="background:#ffffff;border-radius:16px;overflow:hidden;">
            <tr>
              <td style="padding:32px 32px 8px 32px;">
                <h1 style="margin:0;font-size:20px;color:#2563eb;">{heading}</h1>
              </td>
            </tr>
            <tr>
              <td style="padding:8px 32px 0 32px;font-size:14px;line-height:22px;">
                <p style="margin:0 0 12px 0;">{greeting}</p>
                <p style="margin:0 0 24px 0;">{body}</p>
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 8px 32px;">
                <a href="{action_url}"
                   style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;
                          padding:12px 24px;border-radius:9999px;font-size:14px;font-weight:bold;">
                  {button_label}
                </a>
              </td>
            </tr>
            <tr>
              <td style="padding:16px 32px 32px 32px;font-size:12px;color:#64748b;line-height:18px;">
                <p style="margin:0 0 8px 0;">If the button doesn't work, copy and paste this link:</p>
                <p style="margin:0;word-break:break-all;"><a href="{action_url}" style="color:#2563eb;">{action_url}</a></p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


# Module-level singleton used across the app.
email_service = EmailService()
