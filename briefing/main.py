"""실행: python -m briefing.main [--dry-run] [--no-email] [--fixture f.json] [--date YYYY-MM-DD]

순서: 수집 → 요약 → archive/날짜.json 저장 → site/ 생성 → 메일 발송
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import yaml

from .render import WEEKDAY, render_html
from .site import build_site, save_archive
from .summarize import summarize

KST = dt.timezone(dt.timedelta(hours=9))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--dry-run", action="store_true", help="메일 대신 out/briefing.html 저장 (기록·사이트는 생성)")
    ap.add_argument("--no-email", action="store_true", help="메일 발송 생략")
    ap.add_argument("--fixture", help="수집 대신 JSON 파일 사용 (테스트용)")
    ap.add_argument("--date", help="기록 날짜 지정 YYYY-MM-DD (테스트용, 기본: 오늘 KST)")
    a = ap.parse_args()

    cfg = yaml.safe_load(Path(a.config).read_text(encoding="utf-8"))
    now = dt.datetime.now(KST)
    if a.date:
        now = dt.datetime.fromisoformat(a.date).replace(hour=6, tzinfo=KST)

    if a.fixture:
        news = json.loads(Path(a.fixture).read_text(encoding="utf-8"))["news"]
    else:
        from .collect import collect_news
        news = collect_news(cfg, now)

    brief = summarize(news, cfg)
    save_archive(now, brief, news)
    build_site(cfg)

    body = render_html(brief, news, now, cfg)
    subject = f"[{cfg['newsletter']['title']}] {now:%m/%d}({WEEKDAY[now.weekday()]})"
    if brief.get("top3"):
        subject += " " + brief["top3"][0][:40]

    if a.dry_run:
        out = Path("out")
        out.mkdir(exist_ok=True)
        (out / "briefing.html").write_text(body, encoding="utf-8")
        print(f"[info] 저장: out/briefing.html  제목: {subject}")
    elif not a.no_email:
        from .send import send_email
        send_email(subject, body)


if __name__ == "__main__":
    main()
