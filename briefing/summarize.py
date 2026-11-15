"""LLM 요약. API 키가 없거나 실패하면 헤드라인 목록으로 대체(메일은 무조건 나감)."""
from __future__ import annotations

import json
import os
import re

SYSTEM = """너는 에너지·AI 인프라 산업 동향 분석가다.
독자: {audience}

규칙:
- 입력된 기사 제목 목록만 근거로 쓴다. 목록에 없는 사실·수치를 지어내지 않는다.
- 비슷한 기사는 하나의 포인트로 묶는다. 사소하거나 광고성 기사는 버린다.
- 각 포인트는 한국어 1~2문장. "무슨 일 → 기술·시장·정책 관점에서 왜 중요한가" 순서.
- 산업 구조, 기술 흐름, 수급, 정책 변화에 초점을 둔다.
- 주가·투자 판단·종목 수혜 여부는 언급하지 않는다. 기업명은 사실 전달에 필요할 때만 쓴다.
- 일본어·영어 기사도 한국어로 쓴다.
- 기사 원문 문장을 그대로 옮기지 말고 네 말로 쓴다.
- 각 포인트에 근거 기사 id를 refs로 단다.
- 반드시 아래 JSON 하나만 출력한다. 다른 텍스트 금지.

{{
  "top3": ["오늘 꼭 알아야 할 것 3개, 각 1문장"],
  "sections": [{{"topic": "토픽명", "points": [{{"text": "...", "refs": ["id"]}}]}}],
  "watch": ["앞으로 지켜볼 기술·정책·시장 변수, 1~3개"]
}}"""


def _parse(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("JSON 없음")
    return json.loads(m.group(0))


def _clean(brief: dict, valid_ids: set[str]) -> dict:
    """존재하지 않는 ref 제거, 빈 섹션 제거."""
    def fix(points):
        res = []
        for p in points or []:
            if isinstance(p, dict) and p.get("text"):
                p["refs"] = [r for r in p.get("refs", []) if r in valid_ids]
                res.append(p)
        return res

    brief["sections"] = [
        {"topic": s.get("topic", ""), "points": fix(s.get("points"))}
        for s in brief.get("sections", []) if fix(s.get("points"))
    ]
    brief["top3"] = [t for t in brief.get("top3", []) if isinstance(t, str)][:3]
    brief["watch"] = [t for t in brief.get("watch", []) if isinstance(t, str)][:3]
    return brief


def fallback(news: list[dict], reason: str) -> dict:
    by_topic: dict[str, list] = {}
    for n in news:
        by_topic.setdefault(n["topic"], []).append({"text": n["title"], "refs": [n["id"]]})
    return {
        "top3": [],
        "sections": [{"topic": t, "points": p[:10]} for t, p in by_topic.items()],
        "watch": [],
        "fallback_reason": reason,
    }


def summarize(news: list[dict], cfg: dict) -> dict:
    if not news:
        return fallback(news, "수집된 기사 없음")
    if not os.getenv("ANTHROPIC_API_KEY"):
        return fallback(news, "ANTHROPIC_API_KEY 없음 — 헤드라인만 표시")

    import anthropic

    lcfg = cfg["llm"]
    items = news[: lcfg.get("max_items_to_llm", 120)]
    payload = {
        "news": [{k: n[k] for k in ("id", "topic", "title", "source", "lang")} for n in items],
        "topics": [t["name"] for t in cfg["topics"]],
    }
    try:
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=lcfg["model"],
            max_tokens=lcfg.get("max_tokens", 4000),
            system=SYSTEM.format(audience=cfg["newsletter"]["audience"]),
            messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        )
        text = "".join(b.text for b in msg.content if b.type == "text")
        return _clean(_parse(text), {n["id"] for n in news})
    except Exception as e:
        print(f"[warn] LLM 요약 실패: {e}")
        return fallback(news, f"LLM 요약 실패({type(e).__name__}) — 헤드라인만 표시")
