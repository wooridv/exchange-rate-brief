# 환율 아침 브리핑 (Exchange Brief)

원화(KRW) 대비 **USD · EUR · JPY(100) · CNY** 의 **현찰 살 때 / 팔 때** 환율을
**평일 오전 9시** 잔디(Jandi)로 정기 브리핑하고, **장중 급변 시 실시간 알림(09~18시)** 도 보내며,
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
| `data/history.jsonl` | 시간별(전시간 대비) 시계열 — 실행 간 `actions/cache`로 유지(전일 데이터는 네이버에서 매번 전체 수집) |
| `.github/workflows/exchange-brief.yml` | 장중 10분마다 갱신(정기 브리핑 오전 9시 + 급변 알림 09~18시) + Pages 배포 |

## 갱신 주기 / 실시간 / 급변 알림

- **장중(평일 09~18시 KST) 10분마다** GitHub Actions가 사이트·시간별 데이터를 갱신하고, 대시보드는 60초마다 자동 새로고침해 "준실시간"으로 보여줍니다(상단 "실시간" 표시).
- **정기 잔디 브리핑은 평일 오전 9시에 1회만**.
- **급변 알림**: 09~18시 사이, 직전 갱신(같은 날) 대비 매매기준율이 **±0.4% 이상** 움직이면 🚨 별도 잔디 알림. 통화별 **쿨다운 60분**, 장 시작 오버나이트 갭은 제외.
  - 임계값·쿨다운·시간대는 환경변수로 조정: `ALERT_PCT`(기본 0.4), `ALERT_COOLDOWN_MIN`(60), `ALERT_START_HOUR`(9), `ALERT_END_HOUR`(18).
- 정적 사이트라 브라우저가 네이버를 직접 부를 수 없어(CORS) 초 단위 실시간은 아니며, 갱신 주기(10분)만큼의 지연이 있습니다.

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
4. **Actions → 환율 브리핑 → Run workflow** 로 수동 확인 → 이후 장중 10분마다 자동 갱신(정기 브리핑 오전 9시 + 급변 알림 09~18시)

## 개인정보 · 보안

- 공개 배포물(Pages 사이트 · `data/history.jsonl` · 커밋)에는 **공개 환율 데이터만** 포함합니다.
- 웹훅 URL·이메일 등 개인정보는 **커밋 금지**, GitHub Secret / 로컬 `.env` 로만 주입합니다.
