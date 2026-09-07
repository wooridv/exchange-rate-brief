# -*- coding: utf-8 -*-
"""환율 브리핑 대시보드 SPA(정적). data/app.json 을 읽어 렌더.
전일/전시간 대비 그래프 + 모션그래픽 + 규칙기반 AI 매수신호(근거·지표 포함)."""

SPA_HTML = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>환율 브리핑</title>
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<style>
:root{
  --bg:#eef1f6; --panel:#ffffff; --panel2:#f6f8fc; --line:#e2e7f0; --line2:#eef1f7;
  --tx:#141822; --mut:#68728a; --faint:#9aa4ba;
  --accent:#3d6bff; --accent2:#6f9bff; --accentSoft:#e7edff;
  --up:#e23b52; --down:#2f74d0; --neu:#8a90a0;
  --good:#16a34a; --warn:#d97706; --goodSoft:#e6f6ec; --warnSoft:#fdf0dd;
  --shadow:0 1px 2px rgba(20,30,60,.05),0 10px 30px rgba(30,45,90,.07);
}
@media(prefers-color-scheme:dark){:root{
  --bg:#0e1117; --panel:#171b23; --panel2:#141821; --line:#272d3a; --line2:#1c212b;
  --tx:#e9edf6; --mut:#9aa3b8; --faint:#5c6478;
  --accent:#6f9bff; --accent2:#4a74e6; --accentSoft:#1a2540;
  --up:#ff6b7d; --down:#66a6ff; --neu:#7b8296;
  --good:#4ade80; --warn:#fbbf24; --goodSoft:#12291b; --warnSoft:#2e2410;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 12px 34px rgba(0,0,0,.4);
}}
*{box-sizing:border-box}
html,body{margin:0;overflow-x:clip}
body{background:var(--bg);color:var(--tx);
  font-family:Pretendard,-apple-system,BlinkMacSystemFont,"Malgun Gothic",sans-serif;
  font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased;padding-bottom:48px}
.wrap{max-width:1040px;margin:0 auto;padding:0 16px}
a{color:var(--accent);text-decoration:none}
.tabnum{font-variant-numeric:tabular-nums}

/* topbar */
.top{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--bg) 82%,transparent);
  backdrop-filter:saturate(1.4) blur(10px);border-bottom:1px solid var(--line)}
.top .wrap{display:flex;align-items:center;gap:10px;height:58px}
.brand{font-weight:800;letter-spacing:-.02em;font-size:17px;display:flex;align-items:center;gap:8px;white-space:nowrap}
.brand .dot{width:9px;height:9px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 4px var(--accentSoft)}
.spacer{flex:1}
.slotbadge{font-size:12.5px;font-weight:700;color:var(--accent);background:var(--accentSoft);
  padding:6px 11px;border-radius:999px;white-space:nowrap}
.gen{font-size:12px;color:var(--mut);white-space:nowrap}
.live{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:800;color:var(--good);
  background:var(--goodSoft);padding:6px 10px;border-radius:999px;white-space:nowrap}
.lvdot{width:8px;height:8px;border-radius:50%;background:var(--good);animation:pulse 1.4s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.3;transform:scale(.65)}}
@media(max-width:560px){.brand{font-size:15px}.gen{display:none}}

/* hero */
.hero{margin:20px 0 6px}
.hero h1{font-size:22px;font-weight:800;letter-spacing:-.03em;margin:0 0 3px}
.subline{color:var(--mut);font-size:12.5px}

/* currency cards */
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:16px 0}
@media(max-width:880px){.cards{grid-template-columns:repeat(2,1fr)}}
@media(max-width:480px){.cards{grid-template-columns:1fr}}
.cc{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:16px;
  box-shadow:var(--shadow);cursor:pointer;position:relative;overflow:hidden;
  opacity:0;transform:translateY(10px);animation:rise .5s cubic-bezier(.22,1,.36,1) forwards}
