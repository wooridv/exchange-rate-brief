# 환율 아침 브리핑 (Exchange Brief)

원화(KRW) 대비 **USD · EUR · JPY(100) · CNY** 의 **현찰 살 때 / 팔 때** 환율을
매일 **평일 3회(09:00 · 12:00 · 15:00 KST)** 잔디(Jandi)로 브리핑하고,
전일/전시간 대비 그래프 + 모션그래픽 + **규칙기반 AI 매수 분석**을 담은 대시보드를 GitHub Pages 로 배포합니다.

- 데이터 출처: **네이버 금융 · 하나은행 고시** (`api.stock.naver.com/marketindex/exchange/<code>/prices`)
- **공휴일·대체공휴일·주말에는 잔디로 알리지 않습니다** (대시보드는 계속 갱신). `holidays.py`
- 잔디 메시지는 **7줄 이내**로 요약, 하단에 상세 대시보드 링크 포함
- 의존 라이브러리 없음(파이썬 표준 라이브러리만) — GitHub Actions 에서 그대로 실행

## 구성

| 파일 | 역할 |
|---|---|
| `brief.py` | 수집 → 신호계산 → 사이트 생성 → 잔디 발송 (메인) |
| `app_html.py` | 대시보드 SPA(`SPA_HTML`) — 카드/차트/AI게이지 |
| `holidays.py` | 한국 공휴일·대체공휴일 집합 (**매년 갱신 필요**) |
| `data/history.jsonl` | 슬롯(시간별) 시계열 누적 — 그래프 원천, 저장소 커밋 대상 |
| `.github/workflows/exchange-brief.yml` | 크론 3회 + 히스토리 커밋 + Pages 배포 |

## AI 매수 분석(규칙기반)

통화별 매매기준율 최근 이력으로 계산합니다. **투자자문이 아닌 참고 지표**입니다.

- **밴드 위치**: 최근 20일 최저~최고 중 현재 위치(낮을수록 저렴)
- **추세**: 20일 평균 대비 위/아래(저평가/고평가)
- **모멘텀**: 당일 등락(급등 시 관망, 하락 시 진입 기회)
- **변동성**: 일간 표준편차
- → **매수 적합도 0~100** + 판정(구매 적기 / 중립 / 관망) + **근거·지표 데이터**를 대시보드에 표시

> 자연어 AI 코멘트가 필요하면 GitHub Actions 에 유료 API 키를 넣지 말고,
> **구독 요금제(Claude Code 스케줄 루틴)** 로만 생성하세요.

## 로컬 테스트 (파이썬 3.9+, 외부 라이브러리 불필요)

```bash
cp .env.example .env    # JANDI_WEBHOOK_URL 채우기

python brief.py --test              # 잔디 웹훅 연결만 테스트
python brief.py --out site --dry-run # 수집·사이트 생성(발송·기록 안 함)
# → site/index.html 을 브라우저로 열어 확인
python brief.py --out site --slot morning --no-post  # 사이트+히스토리, 잔디만 미발송
```

주요 옵션: `--slot morning|lunch|afternoon` · `--force`(공휴일/중복 무시) · `--no-post` · `--dry-run`

## 배포(요약)

1. 이 폴더를 새 GitHub 저장소로 push
2. **Settings → Secrets and variables → Actions** 에 `JANDI_WEBHOOK_URL` 등록
3. **Settings → Pages → Source: GitHub Actions** 활성화
4. **Actions → 환율 브리핑 → Run workflow** 로 수동 확인 → 이후 평일 3회 자동 실행

## 개인정보 · 보안

- 공개 배포물(Pages 사이트 · `data/history.jsonl` · 커밋)에는 **공개 환율 데이터만** 포함합니다.
- 웹훅 URL·이메일 등 개인정보는 **커밋 금지**, GitHub Secret / 로컬 `.env` 로만 주입합니다.
