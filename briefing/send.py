"""SMTP 발송 (기본값: Gmail, 앱 비밀번호 사용)."""
from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .render import html_to_text


def send_email(subject: str, html_body: str) -> None:
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "465"))
    user = os.environ["SMTP_USER"]
    pw = os.environ["SMTP_PASSWORD"]
    to = [a.strip() for a in os.environ["MAIL_TO"].split(",") if a.strip()]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = os.getenv("MAIL_FROM", user)
    msg["To"] = msg["From"]          # 수신자는 BCC로 (서로 주소 안 보이게)
    msg.attach(MIMEText(html_to_text(html_body), "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL(host, port, timeout=30) as s:
        s.login(user, pw)
        s.sendmail(msg["From"], to, msg.as_string())
    print(f"[info] 발송 완료 → {len(to)}명")
