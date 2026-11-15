# AI 인프라 데일리 브리핑

매일 새벽 에너지·AI 인프라 분야 뉴스(한·영·일)를 모아서 Claude로 요약합니다.
결과는 **이메일**로 받고, **공개 웹사이트**에 날짜별로 쌓입니다.
산업·기술·정책 동향 브리핑이며, 종목이나 투자 판단은 다루지 않습니다.
서버가 필요 없습니다. GitHub Actions가 매일 KST 05:37쯤 실행합니다.

```
Google News RSS ─▶ Claude 요약 ─┬─▶ archive/날짜.json (저장소에 커밋, 영구 기록)
                                ├─▶ site/ ─▶ GitHub Pages (날짜별 보기 · 토픽 필터 · 전체 검색)
                                └─▶ HTML 메일 ─▶ Gmail SMTP
```

## 1\. 준비물

|항목|발급처|비고|
|-|-|-|
|`ANTHROPIC\_API\_KEY`|console.anthropic.com|하루 입력 약 1만 토큰, 출력 약 2천 토큰 수준. 없으면 헤드라인만 기록|
|`SMTP\_USER`|발송용 Gmail 주소|개인 메인 계정과 분리 추천|
|`SMTP\_PASSWORD`|Google 계정 → 보안 → 2단계 인증 켜기 → **앱 비밀번호**|일반 비밀번호로는 로그인 안 됨|
|`MAIL\_TO`|받을 주소, 쉼표로 여러 명|BCC로 발송|

## 2\. 설치

1. GitHub에 **public** 저장소를 만들고 이 폴더 내용을 그대로 올립니다.

   * 저장소가 공개되어도 Secrets에 넣은 키와 메일 주소는 노출되지 않습니다.
2. Settings → Secrets and variables → Actions → New repository secret에서 위 4개를 등록합니다.
3. Settings → Pages → Build and deployment → Source를 **GitHub Actions**로 바꿉니다.
4. Actions 탭 → `daily-briefing` → **Run workflow**로 1회 수동 실행합니다.
5. 실행이 끝나면 사이트 주소(`https://<아이디>.github.io/<저장소이름>/`)가 표시됩니다.
이 주소를 `config.yaml`의 `site\_url`에 넣고 커밋하면 메일에 "웹에서 보기" 링크가 붙습니다.

## 3\. 사이트 기능

* 첫 화면은 가장 최근 브리핑입니다. 왼쪽 날짜 목록이나 이전/다음 버튼으로 이동합니다. 모바일에서는 날짜 선택 상자로 바뀝니다.
* 토픽 칩으로 "광통신만" 같은 식으로 골라 볼 수 있습니다.
* 상단 검색창은 **전체 기간**에서 찾습니다. 여러 단어를 띄어 쓰면 모두 포함한 항목만 나옵니다.
* 날짜별 주소(`#/2026-11-15`)를 그대로 공유할 수 있습니다.
* 다크 모드는 시스템 설정을 따릅니다.

## 4\. 로컬 테스트

```bash
pip install -r requirements.txt
python -m briefing.main --dry-run --fixture fixtures/sample.json   # 가짜 데이터, 키 없어도 됨
python -m http.server -d site 8000                                 # http://localhost:8000 에서 사이트 확인
python -m briefing.site                                            # archive만으로 사이트 다시 생성
```

로컬에서 테스트하면 `archive/`에 가짜 기록이 생깁니다. 저장소에 올리기 전에 지우세요.

## 5\. 커스터마이즈 (`config.yaml`만 고치면 됨)

* `topics`: 토픽과 검색어. Google 검색 문법(OR, "구문", -제외어)을 그대로 씁니다.
* `newsletter.title`, `tagline`: 사이트와 메일 제목.
* `newsletter.audience`: 요약의 관점과 깊이가 이 문장에 따라 달라집니다.
* `llm.model`: 모델 이름이 바뀌어서 오류가 나면 여기만 수정하면 됩니다.
* 발송 시간: `.github/workflows/daily.yml`의 cron 값 (UTC 기준).

## 6\. 공개 사이트 운영 원칙

* 사이트에는 **AI가 작성한 요약과 출처 링크만** 올라갑니다. 기사 본문은 수집하지도, 게시하지도 않습니다.
기사 제목은 `archive/`에 기록용으로만 남고 사이트 화면에는 나오지 않습니다.
* 요약 지시문(`briefing/summarize.py`의 SYSTEM)에 주가·투자 판단·종목 수혜를 언급하지 말라는 규칙이 들어 있습니다. 지우지 마세요.
* AI 요약은 틀릴 수 있습니다. 사이트 하단 안내 문구도 유지하세요.
* 공개 저장소이므로 커밋 기록에 남는 이름이나 이메일 주소를 확인하세요. 실명을 드러내고 싶지 않다면 GitHub 계정 설정에서 noreply 이메일을 쓰면 됩니다.

