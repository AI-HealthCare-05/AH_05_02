import asyncio
import smtplib
from email.message import EmailMessage
from urllib.parse import urlencode

from app.core import config


class PasswordResetDelivery:
    async def send(self, email: str, token: str) -> None:
        if not config.SMTP_HOST or not config.SMTP_FROM_EMAIL:
            raise RuntimeError("SMTP configuration is missing")
        await asyncio.to_thread(self._send_sync, email, token)

    @staticmethod
    def _send_sync(email: str, token: str) -> None:
        query = urlencode({"reset_token": token})
        url = f"{config.FRONTEND_BASE_URL.rstrip('/')}/?{query}"
        message = EmailMessage()
        message["Subject"] = "[간당간당] 비밀번호 재설정 안내"
        message["From"] = config.SMTP_FROM_EMAIL
        message["To"] = email
        message.set_content(
            "비밀번호 재설정을 요청했습니다. 30분 안에 아래 주소를 이용해 주세요.\n\n"
            f"{url}\n\n요청하지 않았다면 이 메일을 무시해 주세요."
        )
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as smtp:
            if config.SMTP_USE_TLS:
                smtp.starttls()
            if config.SMTP_USERNAME:
                smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            smtp.send_message(message)
