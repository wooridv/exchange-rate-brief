#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""환율 아침 브리핑 — 원화 대비 USD·EUR·JPY·CNY 현찰 살때/팔때 + 잔디 발송 + 대시보드.

동작:
  1) 네이버 금융(하나은행 고시) 일별 시세를 통화별로 수집.
     엔드포인트: api.stock.naver.com/marketindex/exchange/<code>/prices
       → closePrice(매매기준율) / cashBuyValue(현찰 살때) / cashSellValue(현찰 팔때)
         + fluctuations(전일대비) + 최근 N일 히스토리(그래프·신호용)
  2) 규칙기반 신호엔진으로 통화별 '매수 적합도(0~100)' + 근거를 계산.
  3) site/data/app.json + site/index.html(정적 SPA) 생성 — 전일/전시간 대비 그래프,
     모션그래픽, AI 분석(근거·지표 데이터 포함) 대시보드.
  4) 최신 스냅샷 요약(7줄 이내)을 잔디로 발송. (data/history.jsonl 로 슬롯 중복 방지)

주말·법정공휴일·대체공휴일에는 발송/기록하지 않는다(holidays.py). --force 로 우회.

환경변수:
  JANDI_WEBHOOK_URL   잔디 Incoming Webhook URL (발송 시 필수, 커밋 금지)
  REPORT_BASE_URL     대시보드 공개 URL (옵션, 잔디 링크에 사용)
  HISTORY_DAYS        차트/신호에 쓸 일별 히스토리 일수 (기본 60)

