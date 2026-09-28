#!/usr/bin/env python3
"""반도체 대시보드 데이터 수집기.

- 국내 종목: 네이버 금융 일봉 (fchart.stock.naver.com)
- 해외 종목/지수/환율/원자재: Yahoo Finance chart API
- 메모리 현물가: DRAMeXchange 메인 페이지 (매 실행마다 누적 저장)
- 거시지표: FRED CSV (접속 불가 시 건너뜀)

외부 패키지: beautifulsoup4 (메모리 가격 파싱용)
실행: python scripts/update_data.py
"""
import csv, io, json, math, os, re, sys, time, urllib.request, urllib.parse
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
PRICES = os.path.join(DATA, "prices")
KST = timezone(timedelta(hours=9))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
YEARS = 5

# ---------------------------------------------------------------- universe
# (id, 이름, 출처, 심볼, 그룹, 세부분류, 통화)
UNIVERSE = [
    # 국내
    ("005930", "삼성전자", "naver", "005930", "KR", "메모리/종합", "KRW"),
    ("005935", "삼성전자우", "naver", "005935", "KR", "메모리/종합", "KRW"),
    ("000660", "SK하이닉스", "naver", "000660", "KR", "메모리", "KRW"),
    ("402340", "SK스퀘어", "naver", "402340", "KR", "지주(하이닉스)", "KRW"),
    ("042700", "한미반도체", "naver", "042700", "KR", "후공정 장비(HBM)", "KRW"),
    ("000990", "DB하이텍", "naver", "000990", "KR", "파운드리", "KRW"),
    ("058470", "리노공업", "naver", "058470", "KR", "테스트 소켓", "KRW"),
    ("039030", "이오테크닉스", "naver", "039030", "KR", "레이저 장비", "KRW"),
    ("403870", "HPSP", "naver", "403870", "KR", "전공정 장비", "KRW"),
    ("240810", "원익IPS", "naver", "240810", "KR", "전공정 장비", "KRW"),
    ("036930", "주성엔지니어링", "naver", "036930", "KR", "전공정 장비", "KRW"),
    ("095340", "ISC", "naver", "095340", "KR", "테스트 소켓", "KRW"),
    ("357780", "솔브레인", "naver", "357780", "KR", "소재", "KRW"),
    ("005290", "동진쎄미켐", "naver", "005290", "KR", "소재", "KRW"),
    ("108320", "LX세미콘", "naver", "108320", "KR", "팹리스", "KRW"),
    # 해외
    ("NVDA", "엔비디아", "yahoo", "NVDA", "GLOBAL", "AI 가속기", "USD"),
    ("AVGO", "브로드컴", "yahoo", "AVGO", "GLOBAL", "ASIC/네트워크", "USD"),
    ("TSM", "TSMC (ADR)", "yahoo", "TSM", "GLOBAL", "파운드리", "USD"),
    ("AMD", "AMD", "yahoo", "AMD", "GLOBAL", "CPU/GPU", "USD"),
    ("MU", "마이크론", "yahoo", "MU", "GLOBAL", "메모리", "USD"),
    ("ASML", "ASML", "yahoo", "ASML", "GLOBAL", "노광 장비", "USD"),
    ("AMAT", "어플라이드 머티어리얼즈", "yahoo", "AMAT", "GLOBAL", "전공정 장비", "USD"),
    ("LRCX", "램리서치", "yahoo", "LRCX", "GLOBAL", "식각/증착 장비", "USD"),
    ("KLAC", "KLA", "yahoo", "KLAC", "GLOBAL", "검사 장비", "USD"),
    ("8035.T", "도쿄일렉트론", "yahoo", "8035.T", "GLOBAL", "전공정 장비", "JPY"),
    ("QCOM", "퀄컴", "yahoo", "QCOM", "GLOBAL", "모바일 AP", "USD"),
    ("ARM", "Arm", "yahoo", "ARM", "GLOBAL", "IP", "USD"),
    ("MRVL", "마벨", "yahoo", "MRVL", "GLOBAL", "데이터센터 칩", "USD"),
    ("TXN", "텍사스 인스트루먼트", "yahoo", "TXN", "GLOBAL", "아날로그", "USD"),
    ("INTC", "인텔", "yahoo", "INTC", "GLOBAL", "CPU/파운드리", "USD"),
    ("WDC", "웨스턴디지털", "yahoo", "WDC", "GLOBAL", "스토리지", "USD"),
    # 지수·매크로
    ("SOX", "필라델피아 반도체지수", "yahoo", "^SOX", "INDEX", "반도체", "PT"),
    ("NDX", "나스닥 종합", "yahoo", "^IXIC", "INDEX", "주가지수", "PT"),
    ("SPX", "S&P 500", "yahoo", "^GSPC", "INDEX", "주가지수", "PT"),
    ("KOSPI", "코스피", "yahoo", "^KS11", "INDEX", "주가지수", "PT"),
    ("KOSDAQ", "코스닥", "yahoo", "^KQ11", "INDEX", "주가지수", "PT"),
    ("USDKRW", "원/달러 환율", "yahoo", "KRW=X", "MACRO", "환율", "KRW"),
    ("US10Y", "미국 10년물 금리", "yahoo", "^TNX", "MACRO", "금리", "%"),
    ("VIX", "VIX 변동성", "yahoo", "^VIX", "MACRO", "변동성", "PT"),
    ("COPPER", "구리 선물", "yahoo", "HG=F", "MACRO", "원자재", "USD"),
]
MEMORY_BASKET = ["005930", "000660", "MU"]
EQUIPMENT_BASKET = ["ASML", "AMAT", "LRCX", "KLAC", "8035.T"]
FRED = [
    ("IPG3344S", "미국 반도체·전자부품 산업생산", "지수(2017=100)"),
    ("PCU33443344", "미국 반도체·전자부품 생산자물가(PPI)", "지수"),
    ("A34SNO", "미국 컴퓨터·전자제품 신규주문", "백만 달러"),
]


