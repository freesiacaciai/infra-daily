"""LLM 요약. API 키가 없거나 실패하면 헤드라인 목록으로 대체(메일은 무조건 나감).

모델이 직접 JSON 텍스트를 쓰면 따옴표 하나로 깨질 수 있어서,
도구 호출(tool use) 형식으로 받아 항상 올바른 구조가 오도록 한다.
"""
from __future__ import annotations

import json
import os

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
- 결과는 반드시 publish_briefing 도구로 제출한다."""

TOOL = {
    "name": "publish_briefing",
    "description": "완성된 데일리 브리핑을 제출한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "top3": {"type": "array", "items": {"type": "string"},
                     "description": "오늘 꼭 알아야 할 것 3개, 각 1문장"},
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "points": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"},
                                    "refs": {"type": "array", "items": {"type": "string"}},
                                },
                                "required": ["text", "refs"],
                            },
                        },
                    },
                    "required": ["topic", "points"],
                },
            },
            "watch": {"type": "array", "items": {"type": "string"},
                      "description": "앞으로 지켜볼 기술·정책·시장 변수 1~3개"},
        },
        "required": ["top3", "sections", "watch"],
    },
}


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
        for s in brief.get("sections", []) if isinstance(s, dict) and fix(s.get("points"))
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
    client = anthropic.Anthropic()
    last_err = None
    for attempt in (1, 2):  # 한 번 실패하면 한 번 더 시도
        try:
            msg = client.messages.create(
                model=lcfg["model"],
                max_tokens=lcfg.get("max_tokens", 8000),
                system=SYSTEM.format(audience=cfg["newsletter"]["audience"]),
                tools=[TOOL],
                tool_choice={"type": "tool", "name": "publish_briefing"},
                messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
            )
            block = next((b for b in msg.content if b.type == "tool_use"), None)
            if block is None:
                raise ValueError(f"도구 응답 없음 (stop_reason={msg.stop_reason})")
            if msg.stop_reason == "max_tokens":
                raise ValueError("응답이 max_tokens에서 잘림 — config.yaml의 llm.max_tokens를 늘리세요")
            return _clean(dict(block.input), {n["id"] for n in news})
        except Exception as e:
            last_err = e
            print(f"[warn] LLM 요약 실패 ({attempt}회차): {type(e).__name__}: {e}")
    return fallback(news, f"LLM 요약 실패({type(last_err).__name__}) — 헤드라인만 표시")
