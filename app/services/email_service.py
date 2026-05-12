import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    async def _send(self, to_email: str, subject: str, html: str) -> None:
        if not settings.SMTP_USER:
            logger.warning("SMTP not configured – skipping email to %s", to_email)
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html, "html"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                start_tls=True,
            )
            logger.info("Email sent to %s | subject=%s", to_email, subject)
        except Exception as exc:
            logger.error("Failed to send email to %s: %s", to_email, exc)

    async def send_verification_email(self, to_email: str, token: str) -> None:
        link = f"http://localhost:8000/api/v1/auth/verify-email?token={token}"
        await self._send(
            to_email=to_email,
            subject="Verify your email – FastAPI Auth",
            html=f"""
            <h2>Welcome! Please verify your email.</h2>
            <p>Click the link below to activate your account:</p>
            <p><a href="{link}" style="color:#4F46E5">Verify Email Address</a></p>
            <p>This link expires in <strong>24 hours</strong>.</p>
            <p>If you did not create an account, you can safely ignore this email.</p>
            """,
        )

    async def send_password_reset_email(self, to_email: str, token: str) -> None:
        link = f"http://localhost:8000/api/v1/auth/reset-password?token={token}"
        await self._send(
            to_email=to_email,
            subject="Reset your password – FastAPI Auth",
            html=f"""
            <h2>Password Reset Request</h2>
            <p>Click the link below to reset your password:</p>
            <p><a href="{link}" style="color:#4F46E5">Reset Password</a></p>
            <p>This link expires in <strong>1 hour</strong>.</p>
            <p>If you did not request a password reset, please ignore this email.</p>
            """,
        )


email_service = EmailService()
