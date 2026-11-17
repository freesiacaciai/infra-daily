"""뉴스 수집 (Google News RSS)."""
from __future__ import annotations

import datetime as dt
import hashlib
import re
import urllib.parse

import feedparser
import requests

UA = {"User-Agent": "Mozilla/5.0 (briefing-bot)"}
LOCALES = {
    "ko": "hl=ko&gl=KR&ceid=KR:ko",
    "ja": "hl=ja&gl=JP&ceid=JP:ja",
    "en": "hl=en-US&gl=US&ceid=US:en",
}


def _id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:8]


def _norm(title: str) -> str:
    return re.sub(r"\W+", "", title.lower())[:60]


def _split_source(title: str, entry) -> tuple[str, str]:
    src = getattr(getattr(entry, "source", None), "title", "") or ""
    if src and title.endswith(" - " + src):
        title = title[: -len(src) - 3]
    elif " - " in title and not src:
        title, src = title.rsplit(" - ", 1)
    return title.strip(), src.strip()


def collect_news(cfg: dict, now: dt.datetime, hours: float | None = None) -> list[dict]:
    hours = hours or cfg["newsletter"].get("lookback_hours", 26)
    days = max(1, -(-int(hours) // 24))  # 올림
    cutoff = now - dt.timedelta(hours=hours)
    out, seen = [], set()
    for topic in cfg["topics"]:
        bucket = []
        for qd in topic["queries"]:
            q = urllib.parse.quote(f'{qd["q"]} when:{days}d')
            url = f"https://news.google.com/rss/search?q={q}&{LOCALES[qd['lang']]}"
            try:
                feed = feedparser.parse(requests.get(url, headers=UA, timeout=20).content)
            except Exception as e:  # 한 검색어 실패가 전체를 막지 않게
                print(f"[warn] RSS 실패 {topic['name']} / {qd['q']}: {e}")
                continue
            for e in feed.entries:
                pub = e.get("published_parsed")
                pub_dt = dt.datetime(*pub[:6], tzinfo=dt.timezone.utc) if pub else now
                if pub_dt < cutoff:
                    continue
                title, src = _split_source(e.get("title", ""), e)
                key = _norm(title)
                if not title or key in seen:
                    continue
                seen.add(key)
                bucket.append({
                    "id": _id(e.get("link", ""), title),
                    "topic": topic["name"],
                    "title": title,
                    "source": src,
                    "link": e.get("link", ""),
                    "published": pub_dt.isoformat(),
                    "lang": qd["lang"],
                })
        bucket.sort(key=lambda x: x["published"], reverse=True)
        out.extend(bucket[: topic.get("max_items", 20)])
        print(f"[info] {topic['name']}: {len(bucket[: topic.get('max_items', 20)])}건")
    return out
