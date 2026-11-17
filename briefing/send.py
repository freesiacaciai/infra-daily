"""SMTP 발송 (기본값: Gmail 앱 비밀번호). 실패 시 원인을 로그에 남김."""
from __future__ import annotations

import os
import re
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .render import html_to_text


def _mask(addr: str) -> str:
    name, _, dom = addr.partition("@")
    return (name[:2] + "***@" + dom) if dom else "(골뱅이 없음: 전체 주소가 아님)"


def send_email(subject: str, html_body: str) -> None:
    host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    user = os.environ.get("SMTP_USER", "").strip()
    pw = os.environ.get("SMTP_PASSWORD", "").strip()
    if "gmail" in host:
        pw = pw.replace(" ", "")  # 앱 비밀번호는 공백 없이 16자리
    # 쉼표·세미콜론·공백·줄바꿈 어느 것으로 구분해도 됨
    to = [a for a in re.split(r"[,;\s]+", os.environ.get("MAIL_TO", "")) if a]

    print(f"[info] SMTP 점검: host={host} user={_mask(user)} 비밀번호 길이={len(pw)} 수신자={len(to)}명")
    problems = []
    if not user or not pw or not to:
        problems.append("SMTP_USER / SMTP_PASSWORD / MAIL_TO 중 비어 있는 값이 있음")
    if "gmail" in host and len(pw) != 16:
        problems.append(f"Gmail 앱 비밀번호는 16자리인데 {len(pw)}자리임 (일반 비밀번호를 넣었거나 잘못 붙여넣음)")
    if "gmail" in host and user and not user.lower().endswith(("@gmail.com", "@googlemail.com")):
        problems.append("SMTP_USER가 gmail.com 주소가 아님 (회사·학교 Google 계정이면 관리자가 막았을 수 있음)")
    if not pw.isascii():
        problems.append("비밀번호에 한글·전각 문자가 섞여 있음 (한/영 전환 상태 확인)")
    if problems:
        raise RuntimeError(" / ".join(problems))

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = os.getenv("MAIL_FROM", user)
    msg["To"] = msg["From"]  # 실제 수신자는 BCC
    msg.attach(MIMEText(html_to_text(html_body), "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    errors = []
    for port, mode in ((465, "SSL"), (587, "STARTTLS")):
        try:
            if mode == "SSL":
                s = smtplib.SMTP_SSL(host, port, timeout=30, context=ssl.create_default_context())
            else:
                s = smtplib.SMTP(host, port, timeout=30)
                s.ehlo()
                s.starttls(context=ssl.create_default_context())
                s.ehlo()
            with s:
                s.login(user, pw)
                s.sendmail(msg["From"], to, msg.as_string())
            print(f"[info] 발송 완료 ({mode}:{port}) → {len(to)}명")
            return
        except smtplib.SMTPAuthenticationError as e:
            detail = e.smtp_error.decode(errors="ignore") if isinstance(e.smtp_error, bytes) else str(e.smtp_error)
            errors.append(f"{mode}:{port} 인증 거부 {e.smtp_code} {detail.strip()}")
            break  # 인증 거부는 포트를 바꿔도 같음
        except Exception as e:
            errors.append(f"{mode}:{port} {type(e).__name__}: {e}")

    raise RuntimeError(
        " | ".join(errors)
        + " → 앱 비밀번호를 새로 만들어 SMTP_PASSWORD에 다시 넣고, SMTP_USER가 그 비밀번호를 만든 계정과 같은지 확인"
    )