.cc:hover{border-color:var(--accent2)}
.cc.sel{border-color:var(--accent);box-shadow:0 0 0 2px var(--accentSoft),var(--shadow)}
@keyframes rise{to{opacity:1;transform:none}}
.cc .top1{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.cc .flag{font-size:20px}
.cc .lab{font-weight:800;font-size:15px}
.cc .unit{font-size:11px;color:var(--faint);margin-left:auto}
.cc .cclab{font-size:11px;color:var(--accent);font-weight:800;letter-spacing:.02em;margin-bottom:1px}
.cc .buy{font-size:27px;font-weight:800;letter-spacing:-.02em;line-height:1.1}
.cc .buy .w{font-size:12px;color:var(--mut);font-weight:700;margin-left:3px}
.cc .rows{display:flex;justify-content:space-between;font-size:12.5px;color:var(--mut);margin-top:6px}
.cc .rows b{color:var(--tx);font-weight:700}
.cc .badges{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}
.dl{display:inline-flex;align-items:center;gap:3px;font-weight:700;font-size:11.5px;padding:3px 8px;border-radius:999px}
.dl small{font-weight:600;opacity:.8}
.dl.up{color:var(--up);background:color-mix(in srgb,var(--up) 12%,transparent)}
.dl.down{color:var(--down);background:color-mix(in srgb,var(--down) 12%,transparent)}
.dl.neu{color:var(--neu);background:var(--line2)}
.cc .spark{margin-top:12px;height:38px;width:100%}
.cc .sigline{display:flex;align-items:center;gap:6px;margin-top:10px;font-size:12px}
.pill{font-weight:800;font-size:11.5px;padding:2px 8px;border-radius:999px}
.pill.good{color:var(--good);background:var(--goodSoft)}
.pill.warn{color:var(--warn);background:var(--warnSoft)}
.pill.neu{color:var(--neu);background:var(--line2)}

/* card / section */
.card{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:18px;box-shadow:var(--shadow)}
.sect-h{display:flex;align-items:baseline;justify-content:space-between;margin:26px 2px 12px;gap:10px;flex-wrap:wrap}
.sect-h h2{font-size:17px;font-weight:800;letter-spacing:-.02em;margin:0}
.sect-h .m{font-size:12px;color:var(--mut)}

/* chart */
.chart-head{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px}
.seg{display:inline-flex;background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:2px}
.seg button{border:0;background:transparent;color:var(--mut);font:inherit;font-weight:700;font-size:12.5px;
  padding:6px 11px;border-radius:8px;cursor:pointer;transition:.15s}
.seg button.on{background:var(--accent);color:#fff}
.clegend{display:flex;gap:14px;flex-wrap:wrap;margin:2px 2px 6px;min-height:0}
.clegend .lg{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:700;color:var(--mut)}
.clegend .sw{width:14px;height:3px;border-radius:2px}
#chart{width:100%;height:320px}
#chart .grid line{stroke:var(--line);stroke-dasharray:2 4}
#chart .axis text{fill:var(--faint);font-size:11px}
#chart .axis path,#chart .axis line{stroke:var(--line)}
.line-path{fill:none;stroke-width:2.4}
.area{opacity:.14}
.dot-last{filter:drop-shadow(0 0 4px currentColor)}
.ctip{position:fixed;pointer-events:none;background:var(--tx);color:var(--bg);font-size:12px;font-weight:600;
  padding:7px 10px;border-radius:9px;opacity:0;transition:opacity .12s;z-index:60;white-space:nowrap}

/* AI cards */
.ai{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
@media(max-width:720px){.ai{grid-template-columns:1fr}}
.aic{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:18px;box-shadow:var(--shadow)}
.aic .h{display:flex;align-items:center;gap:10px;margin-bottom:6px}
.aic .h .flag{font-size:20px}
.aic .h .nm{font-weight:800;font-size:15px}
.aic .h .vd{margin-left:auto}
.gaugewrap{display:flex;align-items:center;gap:16px;margin:6px 0 12px}
.gauge{width:132px;height:80px;flex:none}
.gscore{font-size:30px;font-weight:800;letter-spacing:-.02em;line-height:1}
.gsub{font-size:11.5px;color:var(--mut)}
.reasons{list-style:none;margin:6px 0 0;padding:0;display:flex;flex-direction:column;gap:6px}
.reasons li{position:relative;padding-left:18px;font-size:13px;color:var(--tx)}
.reasons li::before{content:"›";position:absolute;left:4px;top:0;color:var(--accent);font-weight:800}
.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:13px}
.mt{background:var(--panel2);border:1px solid var(--line2);border-radius:10px;padding:8px 9px}
.mt .k{font-size:10.5px;color:var(--mut)}
.mt .v{font-size:14px;font-weight:800;letter-spacing:-.01em}

/* table */
.tblscroll{overflow:auto;max-height:70vh;-webkit-overflow-scrolling:touch;border:1px solid var(--line);border-radius:14px}
table{width:100%;border-collapse:collapse;font-size:13px;background:var(--panel)}
th,td{padding:10px 12px;text-align:left;white-space:nowrap}
thead th{position:sticky;top:0;z-index:2;background:var(--panel2);color:var(--mut);font-weight:700;font-size:12px;box-shadow:inset 0 -1px 0 var(--line)}
tbody tr{border-bottom:1px solid var(--line2)}
tbody tr:last-child{border-bottom:none}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
td.nm{font-weight:700}
.up{color:var(--up);font-weight:700}.down{color:var(--down);font-weight:700}.neu{color:var(--neu)}
footer{margin-top:30px;color:var(--mut);font-size:12px;text-align:center;line-height:1.8}
.disc{margin-top:6px;color:var(--faint);font-size:11.5px}
.loading{padding:70px 0;text-align:center;color:var(--mut)}
.spin{width:26px;height:26px;border:3px solid var(--line);border-top-color:var(--accent);border-radius:50%;
  margin:0 auto 12px;animation:sp .8s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<div class="top"><div class="wrap">
  <div class="brand"><span class="dot"></span>💱 환율 브리핑</div>
  <div class="spacer"></div>
  <span class="live" id="live" hidden><span class="lvdot"></span>실시간</span>
  <span class="slotbadge" id="slotbadge">—</span>
  <span class="gen" id="gen"></span>
</div></div>

<div class="wrap">
  <div id="app"><div class="loading"><div class="spin"></div>환율 불러오는 중…</div></div>
</div>
<div class="ctip" id="ctip"></div>

<script>
const NF=(n,d=1)=>n==null?'-':(+n).toLocaleString('ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d});
const SGN=p=>p==null?'-':(p>0?'▲':(p<0?'▼':'–'))+Math.abs(p).toFixed(2)+'%';
const CLS=p=>p==null?'neu':(p>0?'up':(p<0?'down':'neu'));
const SIGCLS=v=>!v?'neu':(v.indexOf('적기')>=0?'good':(v.indexOf('관망')>=0?'warn':'neu'));
let DATA=null, SEL='USD', MODE='daily', SERIES='buy';
const SLABEL={base:'매매기준율',buy:'현찰 살 때',sell:'현찰 팔 때',all:'전체(중첩)'};
const SCOL={base:'var(--accent)',buy:'var(--up)',sell:'var(--good)'};

async function boot(){
  try{ DATA=await (await fetch('data/app.json',{cache:'no-store'})).json(); }
  catch(e){ document.getElementById('app').innerHTML='<div class="loading">데이터가 아직 없습니다.</div>'; return; }
  document.getElementById('live').hidden=false;
  document.getElementById('slotbadge').textContent=(DATA.slotKo||'')+' '+(DATA.slotLabel||'');
  document.getElementById('gen').textContent='최근 업데이트 '+(DATA.generated||'');
  SEL=(DATA.currencies[0]||{}).code||'USD';
  render();
  setInterval(refresh,60000);   // 장중 자동 갱신(사이트 데이터가 바뀌면 반영)
}
async function refresh(){
  try{
    const d=await (await fetch('data/app.json',{cache:'no-store'})).json();
    if(d && d.generated!==DATA.generated){
      DATA=d;
      document.getElementById('slotbadge').textContent=(DATA.slotKo||'')+' '+(DATA.slotLabel||'');
      document.getElementById('gen').textContent='최근 업데이트 '+(DATA.generated||'');
      render();
    }
  }catch(e){}
}

function render(){
  const cs=DATA.currencies, app=document.getElementById('app');
  app.innerHTML=`
  <div class="hero">
    <h1>오늘의 환율 · 원화 대비</h1>
    <div class="subline">${esc(DATA.source)} · 현찰 살 때/팔 때 기준 · ${DATA.date} ${DATA.slotLabel} 고시</div>
  </div>
  <div class="cards">${cs.map((c,i)=>ccard(c,i)).join('')}</div>

  <div class="sect-h"><h2>추세 그래프</h2><span class="m">전일 대비(일별) · 전시간 대비(시간별) · 살때/팔때/기준율 전환</span></div>
  <div class="card">
    <div class="chart-head">
      <div class="seg" id="cur-seg">${cs.map(c=>`<button data-c="${c.code}" class="${c.code===SEL?'on':''}">${c.flag} ${c.code}</button>`).join('')}</div>
      <div class="spacer" style="flex:1"></div>
      <div class="seg" id="mode-seg">
        <button data-m="daily" class="${MODE==='daily'?'on':''}">일별</button>
        <button data-m="intraday" class="${MODE==='intraday'?'on':''}">시간별</button>
      </div>
      <div class="seg" id="series-seg">
        <button data-s="base" class="${SERIES==='base'?'on':''}">기준율</button>
        <button data-s="buy" class="${SERIES==='buy'?'on':''}">살 때</button>
        <button data-s="sell" class="${SERIES==='sell'?'on':''}">팔 때</button>
        <button data-s="all" class="${SERIES==='all'?'on':''}">전체(중첩)</button>
      </div>
    </div>
    <div id="legend" class="clegend"></div>
    <svg id="chart"></svg>
  </div>

  <div class="sect-h"><h2>🤖 AI 매수 분석</h2><span class="m">규칙기반 신호 · 점수↑ = 지금 사기 상대적으로 저렴 · 투자참고용</span></div>
  <div class="ai">${cs.map(aicard).join('')}</div>

  <div class="sect-h"><h2>전체 요약</h2><span class="m">단위 원(KRW) · 전일/전시간 대비</span></div>
  <div class="tblscroll">
    <table><thead><tr>
      <th>통화</th><th class="num">현찰 살 때</th><th class="num">현찰 팔 때</th><th class="num">매매기준율</th>
      <th class="num">전일대비</th><th class="num">전시간대비</th><th class="num">AI점수</th><th>판정</th>
    </tr></thead><tbody>
    ${cs.map(c=>{const sg=c.signal||{};return `<tr>
      <td class="nm">${c.flag} ${esc(c.label)}</td>
      <td class="num">${NF(c.buy)}</td><td class="num">${NF(c.sell)}</td>
      <td class="num">${NF(c.base,2)}</td>
      <td class="num ${CLS(c.day.baseChgPct)}">${SGN(c.day.baseChgPct)}</td>
      <td class="num ${CLS(c.slot&&c.slot.baseChgPct)}">${c.slot?SGN(c.slot.baseChgPct):'—'}</td>
      <td class="num">${sg.score!=null?sg.score:'-'}</td>
      <td><span class="pill ${SIGCLS(sg.verdict)}">${esc(sg.short||'-')}</span></td>
    </tr>`;}).join('')}
    </tbody></table>
  </div>

  <footer>
    데이터 출처: <a href="https://finance.naver.com/marketindex/" target="_blank" rel="noopener">네이버 금융 시장지표 ↗</a> · 하나은행 고시 기준<br>
    평일 오전 9시 잔디 브리핑 · 사이트는 장중(9~16시) 수시 갱신 · 최근 ${esc(DATA.generated||'')}
    <div class="disc">※ 규칙기반 참고 지표이며 투자자문이 아닙니다. 실제 거래 환율은 은행·시점별로 다릅니다.</div>
  </footer>`;

  // 카드 애니메이션 stagger
  document.querySelectorAll('.cc').forEach((el,i)=>el.style.animationDelay=(i*70)+'ms');
  // 스파크라인
  cs.forEach(c=>drawSpark(c));
  // countUp 살때
  cs.forEach(c=>{const el=document.getElementById('buy-'+c.code); if(el)countUp(el,c.buy,1,'원');});
  // 게이지
  cs.forEach(c=>drawGauge(c));
  // 이벤트
  document.querySelectorAll('.cc').forEach(el=>el.onclick=()=>{SEL=el.dataset.c;syncSeg();drawChart();});
  wireSeg('cur-seg','c',v=>{SEL=v;});
  wireSeg('mode-seg','m',v=>{MODE=v;});
  wireSeg('series-seg','s',v=>{SERIES=v;redrawSparks();});
  drawChart();
}

function ccard(c,i){
  const d=c.day, sg=c.signal||{};
  const slot=c.slot?`<span class="dl ${CLS(c.slot.baseChgPct)}">${SGN(c.slot.baseChgPct)}<small>전시간</small></span>`:'';
  return `<div class="cc ${c.code===SEL?'sel':''}" data-c="${c.code}">
    <div class="top1"><span class="flag">${c.flag}</span><span class="lab">${esc(c.label)}</span><span class="unit">${esc(c.unit)}</span></div>
    <div class="cclab">현찰 살 때</div>
    <div class="buy tabnum" id="buy-${c.code}">${NF(c.buy)}<span class="w">원</span></div>
    <div class="rows"><span>팔 때 <b>${NF(c.sell)}</b></span><span>기준 <b>${NF(c.base,2)}</b></span></div>
    <div class="badges">
      <span class="dl ${CLS(d.baseChgPct)}">${SGN(d.baseChgPct)}<small>전일</small></span>${slot}
    </div>
    <svg class="spark" id="spark-${c.code}" preserveAspectRatio="none"></svg>
    <div class="sigline"><span class="pill ${SIGCLS(sg.verdict)}">${esc(sg.short||'-')}</span><span style="color:var(--mut)">AI ${sg.score!=null?sg.score:'-'}점</span></div>
  </div>`;
}

function aicard(c){
  const sg=c.signal; if(!sg)return `<div class="aic"><div class="h"><span class="flag">${c.flag}</span><span class="nm">${esc(c.label)}</span></div><p style="color:var(--mut)">데이터 부족</p></div>`;
  const m=sg.metrics;
  return `<div class="aic" data-c="${c.code}">
    <div class="h"><span class="flag">${c.flag}</span><span class="nm">${esc(c.label)} · ${esc(c.unit)}</span>
      <span class="vd"><span class="pill ${SIGCLS(sg.verdict)}">${esc(sg.verdict)}</span></span></div>
    <div class="gaugewrap">
      <svg class="gauge" id="gauge-${c.code}" viewBox="0 0 132 80"></svg>
      <div><div class="gscore" id="gscore-${c.code}" style="color:${gcolor(sg.score)}">0</div>
        <div class="gsub">매수 적합도 / 100</div></div>
    </div>
    <ul class="reasons">${sg.reasons.map(r=>`<li>${esc(r)}</li>`).join('')}</ul>
    <div class="metrics">
      <div class="mt"><div class="k">현재 기준율</div><div class="v tabnum">${NF(m.cur,2)}</div></div>
      <div class="mt"><div class="k">20일 평균</div><div class="v tabnum">${NF(m.sma20,2)}</div></div>
      <div class="mt"><div class="k">밴드 위치</div><div class="v tabnum">${m.pctile}%</div></div>
      <div class="mt"><div class="k">${m.window}일 최저</div><div class="v tabnum">${NF(m.lo,2)}</div></div>
      <div class="mt"><div class="k">${m.window}일 최고</div><div class="v tabnum">${NF(m.hi,2)}</div></div>
      <div class="mt"><div class="k">변동성/일</div><div class="v tabnum">${m.vol}%</div></div>
    </div>
  </div>`;
}

/* ---------- 스파크라인(카드 미니차트) — 선택 시리즈 반영 ---------- */
function sparkKey(){return SERIES==='all'?'base':SERIES;}
function redrawSparks(){(DATA.currencies||[]).forEach(drawSpark);}
function drawSpark(c){
  const el=document.getElementById('spark-'+c.code); if(!el)return;
  const key=sparkKey();
  const arr=(c.daily||[]).map(d=>d[key]).filter(v=>v!=null).slice(-30);
  if(arr.length<2){el.style.display='none';return;}
  const W=200,H=38,pad=3;
  const mn=Math.min(...arr),mx=Math.max(...arr),rg=(mx-mn)||1;
  const X=i=>pad+i*(W-2*pad)/(arr.length-1);
  const Y=v=>H-pad-(v-mn)/rg*(H-2*pad);
  const rising=arr[arr.length-1]>=arr[0];
  const col=rising?'var(--up)':'var(--down)';
  const dl=arr.map((v,i)=>(i?'L':'M')+X(i).toFixed(1)+' '+Y(v).toFixed(1)).join(' ');
  const ar=`M${X(0)} ${H} `+arr.map((v,i)=>'L'+X(i).toFixed(1)+' '+Y(v).toFixed(1)).join(' ')+` L${X(arr.length-1)} ${H} Z`;
  el.setAttribute('viewBox',`0 0 ${W} ${H}`);
  el.innerHTML=`<defs><linearGradient id="sg-${c.code}" x1="0" x2="0" y1="0" y2="1">
    <stop offset="0" stop-color="${col}" stop-opacity=".28"/><stop offset="1" stop-color="${col}" stop-opacity="0"/></linearGradient></defs>
    <path d="${ar}" fill="url(#sg-${c.code})"/>
    <path d="${dl}" fill="none" stroke="${col}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"
      class="draw" style="stroke-dasharray:600;stroke-dashoffset:600"/>
    <circle cx="${X(arr.length-1).toFixed(1)}" cy="${Y(arr[arr.length-1]).toFixed(1)}" r="2.4" fill="${col}"/>`;
  const p=el.querySelector('.draw');
  requestAnimationFrame(()=>{p.style.transition='stroke-dashoffset 1s ease';p.style.strokeDashoffset='0';});
}

/* ---------- 게이지(반원) ---------- */
function gcolor(s){return s>=66?'var(--good)':(s<=33?'var(--warn)':'var(--accent)');}
function drawGauge(c){
  const sg=c.signal; if(!sg)return;
  const el=document.getElementById('gauge-'+c.code); if(!el)return;
  const cx=66,cy=72,r=54;
  const arc=(a0,a1)=>{const p0=pol(cx,cy,r,a0),p1=pol(cx,cy,r,a1);
    const laf=(a1-a0)>Math.PI?1:0; return `M${p0.x} ${p0.y} A${r} ${r} 0 ${laf} 1 ${p1.x} ${p1.y}`;};
  const A0=Math.PI, A1=2*Math.PI; // 180°→360° (좌→우, 위쪽 반원)
  const val=A0+(A1-A0)*(sg.score/100);
  el.innerHTML=`
    <path d="${arc(A0,A1)}" fill="none" stroke="var(--line)" stroke-width="10" stroke-linecap="round"/>
    <path id="ga-${c.code}" d="${arc(A0,A1)}" fill="none" stroke="${gcolor(sg.score)}" stroke-width="10" stroke-linecap="round"
      style="stroke-dasharray:${Math.PI*r};stroke-dashoffset:${Math.PI*r}"/>`;
  const path=el.querySelector('#ga-'+c.code);
  const full=Math.PI*r, target=full*(1-sg.score/100);
  requestAnimationFrame(()=>{path.style.transition='stroke-dashoffset 1.1s cubic-bezier(.22,1,.36,1)';path.style.strokeDashoffset=target;});
  const sc=document.getElementById('gscore-'+c.code); if(sc)countUp(sc,sg.score,0,'');
}
function pol(cx,cy,r,a){return {x:cx+r*Math.cos(a),y:cy+r*Math.sin(a)};}

/* ---------- 메인 라인차트(d3) + 모션 ---------- */
function pointsOf(c){
  const src=MODE==='intraday'?(c.intraday||[]):(c.daily||[]);
  return src.map((d,i)=>({x:i,
    label:MODE==='intraday'?((d.date?d.date.slice(5)+' ':'')+(d.slotLabel||'')):d.date,
    base:d.base, buy:d.buy, sell:d.sell}));
}
function drawChart(){
  const c=DATA.currencies.find(x=>x.code===SEL); if(!c)return;
  const pts=pointsOf(c);
  const keys=SERIES==='all'?['base','buy','sell']:[SERIES];
  const svg=d3.select('#chart'); svg.selectAll('*').remove();
  const leg=document.getElementById('legend'); leg.innerHTML='';
  const box=document.getElementById('chart').getBoundingClientRect();
  const W=box.width||800,H=320,m={t:16,r:16,b:26,l:58};
  svg.attr('viewBox',`0 0 ${W} ${H}`);
  if(pts.length<2){svg.append('text').attr('x',W/2).attr('y',H/2).attr('text-anchor','middle').attr('fill','var(--mut)').text(MODE==='intraday'?'시간별 데이터가 아직 쌓이는 중입니다':'데이터 부족');return;}
  const x=d3.scalePoint().domain(pts.map(d=>d.x)).range([m.l,W-m.r]);
  let vals=[]; keys.forEach(k=>pts.forEach(p=>{if(p[k]!=null)vals.push(p[k]);}));
  const ext=d3.extent(vals),pad=(ext[1]-ext[0]||1)*0.12;
  const y=d3.scaleLinear().domain([ext[0]-pad,ext[1]+pad]).range([H-m.b,m.t]);
  // grid + y axis
  const yaxis=svg.append('g').attr('class','axis grid').attr('transform',`translate(${m.l},0)`)
    .call(d3.axisLeft(y).ticks(5).tickSize(-(W-m.l-m.r)).tickFormat(d=>d.toLocaleString('ko-KR')));
  yaxis.select('.domain').remove();
  // x axis
  const step=Math.ceil(pts.length/6);
  svg.append('g').attr('class','axis').attr('transform',`translate(0,${H-m.b})`)
    .call(d3.axisBottom(x).tickValues(pts.filter((d,i)=>i%step===0).map(d=>d.x)).tickFormat(v=>{const d=pts.find(z=>z.x===v);return d?d.label:'';}));
  const defs=svg.append('defs');
  const single=keys.length===1;
  keys.forEach((k,ki)=>{
    const data=pts.filter(p=>p[k]!=null).map(p=>({x:p.x,v:p[k]}));
    if(data.length<2)return;
    let col;
    if(single){const rising=data[data.length-1].v>=data[0].v; col=rising?'var(--up)':'var(--down)';}
    else col=SCOL[k];
    const line=d3.line().x(d=>x(d.x)).y(d=>y(d.v)).curve(d3.curveMonotoneX);
    if(single){
      const gid='grad-main';
      const g=defs.append('linearGradient').attr('id',gid).attr('x1',0).attr('x2',0).attr('y1',0).attr('y2',1);
      g.append('stop').attr('offset','0').attr('stop-color',col).attr('stop-opacity',.22);
      g.append('stop').attr('offset','1').attr('stop-color',col).attr('stop-opacity',0);
      const area=d3.area().x(d=>x(d.x)).y0(H-m.b).y1(d=>y(d.v)).curve(d3.curveMonotoneX);
      svg.append('path').datum(data).attr('class','area').attr('fill',`url(#${gid})`).attr('d',area);
    }
    const path=svg.append('path').datum(data).attr('class','line-path').attr('stroke',col).attr('d',line);
    const L=path.node().getTotalLength();
    path.attr('stroke-dasharray',L).attr('stroke-dashoffset',L)
      .transition().duration(950).delay(ki*160).ease(d3.easeCubicOut).attr('stroke-dashoffset',0);
    const last=data[data.length-1];
    svg.append('circle').attr('class','dot-last').attr('cx',x(last.x)).attr('cy',y(last.v)).attr('r',0)
      .attr('fill',col).attr('color',col).transition().delay(850+ki*160).duration(300).attr('r',4.5);
  });
  // legend (중첩 모드)
  if(!single){
    leg.innerHTML=keys.map(k=>`<span class="lg"><span class="sw" style="background:${SCOL[k]}"></span>${SLABEL[k]}</span>`).join('');
  }
  // hover (모든 시리즈 값 표시)
  const tip=document.getElementById('ctip');
  const guide=svg.append('line').attr('y1',m.t).attr('y2',H-m.b).attr('stroke','var(--line)').style('opacity',0);
  const foci=keys.map(k=>svg.append('circle').attr('r',3.5).attr('fill',SCOL[k]||'var(--accent)').style('opacity',0));
  svg.append('rect').attr('x',m.l).attr('y',m.t).attr('width',W-m.l-m.r).attr('height',H-m.t-m.b)
    .attr('fill','transparent')
    .on('mousemove',(ev)=>{const mx=d3.pointer(ev)[0];
      let best=pts[0],bd=1e9; pts.forEach(p=>{const dd=Math.abs(x(p.x)-mx);if(dd<bd){bd=dd;best=p;}});
      guide.attr('x1',x(best.x)).attr('x2',x(best.x)).style('opacity',1);
      let rows='';
      keys.forEach((k,i)=>{ if(best[k]==null){foci[i].style('opacity',0);return;}
        foci[i].attr('cx',x(best.x)).attr('cy',y(best[k])).style('opacity',1);
        rows+=`<div style="display:flex;gap:8px;justify-content:space-between"><span style="color:${SCOL[k]}">■</span><span>${SLABEL[k]}</span><b>${best[k].toLocaleString('ko-KR')}원</b></div>`;});
      tip.style.opacity=1;tip.style.left=(ev.clientX+14)+'px';tip.style.top=(ev.clientY-10)+'px';
      tip.innerHTML=`<div style="margin-bottom:3px"><b>${esc(best.label)}</b></div>${rows}`;})
    .on('mouseleave',()=>{guide.style('opacity',0);foci.forEach(f=>f.style('opacity',0));tip.style.opacity=0;});
}

/* ---------- 공통 ---------- */
function wireSeg(id,attr,setter){const g=document.getElementById(id);if(!g)return;
  g.querySelectorAll('button').forEach(b=>b.onclick=()=>{setter(b.dataset[attr]);
    g.querySelectorAll('button').forEach(x=>x.classList.remove('on'));b.classList.add('on');
    if(id==='cur-seg')syncSeg();drawChart();});}
function syncSeg(){document.querySelectorAll('#cur-seg button').forEach(b=>b.classList.toggle('on',b.dataset.c===SEL));
  document.querySelectorAll('.cc').forEach(el=>el.classList.toggle('sel',el.dataset.c===SEL));}
function countUp(el,target,dec,suf){target=+target||0;const dur=900,t0=performance.now();
  function fr(t){const k=Math.min(1,(t-t0)/dur);const e=1-Math.pow(1-k,3);const v=target*e;
    const txt=v.toLocaleString('ko-KR',{minimumFractionDigits:dec,maximumFractionDigits:dec});
    el.innerHTML=suf?(txt+'<span class="w">'+suf+'</span>'):txt;
    if(k<1)requestAnimationFrame(fr);}
  requestAnimationFrame(fr);}
function esc(s){return String(s==null?'':s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
window.addEventListener('resize',()=>{clearTimeout(window.__rz);window.__rz=setTimeout(drawChart,180);});
boot();
</script>
</body>
</html>
"""