def get(url, timeout=25, retries=3):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa
            last = e
            time.sleep(1.5 * (i + 1))
    raise last


# ---------------------------------------------------------------- fetchers
def fetch_naver(code):
    raw = get(f"https://fchart.stock.naver.com/sise.nhn?symbol={code}&timeframe=day&count={YEARS*250+30}&requestType=0").decode("euc-kr", "ignore")
    d, c = [], []
    for m in re.finditer(r'data="(\d{8})\|[^|]*\|[^|]*\|[^|]*\|([\d.]+)\|', raw):
        s = m.group(1)
        d.append(f"{s[:4]}-{s[4:6]}-{s[6:]}")
        c.append(float(m.group(2)))
    return d, c


def fetch_yahoo(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?range={YEARS}y&interval=1d&includePrePost=false"
    j = json.loads(get(url))
    r = j["chart"]["result"][0]
    tz = r["meta"].get("gmtoffset", 0)
    ts = r.get("timestamp") or []
    cl = r["indicators"]["quote"][0]["close"]
    d, c = [], []
    for t, v in zip(ts, cl):
        if v is None:
            continue
        day = datetime.fromtimestamp(t + tz, tz=timezone.utc).strftime("%Y-%m-%d")
        if d and d[-1] == day:
            c[-1] = v
            continue
        d.append(day)
        c.append(round(v, 4))
    # 장중 최신가 반영
    mp = r["meta"].get("regularMarketPrice")
    mt = r["meta"].get("regularMarketTime")
    if mp and mt:
        day = datetime.fromtimestamp(mt + tz, tz=timezone.utc).strftime("%Y-%m-%d")
        if d and d[-1] == day:
            c[-1] = round(mp, 4)
        elif not d or day > d[-1]:
            d.append(day); c.append(round(mp, 4))
    return d, c


def fetch_fred(sid):
    raw = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", timeout=30, retries=2).decode()
    d, v = [], []
    for row in csv.reader(io.StringIO(raw)):
        if len(row) < 2 or not re.match(r"\d{4}-", row[0]) or row[1] in (".", ""):
            continue
        d.append(row[0]); v.append(float(row[1]))
    return d, v


def fetch_memory():
    from bs4 import BeautifulSoup
    html = get("https://www.dramexchange.com/").decode("utf-8", "ignore")
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for t in soup.find_all("table"):
        rows = [[c.get_text(" ", strip=True) for c in r.find_all(["td", "th"])] for r in t.find_all("tr")]
        rows = [r for r in rows if any(r)]
        if not rows or rows[0][:1] != ["Item"] or len(rows[0]) < 7:
            continue
        freq = "weekly" if "Weekly" in rows[0][1] else "daily"
        for r in rows[1:]:
            name = re.sub(r"\s+", " ", r[0]).strip()
            try:
                avg = float(r[5]); hi = float(r[3]); lo = float(r[4])
                chg = float(r[6].replace("%", "").strip())
            except (ValueError, IndexError):
                continue
            out.append({"name": name, "cat": classify(name), "freq": freq, "avg": avg, "high": hi, "low": lo, "chg": chg})
    return out


def classify(n):
    if n.startswith("GDDR"): return "GDDR (그래픽 D램)"
    if "DIMM" in n: return "D램 모듈"
    if n.startswith("DDR"): return "D램 현물"
    if "MicroSD" in n or "SD" in n.split()[0]: return "메모리 카드"
    if "TLC" in n or n.startswith(("SLC", "MLC")): return "낸드 플래시"
    return "기타"


# ---------------------------------------------------------------- indicators
def sma(a, n):
    if len(a) < n: return None
    return sum(a[-n:]) / n


def rsi(a, n=14):
    if len(a) < n * 3: return None
    g = l = 0.0
    for i in range(1, n + 1):
        ch = a[i] - a[i - 1]; g += max(ch, 0); l += max(-ch, 0)
    g /= n; l /= n
    for i in range(n + 1, len(a)):
        ch = a[i] - a[i - 1]
        g = (g * (n - 1) + max(ch, 0)) / n
        l = (l * (n - 1) + max(-ch, 0)) / n
    return 100.0 if l == 0 else 100 - 100 / (1 + g / l)


def ret(a, k):
    if len(a) <= k or a[-1 - k] == 0: return None
    return (a[-1] / a[-1 - k] - 1) * 100


def cross_days(c, fast=50, slow=200, lookback=30):
    """최근 lookback 거래일 내 골든/데드크로스 발생 시 (종류, 경과일)"""
    if len(c) < slow + lookback + 1: return None
    def diff(i):
        s = c[: i + 1]
        return sum(s[-fast:]) / fast - sum(s[-slow:]) / slow
    prev = diff(len(c) - lookback - 1)
    for i in range(len(c) - lookback, len(c)):
        cur = diff(i)
        if prev <= 0 < cur: kind = "golden"
        elif prev >= 0 > cur: kind = "dead"
        else: kind = None
        if kind: found = (kind, len(c) - 1 - i)
        prev = cur
    return locals().get("found")


def metrics(d, c):
    last = c[-1]
    y0 = [v for dd, v in zip(d, c) if dd[:4] < d[-1][:4]]
    w = c[-252:]
    ma = {n: sma(c, n) for n in (5, 20, 60, 120, 200)}
    rets = [math.log(c[i] / c[i - 1]) for i in range(max(1, len(c) - 20), len(c)) if c[i - 1] > 0]
    vol = (sum((x - sum(rets) / len(rets)) ** 2 for x in rets) / max(1, len(rets) - 1)) ** 0.5 * math.sqrt(252) * 100 if len(rets) > 5 else None
    m = {
        "last": last, "date": d[-1],
        "chg1d": ret(c, 1), "r1w": ret(c, 5), "r1m": ret(c, 21), "r3m": ret(c, 63), "r6m": ret(c, 126), "r1y": ret(c, 252),
        "ytd": (last / y0[-1] - 1) * 100 if y0 else None,
        "hi52": max(w), "lo52": min(w), "dd52": (last / max(w) - 1) * 100,
        "rsi": rsi(c[-400:]), "vol20": vol,
        **{f"disp{n}": (last / v * 100 if v else None) for n, v in ma.items() if n != 5},
        "above200": (last > ma[200]) if ma[200] else None,
        "newHigh": last >= max(w) * 0.999,
        "cross": cross_days(c),
        "spark": [round(x, 4) for x in c[-66:]],
    }
    return {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items()}


def align(series_a, series_b):
    da = dict(zip(*series_a)); db = dict(zip(*series_b))
    ds = sorted(set(da) & set(db))
    return ds, [da[x] for x in ds], [db[x] for x in ds]


def basket(dates, members):
    """dates 기준 동일가중 지수(시작=100), 각 종목 전일가 이월"""
    out = []
    ptrs = []
    for d, c in members:
        m = dict(zip(d, c)); ptrs.append((sorted(m), m))
    vals = [None] * len(members)
    base = [None] * len(members)
    idx = [0] * len(members)
    for day in dates:
        for k, (keys, m) in enumerate(ptrs):
            while idx[k] < len(keys) and keys[idx[k]] <= day:
                vals[k] = m[keys[idx[k]]]; idx[k] += 1
        if any(v is None for v in vals):
            out.append(None); continue
        for k in range(len(vals)):
            if base[k] is None: base[k] = vals[k]
        out.append(round(sum(v / b for v, b in zip(vals, base)) / len(vals) * 100, 3))
    return out


def scale(x, lo, hi):
    if x is None: return None
    return max(0.0, min(100.0, (x - lo) / (hi - lo) * 100))


def zscore(arr):
    n = len(arr); mu = sum(arr) / n
    sd = (sum((v - mu) ** 2 for v in arr) / n) ** 0.5
    return mu, sd, ((arr[-1] - mu) / sd if sd else 0)


# ---------------------------------------------------------------- main
def main():
    os.makedirs(PRICES, exist_ok=True)
    now = datetime.now(KST)
    series, meta, errors = {}, [], []
    for sid, name, src, sym, grp, sub, cur in UNIVERSE:
        try:
            d, c = fetch_naver(sym) if src == "naver" else fetch_yahoo(sym)
            if len(c) < 30: raise ValueError("데이터 부족")
            series[sid] = (d, c)
            with open(os.path.join(PRICES, f"{safe(sid)}.json"), "w") as f:
                json.dump({"d": d, "c": c}, f, separators=(",", ":"))
            meta.append({"id": sid, "file": safe(sid), "name": name, "src": "네이버 금융" if src == "naver" else "Yahoo Finance",
                         "symbol": sym, "group": grp, "sub": sub, "cur": cur, **metrics(d, c)})
        except Exception as e:
            errors.append(f"{sid}: {e}")
            print("WARN", sid, e, file=sys.stderr)
        time.sleep(0.25)

    # ---- 괴리율/상대강도 시계열
    derived = {}
    def put(key, title, formula, d, v, unit):
        with open(os.path.join(PRICES, f"{key}.json"), "w") as f:
            json.dump({"d": d, "c": v}, f, separators=(",", ":"))
        win = v[-252:]
        mu, sd, z = zscore(win)
        derived[key] = {"title": title, "formula": formula, "unit": unit, "last": round(v[-1], 3), "date": d[-1],
                        "mean1y": round(mu, 3), "sd1y": round(sd, 3), "z": round(z, 2),
                        "max1y": round(max(win), 3), "min1y": round(min(win), 3)}
    if "005930" in series and "005935" in series:
        d, a, b = align(series["005930"], series["005935"])
        put("gap_samsung", "삼성전자 보통주↔우선주 괴리율", "(보통주 − 우선주) ÷ 보통주 × 100", d, [round((x - y) / x * 100, 3) for x, y in zip(a, b)], "%")
    if "402340" in series and "000660" in series:
        d, a, b = align(series["402340"], series["000660"])
        put("ratio_sksq", "SK스퀘어 ÷ SK하이닉스 주가비율", "SK스퀘어 주가 ÷ SK하이닉스 주가 (높을수록 지주 할인 축소)", d, [round(x / y, 4) for x, y in zip(a, b)], "배")
    if "SOX" in series and "NDX" in series:
        d, a, b = align(series["SOX"], series["NDX"])
        put("rs_sox_ndx", "반도체 상대강도 (SOX ÷ 나스닥)", "SOX ÷ 나스닥 × 100 (상승 = 반도체가 시장보다 강함)", d, [round(x / y * 100, 3) for x, y in zip(a, b)], "")
    if "SOX" in series:
        sd = series["SOX"][0]
        mem = [series[k] for k in MEMORY_BASKET if k in series]
        eq = [series[k] for k in EQUIPMENT_BASKET if k in series]
        if mem:
            v = basket(sd, mem); i0 = next(i for i, x in enumerate(v) if x is not None)
            put("idx_memory", "메모리 3사 바스켓 (삼성·하이닉스·마이크론)", "동일가중, 5년 전 = 100", sd[i0:], v[i0:], "")
        if eq:
            v = basket(sd, eq); i0 = next(i for i, x in enumerate(v) if x is not None)
            put("idx_equip", "장비 5사 바스켓 (ASML·AMAT·LRCX·KLA·TEL)", "동일가중, 5년 전 = 100", sd[i0:], v[i0:], "")

    # ---- 메모리 가격 (누적)
    mem_path = os.path.join(DATA, "memory.json")
    memdb = json.load(open(mem_path)) if os.path.exists(mem_path) else {"items": {}}
    today = now.strftime("%Y-%m-%d")
    try:
        for it in fetch_memory():
            rec = memdb["items"].setdefault(it["name"], {"cat": it["cat"], "freq": it["freq"], "hist": []})
            rec.update({k: it[k] for k in ("cat", "freq", "high", "low", "chg")}); rec["avg"] = it["avg"]
            h = rec["hist"]
            if h and h[-1][0] == today: h[-1][1] = it["avg"]
            else: h.append([today, it["avg"]])
            rec["hist"] = h[-1500:]
        memdb["updated"] = now.isoformat(timespec="seconds")
        memdb["source"] = "DRAMeXchange (TrendForce) 현물가, USD"
    except Exception as e:
        errors.append(f"memory: {e}"); print("WARN memory", e, file=sys.stderr)
    json.dump(memdb, open(mem_path, "w"), ensure_ascii=False, separators=(",", ":"))

    # ---- FRED 거시지표 (선택)
    macro_path = os.path.join(DATA, "macro.json")
    macro = json.load(open(macro_path)) if os.path.exists(macro_path) else {}
    for sid, title, unit in FRED:
        try:
            d, v = fetch_fred(sid)
            d, v = d[-120:], v[-120:]
            yoy = [None if i < 12 else round((v[i] / v[i - 12] - 1) * 100, 2) for i in range(len(v))]
            macro[sid] = {"title": title, "unit": unit, "d": d, "v": v, "yoy": yoy, "last": v[-1], "date": d[-1], "lastYoy": yoy[-1]}
        except Exception as e:
            print("WARN fred", sid, e, file=sys.stderr)
    json.dump(macro, open(macro_path, "w"), ensure_ascii=False, separators=(",", ":"))

    # ---- 반도체 경기 온도계
    M = {m["id"]: m for m in meta}
    comps = []
    def comp(key, label, score, value, desc):
        if score is not None:
            comps.append({"key": key, "label": label, "score": round(score), "value": value, "desc": desc})
    sox = M.get("SOX")
    if sox:
        comp("trend", "추세", scale(sox.get("disp200"), 85, 120), f"SOX 200일 이격도 {sox['disp200']:.1f}", "SOX가 200일 이동평균보다 얼마나 위에 있는지")
        comp("momentum", "모멘텀", scale(sox.get("r3m"), -25, 30), f"SOX 3개월 {sox['r3m']:+.1f}%", "최근 3개월 반도체지수 수익률")
    if "rs_sox_ndx" in derived:
        d, v = json.load(open(os.path.join(PRICES, "rs_sox_ndx.json"))).values()
        r = (v[-1] / v[-64] - 1) * 100 if len(v) > 64 else None
        comp("relative", "상대강도", scale(r, -12, 12), f"SOX/나스닥 3개월 {r:+.1f}%", "반도체가 전체 기술주 대비 강한지")
    stocks = [m for m in meta if m["group"] in ("KR", "GLOBAL") and m.get("above200") is not None]
    if stocks:
        br = sum(1 for m in stocks if m["above200"]) / len(stocks) * 100
        comp("breadth", "시장 폭", br, f"{len(stocks)}개 중 {br:.0f}% 200일선 위", "추적 종목 중 장기 상승추세 종목 비율")
    if "idx_memory" in derived:
        d, v = json.load(open(os.path.join(PRICES, "idx_memory.json"))).values()
        r = (v[-1] / v[-64] - 1) * 100 if len(v) > 64 else None
        comp("memory", "메모리 사이클", scale(r, -25, 35), f"메모리 3사 3개월 {r:+.1f}%", "메모리 대표주 3개월 수익률 (D램 업황 선행)")
    dr = [it for n, it in memdb["items"].items() if it["cat"] == "D램 현물" and len(it["hist"]) >= 20]
    if dr:
        ch = sum((it["hist"][-1][1] / it["hist"][-20][1] - 1) * 100 for it in dr) / len(dr)
        comp("dram", "D램 현물가", scale(ch, -15, 15), f"D램 현물 평균 20회 {ch:+.1f}%", "DRAMeXchange 현물가 최근 추세")
    vix = M.get("VIX")
    if vix:
        comp("risk", "위험선호", scale(-vix["last"], -35, -12), f"VIX {vix['last']:.1f}", "변동성이 낮을수록 위험자산 선호")
    ip = macro.get("IPG3344S")
    if ip and ip.get("lastYoy") is not None:
        comp("macro", "실물 생산", scale(ip["lastYoy"], -10, 20), f"美 반도체 산업생산 YoY {ip['lastYoy']:+.1f}%", "실물 경기(후행)")
    score = round(sum(c["score"] for c in comps) / len(comps)) if comps else None
    regime = None
    if score is not None:
        regime = next(lbl for th, lbl in [(80, "과열"), (62, "활황"), (45, "중립"), (30, "둔화"), (-1, "침체")] if score >= th)

    # ---- 투자 신호
    sig = []
    for m in meta:
        if m["group"] not in ("KR", "GLOBAL", "INDEX"): continue
        n, r, d20 = m["name"], m.get("rsi"), m.get("disp20")
        if r and r >= 75: sig.append({"lvl": "hot", "tag": "과매수", "id": m["id"], "text": f"{n} RSI {r:.0f}"})
        if r and r <= 28: sig.append({"lvl": "cold", "tag": "과매도", "id": m["id"], "text": f"{n} RSI {r:.0f}"})
        if d20 and d20 >= 115: sig.append({"lvl": "hot", "tag": "단기 급등", "id": m["id"], "text": f"{n} 20일 이격도 {d20:.0f}"})
        if d20 and d20 <= 88: sig.append({"lvl": "cold", "tag": "단기 급락", "id": m["id"], "text": f"{n} 20일 이격도 {d20:.0f}"})
        if m.get("cross"):
            k, days = m["cross"]
            sig.append({"lvl": "up" if k == "golden" else "down", "tag": "골든크로스" if k == "golden" else "데드크로스",
                        "id": m["id"], "text": f"{n} 50일선이 200일선을 {'상향' if k == 'golden' else '하향'} 돌파 · {days}거래일 전"})
        if m.get("newHigh"): sig.append({"lvl": "up", "tag": "52주 신고가", "id": m["id"], "text": f"{n} 52주 최고가 경신"})
    for k, v in derived.items():
        if abs(v["z"]) >= 1.8:
            sig.append({"lvl": "info", "tag": "극단 구간", "id": k, "text": f"{v['title']} 1년 평균 대비 {v['z']:+.1f}σ"})
    order = {"hot": 0, "down": 1, "cold": 2, "up": 3, "info": 4}
    sig.sort(key=lambda x: order[x["lvl"]])

    summary = {
        "updated": now.isoformat(timespec="seconds"),
        "series": meta, "derived": derived,
        "thermo": {"score": score, "regime": regime, "components": comps},
        "signals": sig[:40], "errors": errors,
    }
    json.dump(summary, open(os.path.join(DATA, "summary.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    print(f"OK {len(meta)} series, {len(derived)} derived, score={score} ({regime}), errors={len(errors)}")


def safe(s):
    return re.sub(r"[^A-Za-z0-9_-]", "_", s)


if __name__ == "__main__":
    main()
