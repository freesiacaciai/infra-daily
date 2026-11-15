"""일자별 기록(archive/*.json) 저장과 정적 웹사이트(site/) 생성.

사이트 구조
  site/index.html          단일 페이지 (#/YYYY-MM-DD 로 날짜 이동)
  site/data/days.json      날짜 목록 + 각 날짜 3줄 요약
  site/data/d/<날짜>.json   그날 브리핑
  site/data/search.json    전체 기간 검색용 인덱스 (요약 문장 단위)
단독 실행: python -m briefing.site  (archive만으로 사이트 재생성)
"""
from __future__ import annotations

import datetime as dt
import json
import shutil
from pathlib import Path

import yaml

ARCHIVE = Path("archive")
SITE = Path("site")
ASSET = Path(__file__).with_name("site_template.html")


def save_archive(now: dt.datetime, brief: dict, news: list[dict]) -> Path:
    ARCHIVE.mkdir(exist_ok=True)
    day = now.strftime("%Y-%m-%d")
    used = {r for s in brief.get("sections", []) for p in s["points"] for r in p.get("refs", [])}
    rec = {
        "date": day,
        "generated_at": now.isoformat(timespec="minutes"),
        "n_news": len(news),
        "fallback": brief.get("fallback_reason"),
        "top3": brief.get("top3", []),
        "sections": brief.get("sections", []),
        "watch": brief.get("watch", []),
        # 사이트에는 출처명+링크만 노출. 제목은 기록용으로만 보관.
        "refs": {n["id"]: {"s": n["source"] or "원문", "u": n["link"], "t": n["title"]}
                 for n in news if n["id"] in used},
    }
    path = ARCHIVE / f"{day}.json"
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[info] 기록 저장: {path}")
    return path


def build_site(cfg: dict) -> None:
    if SITE.exists():
        shutil.rmtree(SITE)
    (SITE / "data" / "d").mkdir(parents=True)

    days, search = [], []
    for f in sorted(ARCHIVE.glob("*.json"), reverse=True):
        rec = json.loads(f.read_text(encoding="utf-8"))
        d = rec["date"]
        refs = {k: {"s": v["s"], "u": v["u"]} for k, v in rec.get("refs", {}).items()}
        day = {k: rec.get(k) for k in ("date", "n_news", "fallback", "top3", "sections", "watch")}
        day["refs"] = refs
        (SITE / "data" / "d" / f"{d}.json").write_text(json.dumps(day, ensure_ascii=False), encoding="utf-8")
        days.append({"d": d, "top": (rec.get("top3") or [""])[0],
                     "topics": [s["topic"] for s in rec.get("sections", [])]})
        for t in rec.get("top3", []):
            search.append({"d": d, "k": "3줄", "x": t})
        for s in rec.get("sections", []):
            for p in s["points"]:
                search.append({"d": d, "k": s["topic"], "x": p["text"]})
        for w in rec.get("watch", []):
            search.append({"d": d, "k": "지켜볼 것", "x": w})

    (SITE / "data" / "days.json").write_text(json.dumps(days, ensure_ascii=False), encoding="utf-8")
    (SITE / "data" / "search.json").write_text(json.dumps(search, ensure_ascii=False), encoding="utf-8")

    nl = cfg["newsletter"]
    page = ASSET.read_text(encoding="utf-8")
    page = page.replace("{{TITLE}}", nl["title"]).replace("{{TAGLINE}}", nl.get("tagline", ""))
    (SITE / "index.html").write_text(page, encoding="utf-8")
    (SITE / ".nojekyll").write_text("")
    print(f"[info] 사이트 생성: {len(days)}일치, 검색 항목 {len(search)}개")


if __name__ == "__main__":
    build_site(yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8")))
