"""실행: python -m briefing.main [--dry-run] [--no-email] [--fixture f.json] [--date YYYY-MM-DD]

순서: 수집 → 요약 → archive/날짜.json 저장 → site/ 생성 → 메일 발송
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path

import yaml

from .render import WEEKDAY, render_html
from .site import build_site, save_archive
from .summarize import summarize

KST = dt.timezone(dt.timedelta(hours=9))


def _lookback_hours(cfg: dict, now: dt.datetime) -> float:
    """직전 발행일 이후 기사를 모두 담도록 수집 기간을 늘림 (월요일·연휴 다음날 대비). 최대 5일."""
    base = cfg["newsletter"].get("lookback_hours", 26)
    prev = sorted(p.stem for p in Path("archive").glob("*.json") if p.stem < f"{now:%Y-%m-%d}")
    if not prev:
        return base
    last = dt.datetime.fromisoformat(prev[-1]).replace(hour=7, tzinfo=KST)
    hours = (now - last).total_seconds() / 3600 + 2
    return min(max(base, hours), 120)


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

    auto = os.getenv("GITHUB_EVENT_NAME") == "schedule" or os.getenv("AUTO_RUN") == "true"

    # 자동 실행은 주말·공휴일(한국) 건너뜀. 수동 실행은 언제든 가능.
    if auto and not a.date:
        import holidays
        hol = holidays.KR(years=now.year).get(now.date())
        if now.weekday() >= 5 or hol:
            print(f"[info] {now:%Y-%m-%d} {hol or '주말'} — 자동 실행 건너뜀")
            build_site(cfg)
            return

    # 예약 실행은 하루에 여러 번 걸어둔다(GitHub가 가끔 건너뛰기 때문). 이미 정상 발행된 날이면 건너뜀.
    today = Path("archive") / f"{now:%Y-%m-%d}.json"
    if auto and today.exists():
        if not json.loads(today.read_text(encoding="utf-8")).get("fallback"):
            print(f"[info] {today.name} 이미 발행됨 — 이번 예약 실행은 건너뜀")
            build_site(cfg)
            return

    if a.fixture:
        news = json.loads(Path(a.fixture).read_text(encoding="utf-8"))["news"]
    else:
        from .collect import collect_news
        news = collect_news(cfg, now, _lookback_hours(cfg, now))

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
        try:
            send_email(subject, body)
        except Exception as e:
            # 메일이 실패해도 기록 커밋·사이트 배포는 계속 진행 (Actions 요약 화면에 오류 표시)
            print(f"::error title=메일 발송 실패::{e}")
            print("[warn] 메일 발송 실패 — 기록과 사이트 배포는 계속 진행합니다.")


if __name__ == "__main__":
    main()
