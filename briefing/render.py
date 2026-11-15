"""HTML 메일 렌더링. 메일 클라이언트 호환을 위해 인라인 스타일만 사용."""
from __future__ import annotations

import datetime as dt
import html
import re

from jinja2 import Environment

WEEKDAY = "월화수목금토일"

TEMPLATE = """<!doctype html><html><body style="margin:0;padding:0;background:#f4f4f2;">
<div style="max-width:640px;margin:0 auto;padding:24px 16px;font-family:-apple-system,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;color:#1a1a1a;line-height:1.6;">
  <div style="font-size:12px;color:#888;letter-spacing:.5px;">{{ date }}</div>
  <h1 style="margin:4px 0 20px;font-size:22px;">{{ title }}</h1>

  {% if b.fallback_reason %}
  <div style="background:#fff4e5;border-left:3px solid #f0a020;padding:8px 12px;font-size:13px;margin-bottom:16px;">{{ b.fallback_reason }}</div>
  {% endif %}

  {% if b.top3 %}
  <div style="background:#1a1a1a;color:#fff;padding:16px 18px;border-radius:6px;margin-bottom:24px;">
    <div style="font-size:12px;color:#aaa;margin-bottom:6px;">오늘의 3줄</div>
    <ol style="margin:0;padding-left:20px;">{% for t in b.top3 %}<li style="margin:4px 0;">{{ t }}</li>{% endfor %}</ol>
  </div>
  {% endif %}

  {% for s in b.sections %}
  <h2 style="font-size:16px;border-bottom:2px solid #1a1a1a;padding-bottom:4px;margin:24px 0 10px;">{{ s.topic }}</h2>
  <ul style="margin:0;padding-left:18px;">
  {% for p in s.points %}<li style="margin:8px 0;">{{ p.text }}{{ refs(p.refs) }}</li>{% endfor %}
  </ul>
  {% endfor %}

  {% if b.watch %}
  <div style="background:#eef3f8;padding:14px 18px;border-radius:6px;margin-top:24px;">
    <div style="font-size:12px;color:#557;margin-bottom:6px;">지켜볼 것</div>
    <ul style="margin:0;padding-left:18px;">{% for t in b.watch %}<li style="margin:4px 0;">{{ t }}</li>{% endfor %}</ul>
  </div>
  {% endif %}

  <div style="font-size:11px;color:#999;margin-top:32px;border-top:1px solid #ddd;padding-top:10px;">
    뉴스 {{ n_news }}건 기반 자동 생성 요약 · 세부 내용은 원문 링크에서 확인하세요.
    {% if site_url %}<br><a href="{{ site_url }}#/{{ day }}" style="color:#3366aa;">웹에서 보기</a> · <a href="{{ site_url }}" style="color:#3366aa;">지난 브리핑 검색</a>{% endif %}
  </div>
</div></body></html>"""


def render_html(brief: dict, news: list[dict], now: dt.datetime, cfg: dict) -> str:
    idx = {n["id"]: (n["source"] or "원문", n["link"]) for n in news}

    def refs(ids):
        links = [
            f'<a href="{html.escape(idx[i][1])}" style="color:#3366aa;text-decoration:none;">{html.escape(idx[i][0])}</a>'
            for i in ids if i in idx
        ]
        return (' <span style="font-size:12px;color:#888;">— ' + " · ".join(links) + "</span>") if links else ""

    env = Environment(autoescape=True)
    env.globals["refs"] = lambda ids: __import__("markupsafe").Markup(refs(ids))
    return env.from_string(TEMPLATE).render(
        b=brief,
        title=cfg["newsletter"]["title"],
        date=f"{now:%Y.%m.%d} ({WEEKDAY[now.weekday()]})",
        n_news=len(news),
        site_url=(cfg["newsletter"].get("site_url") or "").rstrip("/") + "/" if cfg["newsletter"].get("site_url") else "",
        day=f"{now:%Y-%m-%d}",
    )


def html_to_text(h: str) -> str:
    t = re.sub(r"<(br|/li|/h\d|/div)>", "\n", h)
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"\n\s*\n+", "\n\n", html.unescape(t)).strip()