CLI: --dry-run / --slot morning|lunch|afternoon / --force / --test / --no-post / --out DIR
"""

import argparse
import datetime as dt
import json
import os
import statistics
import sys
import time
import urllib.request

from holidays import is_holiday, skip_reason

try:
    from zoneinfo import ZoneInfo
    KST = ZoneInfo("Asia/Seoul")
except Exception:  # pragma: no cover
    KST = dt.timezone(dt.timedelta(hours=9))

# 통화: (키, 네이버코드, 국기, 표시라벨, 단위설명)
CURRENCIES = [
    ("USD", "FX_USDKRW", "\U0001F1FA\U0001F1F8", "USD", "달러 (1$)"),
    ("EUR", "FX_EURKRW", "\U0001F1EA\U0001F1FA", "EUR", "유로 (1€)"),
    ("JPY", "FX_JPYKRW", "\U0001F1EF\U0001F1F5", "JPY100", "엔화 (100¥)"),
    ("CNY", "FX_CNYKRW", "\U0001F1E8\U0001F1F3", "CNY", "위안 (1¥)"),
]
KO_NAME = {"USD": "달러", "EUR": "유로", "JPY": "엔화", "CNY": "위안"}
FLAG = {k: f for k, _c, f, _l, _u in CURRENCIES}
PRICES_URL = "https://api.stock.naver.com/marketindex/exchange/%s/prices?page=1&pageSize=%d"
WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]
HISTORY_FILE = os.path.join("data", "history.jsonl")
SOURCE_NAME = "네이버 금융 · 하나은행 고시"

# KST 시(hour) → (슬롯키, 표시라벨). 잔디 발송은 오전 9시 1회만.
# (사이트/시간별 데이터는 워크플로가 장중 20분마다 계속 갱신)
SLOT_MAP = {9: ("morning", "09:00")}
SLOT_KO = {"morning": "아침", "lunch": "점심", "afternoon": "오후", "adhoc": "수시"}


# --------------------------------------------------------------------------
# 공통 유틸
# --------------------------------------------------------------------------
def load_dotenv(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _num(v):
    try:
        if v in (None, ""):
            return None
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _http(url, timeout=30, retries=6):
    # 해외 러너(GitHub Actions)에서 간헐적 연결 끊김(SSL UNEXPECTED_EOF) 대응:
    # 재시도 넉넉히 + 점증 대기. 네이버 API 는 cp949 로 응답하기도 하므로 인코딩 폴백.
    hdr = {"User-Agent": "Mozilla/5.0 (exchange-brief/1.0)",
           "Accept": "application/json"}
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=hdr, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b = r.read()
            try:
                return b.decode("utf-8")
            except UnicodeDecodeError:
                return b.decode("cp949", "replace")
        except Exception as e:  # noqa: BLE001
            last = e
            if i < retries - 1:
                time.sleep(1.0 + 1.5 * i)  # 1.0,2.5,4.0,5.5,7.0s
    raise RuntimeError("HTTP 실패(%s): %s" % (url, last))


def pct(new, old):
    if not old:
        return None
    return round((new - old) / old * 100.0, 2)


# --------------------------------------------------------------------------
# 데이터 수집
# --------------------------------------------------------------------------
def fetch_prices(code, size):
    """네이버 일별 시세 → 최신순 리스트.
    각 원소: {date, base, buy, sell, dayChg, dayChgPct}"""
    raw = _http(PRICES_URL % (code, size))
    rows = json.loads(raw)
    out = []
    for it in rows:
        base = _num(it.get("closePrice"))
        if base is None:
            continue
        out.append({
            "date": str(it.get("localTradedAt", "")).strip(),
            "base": base,
            "buy": _num(it.get("cashBuyValue")),   # 현찰 살 때(내가 살 때)
            "sell": _num(it.get("cashSellValue")),  # 현찰 팔 때(내가 팔 때)
            "dayChg": _num(it.get("fluctuations")),
            "dayChgPct": _num(it.get("fluctuationsRatio")),
        })
    return out  # 최신 → 과거


# --------------------------------------------------------------------------
# 규칙기반 신호엔진 (AI 분석) — 무료·키 불필요
# --------------------------------------------------------------------------
def compute_signal(rows):
    """rows(최신순)로 매수 적합도(0~100) + 근거/지표 계산.
    점수가 높을수록 '원화 보유자가 외화를 사기에 상대적으로 저렴'."""
    bases = [r["base"] for r in rows if r["base"] is not None][::-1]  # 과거→현재
    n = len(bases)
    if n < 2:
        return None
    cur = bases[-1]
    win = min(20, n)
    window = bases[-win:]
    lo, hi = min(window), max(window)
    pctile = 0.0 if hi == lo else (cur - lo) / (hi - lo) * 100.0
    sma5 = statistics.fmean(bases[-min(5, n):])
    sma20 = statistics.fmean(window)
    rets = [(window[i] - window[i - 1]) / window[i - 1] * 100.0
            for i in range(1, len(window)) if window[i - 1]]
    vol = statistics.pstdev(rets) if len(rets) > 1 else 0.0
    mom = (cur - bases[-2]) / bases[-2] * 100.0 if bases[-2] else 0.0

    score = 100.0 - pctile           # 밴드 하단일수록 저렴 → 높은 점수
    score += 5 if cur < sma20 else -5  # 20일 평균 아래=저평가
    if mom > 0.5:
        score -= 8                   # 오늘 급등 → 관망
    elif mom < -0.5:
        score += 8                   # 오늘 하락 → 진입 기회
    score = int(max(0, min(100, round(score))))

    if score >= 66:
        verdict, short = "구매 적기", "적기"
    elif score <= 33:
        verdict, short = "관망(비쌈)", "관망"
    else:
        verdict, short = "중립", "중립"

    vol_txt = "낮음" if vol < 0.4 else ("높음" if vol > 0.8 else "보통")
    reasons = [
        "최근 %d일 밴드에서 하위 %.0f%% 가격대 (낮을수록 저렴)" % (win, pctile),
        "20일 평균 %s원 대비 %s" % (
            _fmt(sma20), "아래 → 저평가 구간" if cur < sma20 else "위 → 고평가 구간"),
        "오늘 %s %.2f%% → %s" % (
            "상승" if mom > 0 else ("하락" if mom < 0 else "보합"), abs(mom),
            "단기 상승, 관망 유리" if mom > 0.5 else (
                "단기 하락, 진입 기회" if mom < -0.5 else "보합권, 방향성 약함")),
        "변동성 %.2f%%/일 (%s)" % (vol, vol_txt),
    ]
    return {
        "score": score, "verdict": verdict, "short": short,
        "reasons": reasons,
        "metrics": {
            "cur": round(cur, 2), "sma5": round(sma5, 2), "sma20": round(sma20, 2),
            "hi": round(hi, 2), "lo": round(lo, 2),
            "pctile": round(pctile, 1), "vol": round(vol, 2),
            "mom": round(mom, 2), "window": win,
        },
    }


# --------------------------------------------------------------------------
# 포맷
# --------------------------------------------------------------------------
def _fmt(v, dec=1):
    if v is None:
        return "-"
    return "{:,.{d}f}".format(float(v), d=dec)


def arrow(p):
    if p is None:
        return "–"
    return "▲" if p > 0 else ("▼" if p < 0 else "–")


def sgn(p):
    if p is None:
        return "-"
    a = "▲" if p > 0 else ("▼" if p < 0 else "–")
    return "%s%.2f%%" % (a, abs(p))


def date_label(ds):
    d = dt.datetime.strptime(ds, "%Y-%m-%d").date()
    return "%d/%d(%s)" % (d.month, d.day, WEEKDAY_KO[d.weekday()])


# --------------------------------------------------------------------------
# 잔디
# --------------------------------------------------------------------------
def _ko_name(code):
    name = KO_NAME.get(code, code)
    return name + "(100엔)" if code == "JPY" else name


def jandi_body(bundle, report_url=None):
    """7줄 이내: 헤더 + 4통화(한글명·살때/팔때·전일대비) + AI 한 줄 + 링크."""
    lines = []
    lines.append("💱 환율 브리핑  %s %s" % (date_label(bundle["date"]), bundle["slotLabel"]))
    for c in bundle["currencies"]:
        lines.append("%s %s  살때: %s · 팔때: %s · %s" % (
            c["flag"], _ko_name(c["code"]), _fmt(c["buy"]), _fmt(c["sell"]),
            sgn(c["day"]["baseChgPct"])))
    ai = " · ".join("%s %s" % (KO_NAME.get(c["code"], c["code"]), c["signal"]["short"])
                    for c in bundle["currencies"] if c.get("signal"))
    if ai:
        lines.append("🤖 AI 매수신호: " + ai)
    if report_url:
        lines.append("🔗 그래프·상세분석: %s" % report_url)
    return "\n".join(lines[:7])


def jandi_color(bundle):
    verdicts = [c["signal"]["verdict"] for c in bundle["currencies"] if c.get("signal")]
    if any("적기" in v for v in verdicts):
        return "#16a34a"   # 초록: 매수 적기 있음
    if any("관망" in v for v in verdicts):
        return "#d97706"   # 주황: 관망 우세
    return "#2563eb"       # 파랑: 중립


def console_summary(bundle):
    out = ["=" * 60,
           "환율 브리핑  %s %s  (%s)" % (date_label(bundle["date"]),
                                     bundle["slotLabel"], SOURCE_NAME),
           "=" * 60]
    for c in bundle["currencies"]:
        s = c.get("signal") or {}
        out.append("%s %-6s 살 %s / 팔 %s  기준 %s (전일 %s)  AI %s(%s)" % (
            c["flag"], c["label"], _fmt(c["buy"]), _fmt(c["sell"]),
            _fmt(c["base"], 2), sgn(c["day"]["baseChgPct"]),
            s.get("score", "-"), s.get("short", "-")))
    return "\n".join(out)


def post_jandi(url, body, color="#2563eb"):
    data = json.dumps({"body": body, "connectColor": color}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Content-Type": "application/json",
        "Accept": "application/vnd.tosslab.jandi-v2+json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.read().decode("utf-8", "replace")


# --------------------------------------------------------------------------
# 히스토리(슬롯 시계열) — data/history.jsonl (저장소 커밋 대상)
# --------------------------------------------------------------------------
def read_history():
    rows = []
    if not os.path.exists(HISTORY_FILE):
        return rows
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


def append_history(entry):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def point_exists(history, date, point_label):
    """같은 날짜·시각(HH:MM) 포인트가 이미 있으면 True(같은 분 재실행 중복 방지)."""
    return any(h.get("date") == date and h.get("slotLabel") == point_label for h in history)


def posted_slot_today(history, date, slot_key):
    """오늘 해당 발송 슬롯(morning/lunch/afternoon)으로 이미 잔디를 보냈으면 True."""
    if not slot_key:
        return False
    return any(h.get("date") == date and h.get("postSlot") == slot_key for h in history)


def prev_slot_rates(history, code):
    """history(시간순)에서 가장 최근 슬롯의 해당 통화 값 → 전시간(전 슬롯) 대비용."""
    for h in reversed(history):
        r = (h.get("rates") or {}).get(code)
        if r and r.get("base") is not None:
            return r
    return None


def prev_slot_full(history, code):
    """가장 최근 슬롯의 (값, 날짜, 라벨) → 인트라데이 급변 감지용."""
    for h in reversed(history):
        r = (h.get("rates") or {}).get(code)
        if r and r.get("base") is not None:
            return r, h.get("date"), h.get("slotLabel")
    return None, None, None


def last_alert_dt(history, code):
    """해당 통화의 마지막 알림 시각(datetime) → 쿨다운 판정."""
    for h in reversed(history):
        if code in (h.get("alerts") or []):
            try:
                return dt.datetime.fromisoformat(h.get("ts"))
            except (TypeError, ValueError):
                return None
    return None


def detect_alerts(history, snapshot, today, threshold, now, cooldown_min):
    """직전 슬롯(같은 날) 대비 |변동%| >= threshold 인 통화 목록. 쿨다운 적용."""
    out = []
    for code, cur in snapshot.items():
        prev, pdate, plabel = prev_slot_full(history, code)
        if not prev or pdate != today or not prev.get("base") or not cur.get("base"):
            continue  # 인트라데이(같은 날) 비교만 → 오버나이트 갭 제외
        p = pct(cur["base"], prev["base"])
        if p is None or abs(p) < threshold:
            continue
        last = last_alert_dt(history, code)
        if last is not None and (now - last).total_seconds() < cooldown_min * 60:
            continue  # 쿨다운: 최근 알림 후 일정 시간 내 재알림 금지
        out.append({"code": code, "pct": p, "buy": cur["buy"], "sell": cur["sell"],
                    "base": cur["base"], "from": plabel})
    return out


def day_open_base(history, today, code):
    """오늘 첫 기록(≈오전 9시) 매매기준율 → 일중 누적 스윙 기준."""
    for h in history:  # 이른 것부터
        if h.get("date") == today:
            r = (h.get("rates") or {}).get(code)
            if r and r.get("base") is not None:
                return r["base"]
    return None


def swing_alerted_today(history, today, code, direction):
    tag = code + direction
    return any(h.get("date") == today and tag in (h.get("swingAlerts") or []) for h in history)


def detect_swings(history, snapshot, today, swing_pct):
    """오늘 시가 대비 |변동%| >= swing_pct 이고, 방향별 오늘 미알림인 통화."""
    out = []
    for code, cur in snapshot.items():
        op = day_open_base(history, today, code)
        if not op or not cur.get("base"):
            continue
        p = pct(cur["base"], op)
        if p is None or abs(p) < swing_pct:
            continue
        d = "+" if p > 0 else "-"
        if swing_alerted_today(history, today, code, d):
            continue
        out.append({"code": code, "pct": p, "buy": cur["buy"], "sell": cur["sell"],
                    "kind": "swing", "dir": d})
    return out


def _alert_line(a):
    if a.get("kind") == "swing":
        tag = "오늘 %s" % sgn(a["pct"])            # 오늘 ▼0.61% (9시 대비 누적)
    else:
        tag = "%s %s" % ("급등" if a["pct"] > 0 else "급락", sgn(a["pct"]))  # 직전 10분 대비
    return "%s %s %s · 살때 %s 팔때 %s" % (
        FLAG.get(a["code"], ""), KO_NAME.get(a["code"], a["code"]), tag,
        _fmt(a["buy"]), _fmt(a["sell"]))


def alert_body(items, now, report_url=None):
    lines = ["🚨 환율 급변 알림  %s" % now.strftime("%H:%M")]
    for a in items[:4]:
        lines.append(_alert_line(a))
    if report_url:
        lines.append("🔗 상세: %s" % report_url)
    return "\n".join(lines[:7])


def intraday_series(history, code, limit=60):
    """대시보드 시간별(슬롯) 시계열."""
    out = []
    for h in history[-limit:]:
        r = (h.get("rates") or {}).get(code)
        if not r:
            continue
        out.append({"ts": h.get("ts"), "date": h.get("date"),
                    "slotLabel": h.get("slotLabel"),
                    "base": r.get("base"), "buy": r.get("buy"), "sell": r.get("sell")})
    return out


# --------------------------------------------------------------------------
# 번들 구성 + 사이트
# --------------------------------------------------------------------------
def build_bundle(now, slot_key, disp_label, point_label, prices, history):
    currencies = []
    rates_snapshot = {}
    for key, code, flag, label, unit in CURRENCIES:
        rows = prices.get(key) or []
        if not rows:
            continue
        cur = rows[0]
        prev = rows[1] if len(rows) > 1 else None
        prev_slot = prev_slot_rates(history, key)

        day = {
            "baseChg": cur["dayChg"], "baseChgPct": cur["dayChgPct"],
            "buyChg": (round(cur["buy"] - prev["buy"], 2) if prev and cur["buy"] and prev["buy"] else None),
            "buyChgPct": (pct(cur["buy"], prev["buy"]) if prev else None),
            "sellChg": (round(cur["sell"] - prev["sell"], 2) if prev and cur["sell"] and prev["sell"] else None),
            "sellChgPct": (pct(cur["sell"], prev["sell"]) if prev else None),
        }
        slot_delta = None
        if prev_slot and prev_slot.get("base"):
            slot_delta = {
                "baseChg": round(cur["base"] - prev_slot["base"], 2),
                "baseChgPct": pct(cur["base"], prev_slot["base"]),
                "from": prev_slot.get("slotLabel"),
            }
        daily = [{"date": r["date"], "base": r["base"], "buy": r["buy"], "sell": r["sell"]}
                 for r in rows[::-1]]  # 과거→현재(차트용)

        currencies.append({
            "code": key, "flag": flag, "label": label, "unit": unit,
            "base": cur["base"], "buy": cur["buy"], "sell": cur["sell"],
            "prevBase": (prev["base"] if prev else None),
            "prevBuy": (prev["buy"] if prev else None),
            "prevSell": (prev["sell"] if prev else None),
            "day": day, "slot": slot_delta,
            "signal": compute_signal(rows),
            "daily": daily,
            "intraday": intraday_series(history, key) + [{
                "ts": now.isoformat(timespec="minutes"), "date": now.strftime("%Y-%m-%d"),
                "slotLabel": point_label, "base": cur["base"], "buy": cur["buy"], "sell": cur["sell"]}],
        })
        rates_snapshot[key] = {"base": cur["base"], "buy": cur["buy"], "sell": cur["sell"],
                               "dayChgPct": cur["dayChgPct"], "slotLabel": point_label}

    return {
        "generated": now.strftime("%Y-%m-%d %H:%M"),
        "date": now.strftime("%Y-%m-%d"),
        "slot": slot_key or "adhoc", "slotLabel": disp_label,
        "slotKo": SLOT_KO.get(slot_key, "수시"),
        "source": SOURCE_NAME,
        "currencies": currencies,
    }, rates_snapshot


def write_site(bundle, out_dir):
    data_dir = os.path.join(out_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    with open(os.path.join(data_dir, "app.json"), "w", encoding="utf-8") as f:
        json.dump(bundle, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(SPA_HTML)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
SLOT_CANON = {"morning": "09:00", "lunch": "12:00", "afternoon": "15:00"}


def resolve_slot(now, override):
    """반환: (post_slot_key or None, 표시라벨).
    post_slot_key 가 있으면 그 시각대(9/12/15시)에 잔디 발송 대상."""
    if override:
        return override, SLOT_CANON.get(override, now.strftime("%H:%M"))
    hit = SLOT_MAP.get(now.hour)   # 9/12/15시 → (key, 캐논라벨)
    if hit:
        return hit[0], hit[1]
    return None, now.strftime("%H:%M")


def main(argv=None):
    # Windows 콘솔(cp949)에서도 이모지/한글 출력이 깨지지 않도록
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    load_dotenv()
    ap = argparse.ArgumentParser(description="환율 아침 브리핑")
    ap.add_argument("--slot", choices=["morning", "lunch", "afternoon"])
    ap.add_argument("--dry-run", action="store_true", help="사이트만 생성, 잔디 미발송·히스토리 미기록")
    ap.add_argument("--no-post", action="store_true", help="사이트+히스토리 갱신, 잔디만 미발송")
    ap.add_argument("--force", action="store_true", help="공휴일/중복 슬롯 무시하고 실행")
    ap.add_argument("--test", action="store_true", help="잔디 웹훅 연결 테스트만")
    ap.add_argument("--out", default="site")
    ap.add_argument("--days", type=int, default=int(os.environ.get("HISTORY_DAYS", "60")))
    args = ap.parse_args(argv)

    webhook = os.environ.get("JANDI_WEBHOOK_URL", "").strip()
    if args.test:
        if not webhook:
            print("JANDI_WEBHOOK_URL 미설정", file=sys.stderr)
            return 2
        s, r = post_jandi(webhook, "✅ 환율 브리핑 웹훅 연결 테스트\n정상 수신되면 설정 완료입니다.")
        print("잔디 응답:", s, r)
        return 0

    now = dt.datetime.now(KST)
    today = now.date()

    # 주말·공휴일: 잔디 발송/히스토리 기록만 제외(대시보드는 계속 갱신)
    reason = skip_reason(today)
    blocked = bool(reason) and not args.force
    if blocked:
        print("오늘(%s)은 %s → 잔디 발송·기록 제외(사이트만 갱신)" % (today, reason))

    post_slot, disp_label = resolve_slot(now, args.slot)
    point_label = now.strftime("%H:%M")  # 시간별 그래프용 실제 시각(분 단위)
    print("실행: %s  표시=%s  발송슬롯=%s" % (
        now.strftime("%Y-%m-%d %H:%M"), disp_label, post_slot or "-"))

    # 통화별 수집(개별 실패 격리)
    prices = {}
    for key, code, _f, _l, _u in CURRENCIES:
        try:
            prices[key] = fetch_prices(code, max(20, args.days))
            print("  %s: %d일 수집 (최신 %s)" % (key, len(prices[key]),
                                            prices[key][0]["date"] if prices[key] else "-"))
        except Exception as e:  # noqa: BLE001
            print("  ! %s 수집 실패(skip): %s" % (key, e))
    if not any(prices.values()):
        print("전 통화 수집 실패 → 종료")
        return 1

    history = read_history()
    bundle, snapshot = build_bundle(now, post_slot, disp_label, point_label, prices, history)

    write_site(bundle, args.out)
    print("\n" + console_summary(bundle))
    body = jandi_body(bundle, os.environ.get("REPORT_BASE_URL", "").strip() or None)
    print("\n[잔디 %d줄]\n%s" % (len(body.splitlines()), body))
    print("\n[사이트] %s" % os.path.join(args.out, "index.html"))

    if args.dry_run:
        print("\n(dry-run: 발송·기록 안 함)")
        return 0
    if blocked:
        return 0  # 휴일/주말: 사이트만 갱신하고 종료

    # 잔디 발송 여부: 9/12/15시 슬롯이고, 오늘 그 슬롯을 아직 안 보냈을 때만
    already_posted = posted_slot_today(history, bundle["date"], post_slot)
    do_post = (bool(post_slot) and not already_posted and not args.no_post
               and bool(webhook)) or (args.force and bool(webhook) and not args.no_post)

    posted_ok = False
    if do_post:
        s, r = post_jandi(webhook, body, jandi_color(bundle))
        posted_ok = 200 <= s < 300
        print("\n잔디 발송(%s):" % (post_slot or "force"), s, r)
    else:
        why = ("발송슬롯 아님(시간별 갱신만)" if not post_slot else
               "이미 발송한 슬롯" if already_posted else
               "--no-post" if args.no_post else "웹훅 미설정")
        print("\n잔디 미발송: %s" % why)

    # 급변 알림(오전 9시~오후 6시). ① 순간 급변(직전 10분 ±ALERT_PCT) ② 일중 누적 스윙(오늘 9시 대비 ±SWING_PCT)
    alerted, swing_tags = [], []
    threshold = float(os.environ.get("ALERT_PCT", "0.4"))
    swing_pct = float(os.environ.get("ALERT_SWING_PCT", "0.5"))
    cooldown = int(os.environ.get("ALERT_COOLDOWN_MIN", "60"))
    a_start = int(os.environ.get("ALERT_START_HOUR", "9"))
    a_end = int(os.environ.get("ALERT_END_HOUR", "18"))
    report_url = os.environ.get("REPORT_BASE_URL", "").strip() or None
    in_window = a_start <= now.hour < a_end
    if in_window and not args.no_post and webhook:
        spikes = detect_alerts(history, snapshot, bundle["date"], threshold, now, cooldown)
        swings = detect_swings(history, snapshot, bundle["date"], swing_pct)
        # 통화별 병합(누적 스윙 우선 표시). 발송은 한 건으로.
        by_code = {}
        for a in spikes:
            by_code[a["code"]] = a
        for a in swings:
            by_code[a["code"]] = a
        items = list(by_code.values())
        if items:
            sa, ra = post_jandi(webhook, alert_body(items, now, report_url), "#dc2626")
            if 200 <= sa < 300:
                alerted = [a["code"] for a in spikes]                 # 순간급변 → 쿨다운 마킹
                swing_tags = [a["code"] + a["dir"] for a in swings]   # 누적스윙 → 방향별 하루1회 마킹
                print("\n🚨 급변 알림 발송: %s" %
                      " · ".join("%s %s(%s)" % (KO_NAME.get(a["code"], a["code"]), sgn(a["pct"]),
                                                a.get("kind", "spike")) for a in items))
            else:
                print("\n급변 알림 발송 실패:", sa, ra)

    # 시간별 히스토리 기록(같은 분 중복만 방지). 발송 성공 시 postSlot/alerts/swingAlerts 마킹.
    if not point_exists(history, bundle["date"], point_label):
        append_history({
            "ts": now.isoformat(timespec="minutes"),
            "date": bundle["date"], "slotLabel": point_label,
            "postSlot": (post_slot if (do_post and posted_ok) else None),
            "alerts": alerted, "swingAlerts": swing_tags,
            "rates": snapshot,
        })
        print("히스토리 기록: %s (%s)" % (HISTORY_FILE, point_label))

    if do_post and not posted_ok:
        return 1
    return 0


from app_html import SPA_HTML  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
