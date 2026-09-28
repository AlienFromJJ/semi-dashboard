(() => {
const $ = s => document.querySelector(s);
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const S = { summary: null, memory: null, macro: null, cache: {}, cur: "SOX", period: "1Y", ma: { 20: true, 60: true, 120: false, 200: false }, group: "KR", sort: { k: null, dir: -1 }, plot: null };
const PERIODS = [["1M", 21], ["3M", 63], ["6M", 126], ["1Y", 252], ["3Y", 756], ["5Y", 99999]];
const MA_COL = { 20: "#EAC26B", 60: "#72BC8F", 120: "#BF8EDA", 200: "#DE9255" };
const TILE_IDS = ["SOX", "NDX", "KOSPI", "KOSDAQ", "USDKRW", "US10Y", "VIX", "COPPER"];
const bust = () => "?t=" + Math.floor(Date.now() / 300000);
const getJSON = async (u, fallback) => { try { const r = await fetch(u + bust()); if (!r.ok) throw 0; return await r.json(); } catch { return fallback; } };

// ---------- formatting
const nf = (v, d) => v == null || isNaN(v) ? "–" : v.toLocaleString("ko-KR", { minimumFractionDigits: d, maximumFractionDigits: d });
const dec = cur => cur === "KRW" || cur === "JPY" ? 0 : cur === "%" ? 3 : 2;
const fmtPrice = (v, cur) => { const s = nf(v, dec(cur)); return cur === "KRW" ? s + "원" : cur === "USD" ? "$" + s : cur === "JPY" ? "¥" + s : cur === "%" ? s + "%" : s; };
const pct = (v, d = 1) => v == null ? "–" : (v > 0 ? "+" : "") + nf(v, d) + "%";
const cls = v => v == null ? "" : v > 0 ? "up" : v < 0 ? "down" : "";
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const scoreColor = s => s >= 80 ? css("--red") : s >= 62 ? css("--orange") : s >= 45 ? css("--blue") : s >= 30 ? "#7D7A75" : "#5B6B8C";

function spark(arr, w = 72, h = 28, color) {
  const a = (arr || []).filter(v => v != null);
  if (a.length < 2) return `<svg width="${w}" height="${h}"></svg>`;
  const mn = Math.min(...a), mx = Math.max(...a), rg = mx - mn || 1;
  const pts = a.map((v, i) => `${(i / (a.length - 1) * (w - 2) + 1).toFixed(1)},${(h - 2 - (v - mn) / rg * (h - 4)).toFixed(1)}`).join(" ");
  const c = color || (a[a.length - 1] >= a[0] ? css("--up") : css("--down"));
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="${c}" stroke-width="1.6" stroke-linejoin="round"/></svg>`;
}

// ---------- header
function renderUpdated() {
  const u = new Date(S.summary.updated), el = $("#updated");
  const mins = Math.round((Date.now() - u) / 60000);
  const rel = mins < 1 ? "방금" : mins < 60 ? `${mins}분 전` : mins < 1440 ? `${Math.round(mins / 60)}시간 전` : `${Math.round(mins / 1440)}일 전`;
  el.innerHTML = `${rel} 업데이트<span class="abs"> · ${u.toLocaleString("ko-KR", { timeZone: "Asia/Seoul", month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" })} KST</span>`;
  el.classList.toggle("stale", mins > 60 * 26);
}

// ---------- thermometer
function renderThermo() {
  const t = S.summary.thermo, sc = t.score ?? 0;
  const R = 110, cx = 130, cy = 130;
  const arc = (a0, a1) => { const p = a => [cx + R * Math.cos(Math.PI * (1 - a)), cy - R * Math.sin(Math.PI * (1 - a))]; const [x0, y0] = p(a0), [x1, y1] = p(a1); return `M${x0.toFixed(1)} ${y0.toFixed(1)} A${R} ${R} 0 0 1 ${x1.toFixed(1)} ${y1.toFixed(1)}`; };
  const segs = [[0, .30, "#5B6B8C"], [.30, .45, "#9A978F"], [.45, .62, css("--blue")], [.62, .80, css("--orange")], [.80, 1, css("--red")]];
  const ang = Math.PI * (1 - sc / 100), nx = cx + (R - 26) * Math.cos(ang), ny = cy - (R - 26) * Math.sin(ang);
  $("#gauge").innerHTML = `<svg viewBox="0 0 260 150" role="img" aria-label="경기 온도 ${sc}점, ${t.regime}">
    ${segs.map(([a, b, c]) => `<path d="${arc(a + .004, b - .004)}" stroke="${c}" stroke-width="16" fill="none" opacity=".9"/>`).join("")}
    <line x1="${cx}" y1="${cy}" x2="${nx.toFixed(1)}" y2="${ny.toFixed(1)}" stroke="${css("--tx")}" stroke-width="3" stroke-linecap="round"/>
    <circle cx="${cx}" cy="${cy}" r="6" fill="${css("--tx")}"/>
    <text x="14" y="148" font-size="11" fill="${css("--tx2")}">침체</text><text x="222" y="148" font-size="11" fill="${css("--tx2")}">과열</text>
  </svg><div class="g-score num">${sc}</div>
  <div class="g-reg" style="background:${scoreColor(sc)}1f;color:${scoreColor(sc)}">${t.regime ?? "–"}</div>`;
  const hot = t.components.filter(c => c.score >= 65).map(c => c.label), cold = t.components.filter(c => c.score < 35).map(c => c.label);
  $("#thermo-note").textContent = [hot.length && `강세: ${hot.join("·")}`, cold.length && `약세: ${cold.join("·")}`].filter(Boolean).join("  |  ");
  $("#comps").innerHTML = t.components.map(c => `<div class="comp" title="${esc(c.desc)}">
    <div class="comp-l">${esc(c.label)}</div>
    <div><div class="bar"><i style="width:${c.score}%;background:${scoreColor(c.score)}"></i></div><div class="comp-v">${esc(c.value)}<span class="cd"> · ${esc(c.desc)}</span></div></div>
    <div class="comp-s num">${c.score}</div></div>`).join("");
}

// ---------- tiles
function renderTiles() {
  const M = byId();
  $("#tiles").innerHTML = TILE_IDS.filter(id => M[id]).map(id => { const m = M[id];
    return `<button class="tile" data-id="${id}"><span class="t-n">${esc(m.name)}</span><span class="t-v num">${fmtPrice(m.last, m.cur === "PT" ? "" : m.cur)}</span><span class="t-c num ${cls(m.chg1d)}">${pct(m.chg1d, 2)} <span class="muted">· 1M ${pct(m.r1m)}</span></span>${spark(m.spark.slice(-44))}</button>`; }).join("");
  $("#tiles").onclick = e => { const b = e.target.closest("[data-id]"); if (b) select(b.dataset.id, true); };
}

// ---------- chart
const byId = () => Object.fromEntries(S.summary.series.map(m => [m.id, m]));
function info(id) {
  const m = byId()[id]; if (m) return { ...m, kind: "price", file: m.file };
  const d = S.summary.derived[id]; if (d) return { ...d, id, name: d.title, kind: "derived", file: id, cur: d.unit === "%" ? "pctv" : "" };
}
async function load(file) { return S.cache[file] ??= await getJSON(`data/prices/${file}.json`, { d: [], c: [] }); }
const maArr = (c, n) => { const o = new Array(c.length).fill(null); let s = 0; for (let i = 0; i < c.length; i++) { s += c[i]; if (i >= n) s -= c[i - n]; if (i >= n - 1) o[i] = s / n; } return o; };

function buildSelect() {
  const G = { INDEX: "지수", KR: "국내 종목", GLOBAL: "해외 종목", MACRO: "매크로" };
  let h = Object.entries(G).map(([g, l]) => `<optgroup label="${l}">${S.summary.series.filter(m => m.group === g).map(m => `<option value="${m.id}">${esc(m.name)}</option>`).join("")}</optgroup>`).join("");
  h += `<optgroup label="괴리율 · 상대강도">${Object.entries(S.summary.derived).map(([k, d]) => `<option value="${k}">${esc(d.title)}</option>`).join("")}</optgroup>`;
  $("#sel").innerHTML = h; $("#sel").onchange = e => select(e.target.value);
  $("#periods").innerHTML = PERIODS.map(([p]) => `<button role="tab" data-p="${p}">${p}</button>`).join("");
  $("#periods").onclick = e => { const b = e.target.closest("[data-p]"); if (b) { S.period = b.dataset.p; drawChart(); } };
}
function select(id, scroll) { S.cur = id; $("#sel").value = id; drawChart(); if (scroll) $("#chart").scrollIntoView(); history.replaceState(null, "", "#" + encodeURIComponent(id)); }

async function drawChart() {
  const it = info(S.cur); if (!it) return;
  const raw = await load(it.file);
  const n = PERIODS.find(p => p[0] === S.period)[1], from = Math.max(0, raw.d.length - n - 1);
  const d = raw.d.slice(from), c = raw.c.slice(from);
  document.querySelectorAll("#periods button").forEach(b => b.setAttribute("aria-selected", b.dataset.p === S.period));
  $("#c-name").textContent = it.name;
  $("#c-sub").textContent = it.kind === "price" ? `${it.sub} · ${it.symbol} · ${it.src}` : it.formula;
  const f = v => it.kind === "derived" ? nf(v, it.unit === "배" ? 3 : 2) + (it.unit === "%" ? "%" : it.unit === "배" ? "배" : "") : fmtPrice(v, it.cur === "PT" ? "" : it.cur);
  const mx = Math.max(...c), mn = Math.min(...c), avg = c.reduce((a, b) => a + b, 0) / c.length;
  const iMx = c.indexOf(mx), iMn = c.indexOf(mn), chg = (c[c.length - 1] / c[0] - 1) * 100;
  const stats = [["현재", f(c[c.length - 1]), d[d.length - 1]],
    it.kind === "price" ? ["기간 수익률", `<span class="${cls(chg)}">${pct(chg)}</span>`, `${d[0]} 부터`] : ["기간 평균", f(avg), `σ ${nf(Math.sqrt(c.reduce((a, b) => a + (b - avg) ** 2, 0) / c.length), 2)}`],
    ["최대", f(mx), d[iMx]], ["최소", f(mn), d[iMn]],
    it.kind === "price" ? ["이격도 20 · RSI", `${nf(it.disp20, 1)} · ${nf(it.rsi, 0)}`, `60일 ${nf(it.disp60, 1)} · 120일 ${nf(it.disp120, 1)}`] : ["1년 평균 대비", `${it.z > 0 ? "+" : ""}${nf(it.z, 2)}σ`, `1년 평균 ${f(it.mean1y)}`]];
  $("#c-stats").innerHTML = stats.map(([k, v, s]) => `<div class="stat"><div class="k">${k}</div><div class="v num">${v}</div><div class="s num">${s}</div></div>`).join("");
  $("#c-foot").textContent = `${d.length}거래일 · ${d[0]} → ${d[d.length - 1]}` + (it.kind === "price" ? ` · 일봉 종가 기준 · 출처 ${it.src}` : "");

  const xs = d.map(s => Date.parse(s + "T00:00:00Z") / 1000);
  const main = css("--blue"), grid = css("--bd"), tx2 = css("--tx2");
  const series = [{}, { label: it.name, stroke: main, width: 2, fill: main + "14", value: (u, v) => v == null ? "–" : f(v) }];
  const data = [xs, c];
  const tog = it.kind === "price" ? [20, 60, 120, 200] : [];
  tog.forEach(p => { if (S.ma[p]) { const m = maArr(raw.c, p).slice(from); series.push({ label: `${p}일선`, stroke: MA_COL[p], width: 1.4, value: (u, v) => v == null ? "–" : f(v) }); data.push(m); } });
  if (it.kind === "derived") { series.push({ label: "기간 평균", stroke: tx2, width: 1, dash: [4, 4], value: () => f(avg) }); data.push(c.map(() => avg)); }
  $("#ma-toggles").innerHTML = tog.map(p => `<button class="chip" data-ma="${p}" aria-pressed="${S.ma[p]}"><i style="background:${MA_COL[p]}"></i>${p}일 이동평균</button>`).join("");
  $("#ma-toggles").onclick = e => { const b = e.target.closest("[data-ma]"); if (b) { S.ma[b.dataset.ma] = !S.ma[b.dataset.ma]; drawChart(); } };

  const el = $("#plot"); S.plot?.destroy(); el.innerHTML = "";
  const w = el.clientWidth, h = w < 600 ? 280 : 340;
  const axis = { stroke: tx2, grid: { stroke: grid, width: 1 }, ticks: { stroke: grid, width: 1 }, font: "12px system-ui" };
  S.plot = new uPlot({ width: w, height: h, series, cursor: { drag: { x: false } }, legend: { live: true },
    scales: { x: { time: true } },
    axes: [{ ...axis, values: (u, v) => v.map(t => { const x = new Date(t * 1000); return n <= 126 ? `${x.getUTCMonth() + 1}/${x.getUTCDate()}` : `${String(x.getUTCFullYear()).slice(2)}.${String(x.getUTCMonth() + 1).padStart(2, "0")}`; }) },
      { ...axis, size: 64, values: (u, v) => v.map(x => x >= 100000 ? nf(x / 1000, 0) + "k" : nf(x, x < 10 ? 2 : 0)) }] }, data, el);
}
window.addEventListener("resize", () => { clearTimeout(S.rt); S.rt = setTimeout(drawChart, 150); });

// ---------- spreads
function renderSpreads() {
  $("#spread-cards").innerHTML = Object.entries(S.summary.derived).map(([k, d]) => {
    const u = d.unit === "%" ? "%" : d.unit === "배" ? "배" : "", dg = d.unit === "배" ? 3 : 2;
    const pos = Math.max(2, Math.min(98, 50 + d.z / 3 * 50));
    return `<button class="sp" data-id="${k}"><div class="t">${esc(d.title)}</div><div class="f">${esc(d.formula)}</div>
      <div class="v num">${nf(d.last, dg)}${u}</div>
      <div class="m num"><span>1년 평균 ${nf(d.mean1y, dg)}${u}</span><span>최대 ${nf(d.max1y, dg)}</span><span>최소 ${nf(d.min1y, dg)}</span></div>
      <div class="zbar"><b style="left:${pos}%"></b></div><div class="zl"><span>−3σ</span><span>평균 대비 ${d.z > 0 ? "+" : ""}${nf(d.z, 2)}σ</span><span>+3σ</span></div></button>`; }).join("");
  $("#spread-cards").onclick = e => { const b = e.target.closest("[data-id]"); if (b) select(b.dataset.id, true); };
}

// ---------- table
const COLS = [["name", "종목"], ["last", "현재가"], ["chg1d", "1일"], ["r1m", "1개월"], ["r3m", "3개월"], ["ytd", "연초 대비"], ["r1y", "1년"], ["dd52", "52주 고점 대비"], ["disp20", "이격도 20"], ["disp60", "이격도 60"], ["rsi", "RSI"], ["above200", "장기 추세"], ["spark", "3개월 추이"]];
function renderTable() {
  $("#groups").innerHTML = [["KR", "국내"], ["GLOBAL", "해외"], ["ALL", "전체"]].map(([g, l]) => `<button role="tab" data-g="${g}" aria-selected="${S.group === g}">${l}</button>`).join("");
  $("#groups").onclick = e => { const b = e.target.closest("[data-g]"); if (b) { S.group = b.dataset.g; renderTable(); } };
  let rows = S.summary.series.filter(m => S.group === "ALL" ? ["KR", "GLOBAL"].includes(m.group) : m.group === S.group);
  if (S.sort.k) rows = [...rows].sort((a, b) => { const x = a[S.sort.k], y = b[S.sort.k]; return (typeof x === "string" ? x.localeCompare(y) : (x ?? -1e9) - (y ?? -1e9)) * S.sort.dir; });
  const dispPill = v => v == null ? "–" : `<span class="${v >= 115 ? "pill p-red" : v <= 88 ? "pill p-blue" : ""}">${nf(v, 1)}</span>`;
  const rsiPill = v => v == null ? "–" : `<span class="${v >= 70 ? "pill p-red" : v <= 30 ? "pill p-blue" : ""}">${nf(v, 0)}</span>`;
  $("#tbl").innerHTML = `<thead><tr>${COLS.map(([k, l]) => `<th data-k="${k}" class="${S.sort.k === k ? "sorted" : ""}" ${k !== "spark" ? 'tabindex="0"' : ""}>${l}${S.sort.k === k ? (S.sort.dir > 0 ? " ↑" : " ↓") : ""}</th>`).join("")}</tr></thead><tbody>${rows.map(m => `<tr data-id="${m.id}">
    <td><div class="nm">${esc(m.name)}</div><div class="sub">${esc(m.sub)} · ${esc(m.symbol)}</div></td>
    <td class="num">${fmtPrice(m.last, m.cur)}</td>
    ${["chg1d", "r1m", "r3m", "ytd", "r1y"].map(k => `<td class="num ${cls(m[k])}">${pct(m[k])}</td>`).join("")}
    <td class="num">${pct(m.dd52)}</td><td class="num">${dispPill(m.disp20)}</td><td class="num">${dispPill(m.disp60)}</td><td class="num">${rsiPill(m.rsi)}</td>
    <td>${m.above200 == null ? "–" : m.above200 ? '<span class="pill p-green">200일선 위</span>' : '<span class="pill p-gray">200일선 아래</span>'}</td>
    <td>${spark(m.spark, 70, 24)}</td></tr>`).join("")}</tbody>`;
  const sortBy = k => { if (!k || k === "spark") return; S.sort = { k, dir: S.sort.k === k ? -S.sort.dir : (k === "name" ? 1 : -1) }; renderTable(); };
  $("#tbl thead").onclick = e => sortBy(e.target.closest("th")?.dataset.k);
  $("#tbl thead").onkeydown = e => { if (e.key === "Enter") sortBy(e.target.dataset.k); };
  $("#tbl tbody").onclick = e => { const r = e.target.closest("tr"); if (r) select(r.dataset.id, true); };
}

// ---------- memory
function renderMemory() {
  const mem = S.memory, items = Object.entries(mem?.items || {});
  if (!items.length) { $("#mem-groups").innerHTML = `<div class="empty">메모리 가격 데이터를 아직 수집하지 못했습니다.</div>`; return; }
  const days = Math.max(...items.map(([, v]) => v.hist.length));
  $("#mem-note").textContent = `${mem.source}. 현물가는 계약가보다 먼저 움직이는 업황 선행 지표입니다. 매 업데이트마다 기록이 누적되며 현재 ${days}회분이 쌓였습니다.`;
  const order = ["D램 현물", "낸드 플래시", "D램 모듈", "GDDR (그래픽 D램)", "메모리 카드"];
  const cats = [...new Set(items.map(([, v]) => v.cat))].sort((a, b) => order.indexOf(a) - order.indexOf(b));
  $("#mem-groups").innerHTML = cats.map(cat => `<div class="mem"><h3>${esc(cat)}</h3><table><thead><tr><th>품목</th><th>평균가</th><th class="hl">고가 / 저가</th><th>변동</th><th>추이</th></tr></thead><tbody>
    ${items.filter(([, v]) => v.cat === cat).map(([n, v]) => `<tr><td>${esc(n)}</td><td class="num">$${nf(v.avg, 3)}</td><td class="num muted hl">${nf(v.high, 2)} / ${nf(v.low, 2)}</td><td class="num ${cls(v.chg)}">${pct(v.chg, 2)}</td><td>${v.hist.length > 1 ? spark(v.hist.map(h => h[1]), 60, 22) : '<span class="muted small">누적 중</span>'}</td></tr>`).join("")}
  </tbody></table><div class="muted small" style="margin-top:8px">${[...new Set(items.filter(([, v]) => v.cat === cat).map(([, v]) => v.freq === "weekly" ? "주간" : "일간"))].join("·")} 세션 기준 · 변동은 직전 세션 대비</div></div>`).join("");
}

// ---------- macro
function renderMacro() {
  const e = Object.entries(S.macro || {});
  if (!e.length) { $("#macro").innerHTML = `<div class="empty">FRED 지표는 다음 자동 업데이트에서 채워집니다. (미국 반도체 산업생산, 반도체 PPI, 전자제품 신규주문)</div>`; return; }
  $("#macro").innerHTML = e.map(([k, m]) => `<div class="mac"><div class="muted small">${esc(m.title)}</div><div class="v num">${m.lastYoy == null ? nf(m.last, 1) : pct(m.lastYoy)}</div><div class="muted small">전년 대비 · ${m.date.slice(0, 7)} · ${esc(k)}</div><div style="margin-top:10px">${spark(m.yoy.slice(-36), 240, 44, css("--blue"))}</div></div>`).join("");
}

// ---------- signals
function renderSignals() {
  const L = { hot: "p-orange", cold: "p-blue", up: "p-green", down: "p-red", info: "p-gray" };
  const s = S.summary.signals;
  $("#sig").innerHTML = s.length ? s.map(x => `<button class="sig" data-id="${esc(x.id)}"><span class="pill ${L[x.lvl] || "p-gray"}">${esc(x.tag)}</span><span>${esc(x.text)}</span></button>`).join("") : `<div class="empty">오늘 탐지된 신호가 없습니다.</div>`;
  $("#sig").onclick = e => { const b = e.target.closest("[data-id]"); if (b && info(b.dataset.id)) select(b.dataset.id, true); };
}

async function init() {
  [S.summary, S.memory, S.macro] = await Promise.all([getJSON("data/summary.json"), getJSON("data/memory.json", {}), getJSON("data/macro.json", {})]);
  if (!S.summary) { $("#updated").textContent = "데이터를 불러오지 못했습니다"; return; }
  const hash = decodeURIComponent(location.hash.slice(1)); if (info(hash)) S.cur = hash;
  renderUpdated(); renderThermo(); renderTiles(); buildSelect(); $("#sel").value = S.cur; drawChart();
  renderSpreads(); renderTable(); renderMemory(); renderMacro(); renderSignals();
}
init();
setInterval(async () => { const s = await getJSON("data/summary.json"); if (s && s.updated !== S.summary?.updated) { S.cache = {}; init(); } else if (S.summary) renderUpdated(); }, 5 * 60 * 1000);
})();
