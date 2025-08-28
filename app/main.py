"""
    This is part of Astrologer API (C) 2023 Giacomo Battaglia
"""

import logging
import logging.config

from fastapi import FastAPI

from .routers import main_router
from .config.settings import settings
from .middleware.secret_key_checker_middleware import SecretKeyCheckerMiddleware


logging.config.dictConfig(settings.LOGGING_CONFIG)
app = FastAPI(
    debug=settings.debug,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    title="Astrologer API",
    version="4.0.0",
    summary="Astrology Made Easy",
    description="The Astrologer API is a RESTful service providing extensive astrology calculations, designed for seamless integration into projects. It offers a rich set of astrological charts and data, making it an invaluable tool for both developers and astrology enthusiasts.",
    contact={
        "name": "Kerykeion Astrology",
        "url": "https://www.kerykeion.net/",
        "email": settings.admin_email,
    },
    license_info={
        "name": "AGPL-3.0",
        "url": "https://www.gnu.org/licenses/agpl-3.0.html",
    },
)

# ——— pega esto en app/main.py ———
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

# Permitir que tu web incruste y llame a este servidor
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # si quieres, luego lo limito a tu dominio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WIDGET_HTML = r'''<!doctype html>
<html lang="es"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Tu carta natal</title>
<style>
  :root{ --ink:#111; --line:#000; }
  *{box-sizing:border-box}
  body{font-family:system-ui,Arial,sans-serif;color:var(--ink);background:#fff;margin:0}
  .box{max-width:1060px;margin:0 auto;padding:30px 28px}
  h1,h2,h3{margin:0 0 12px}
  h1{font-size:28px}
  h2{font-size:22px}
  h3{font-size:18px}
  label{display:block;font-size:14px;margin:10px 0 6px}
  input,select,button{
    width:100%;padding:12px 12px;border:1px solid var(--line);
    background:#fff;color:#000;border-radius:12px;line-height:1.2
  }
  button{cursor:pointer;font-weight:800}
  .row{display:grid;grid-template-columns:1fr 1fr;gap:38px;align-items:start}
  .mt{margin-top:16px}
  .btns{display:flex;gap:12px;flex-wrap:wrap;align-items:center}
  .alert{border:1px solid var(--line);background:#fff;color:#000;border-radius:12px;padding:12px;margin:12px 0;display:none;white-space:pre-wrap}
  .ok{border:1px solid var(--line);padding:24px;border-radius:12px;margin-top:18px}
  .ok > * + *{margin-top:18px}
  table{width:100%;border-collapse:collapse;margin-top:12px;table-layout:fixed}
  thead th{background:#f7f7f7}
  th,td{border:1px solid var(--line);padding:9px 10px;text-align:left;font-size:14px;word-break:break-word;vertical-align:top}
  .svgwrap{border:1px solid var(--line);border-radius:12px;overflow:hidden;padding:10px;background:#fff}
  #svg svg{max-width:100%;height:auto;display:block}
  #diag{display:none !important;} /* ocultar diagnóstico en pantalla y pdf */
  .report-header{display:flex;gap:14px;align-items:center;margin-bottom:4px}
  .report-header img{height:40px;width:auto}
  .report-footer{margin-top:16px;font-size:12px;border-top:1px solid #000;padding-top:8px;display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}
  .pill{display:inline-block;border:1px solid #000;border-radius:999px;padding:2px 8px;font-size:12px}
  .grid-2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  @media (max-width:820px){ .row{grid-template-columns:1fr} .grid-2{grid-template-columns:1fr} }
  /* Impresión/PDF */
  @media print{
    body{background:#fff;color:#000}
    .alert, .btns{display:none !important}
    .box{padding:0}
    .ok{border:none;padding:0}
    thead th{background:#eee}
  }
</style>
</head><body>
<div class="box">
  <div class="report-header">
    <img id="logo" src="https://astrologiamutante.com/wp-content/uploads/2025/08/ufff.svg" alt="Astrología Mutante">
    <h1 id="titulo">Tu carta natal</h1>
  </div>

  <div class="alert" id="alert"></div>

  <div class="row">
    <div>
      <label>Nombre</label>
      <input id="inp-name" placeholder="Nombre de la persona">
    </div>
    <div>
      <label>Sistema de casas</label>
      <select id="inp-house">
        <option value="P" selected>Placidus (P)</option>
        <option value="W">Whole Sign (W)</option>
        <option value="O">Porphyry (O)</option>
        <option value="K">Koch (K)</option>
        <option value="R">Regiomontanus (R)</option>
        <option value="M">Morinus (M)</option>
        <option value="A">Equal (A)</option>
      </select>
    </div>
  </div>

  <div class="row">
    <div>
      <label>Fecha de nacimiento</label>
      <input id="inp-date" type="date" required>
    </div>
    <div>
      <label>Hora de nacimiento</label>
      <input id="inp-time" type="time" required>
    </div>
  </div>

  <div class="row">
    <div>
      <label>Ciudad</label>
      <input id="inp-city" placeholder="Bogotá">
    </div>
    <div>
      <label>País</label>
      <input id="inp-country" placeholder="Colombia">
    </div>
  </div>

  <div class="mt btns">
    <button id="btn-gen">Generar carta</button>
    <button id="btn-pdf" disabled>Descargar PDF</button>
    <span class="pill">tiktok: @astrologia_mutante</span>
    <span class="pill">instagram: @astrologia_mutante</span>
  </div>

  <div id="resultado" class="ok" style="display:none">
    <!-- Se exporta a PDF todo lo que hay dentro de #resultado -->
    <div id="svg" class="svgwrap"></div>

    <div class="grid-2">
      <div id="pos-table"></div>
      <div id="elemmod"></div>
    </div>

    <div id="tablas"></div>

    <details id="diag">
      <summary><b>Diagnóstico</b></summary>
      <div id="diag-content"></div>
    </details>

    <div class="report-footer">
      <div><strong>Astrología Mutante</strong></div>
      <div>tiktok: @astrologia_mutante · instagram: @astrologia_mutante</div>
    </div>
  </div>
</div>

<!-- Librería PDF -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js" referrerpolicy="no-referrer"></script>

<script>
(function(){
  // ===== Parámetros por URL =====
  const q       = new URLSearchParams(location.search);
  const LANG    = q.get('lang')    || 'ES';
  const THEME   = q.get('theme')   || 'light';
  const GEOUSER = q.get('geouser') || 'mofeto';
  const TITLE   = q.get('title')   || 'Tu carta natal';
  const APIBASE = (q.get('api') || '') || '/api/v4';
  document.getElementById('titulo').textContent = decodeURIComponent(TITLE||'');

  // ===== Helpers =====
  const $ = id => document.getElementById(id);
  const $alert=$('alert'), $out=$('resultado'), $svg=$('svg'), $tabs=$('tablas'), $pos=$('pos-table'), $em=$('elemmod');
  const $btnGen=$('btn-gen'), $btnPDF=$('btn-pdf'), $diagC=$('diag-content');
  const showAlert = t => { $alert.style.display='block'; $alert.textContent=t; };
  const hideAlert = ()=>{ $alert.style.display='none'; $alert.textContent=''; };
  const esc = s => String(s).replace(/[&<>"']/g,m=>({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[m]));
  const log = (title,obj)=>{ if(!$diagC) return; $diagC.innerHTML += `<p><b>${title}</b></p><pre>${esc(JSON.stringify(obj,null,2))}</pre>`; };

  // ===== Utilidades numéricas/astro =====
  const norm = s => (s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
  const ISO2 = {"colombia":"CO","argentina":"AR","chile":"CL","peru":"PE","ecuador":"EC","venezuela":"VE","uruguay":"UY","paraguay":"PY","bolivia":"BO","mexico":"MX","méxico":"MX","españa":"ES","espana":"ES","spain":"ES","portugal":"PT","francia":"FR","france":"FR","italia":"IT","italy":"IT","alemania":"DE","germany":"DE","reino unido":"GB","uk":"GB","inglaterra":"GB","united kingdom":"GB","estados unidos":"US","eeuu":"US","usa":"US","united states":"US","brasil":"BR","brazil":"BR","canadá":"CA","canada":"CA"};
  const splitDate = d => { const [y,m,day]=(d||'').split('-').map(n=>parseInt(n,10)); return {year:y,month:m,day}; };
  const splitTime = t => { const [h,mi]=(t||'00:00').split(':').map(n=>parseInt(n,10)); return {hour:h,minute:mi}; };
  const clamp360 = x => ((x%360)+360)%360;
  const minSepDeg = (a,b) => Math.abs(((a - b + 540) % 360) - 180);
  const fmtDegMin = x => { const d=Math.floor(x), m=Math.round((x-d)*60); const dd=(m===60)?d+1:d; const mm=(m===60)?0:m; return `${dd}°${String(mm).padStart(2,"0")}'`; };
  function parseAngleAny(v){
    if(v==null) return null;
    if(typeof v==='number' && Number.isFinite(v)) return v;
    const s=String(v).trim(); if(!s) return null;
    const m=s.match(/(-?\d+(?:\.\d+)?)\s*°?\s*(\d+(?:\.\d+)?)?['’m]?\s*(\d+(?:\.\d+)?)?["”s]?/i);
    if(m){ return parseFloat(m[1]||'0') + (parseFloat(m[2]||'0')/60) + (parseFloat(m[3]||'0')/3600); }
    const n=parseFloat(s.replace(',','.')); return Number.isFinite(n)?n:null;
  }
  function signNameFromLon(lon){
    const i=Math.floor(clamp360(lon)/30);
    return ["Aries","Tauro","G\u00e9minis","C\u00e1ncer","Leo","Virgo","Libra","Escorpio","Sagitario","Capricornio","Acuario","Piscis"][i]||"";
  }
  function degInSign(lon){
    const d=clamp360(lon); const g=Math.floor(d%30); const m=Math.round((d%30-g)*60);
    return `${g}°${String(m).padStart(2,'0')}'`;
  }

  // Elementos y cualidades por signo
  const SIGN_TO_ELEMENT = ["Fuego","Tierra","Aire","Agua","Fuego","Tierra","Aire","Agua","Fuego","Tierra","Aire","Agua"];
  const SIGN_TO_MODALITY = ["Cardinal","Fijo","Mutable","Cardinal","Fijo","Mutable","Cardinal","Fijo","Mutable","Cardinal","Fijo","Mutable"];

  // ===== API =====
  async function call(path, payload, expectSVG=false){
    const r = await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(!r.ok){ const txt=await r.text().catch(()=> ""); throw new Error(`HTTP ${r.status}: ${txt}`); }
    const ct=r.headers.get('content-type')||'';
    if(expectSVG){
      const t=await r.text();
      if(t.trim().startsWith('{')){ try{ const j=JSON.parse(t); return j.svg||j.chart||''; }catch{} }
      return t;
    }
    if(ct.includes('application/json')) return r.json();
    return r.text();
  }
  async function callWithFallbacks(endpoint, basePayload, expectSVG=false){
    const variants = [
      p=>p,
      p=>{ const c=clone(p); if(c.active_points) c.active_points=c.active_points.filter(x=>x!=="Mean_South_Node"); return c; },
      p=>{ const c=clone(p); if(c.active_points) c.active_points=c.active_points.filter(x=>!["Chiron","Mean_Lilith"].includes(x)); return c; },
      p=>{ const c=clone(p); delete c.active_points; return c; },
      p=>{ const c=clone(p); if(c.subject){ const s=clone(c.subject); delete s.house_system; c.subject=s; } return c; },
      p=>{ const c=clone(p); if(c.subject){ const s=clone(c.subject); delete s.geonames_username; c.subject=s; } return c; },
    ];
    let lastErr=null;
    for(const v of variants){
      const payload=v(clone(basePayload));
      try{
        const res=await call(endpoint,payload,expectSVG);
        if(typeof res==='object' && res && (res.status==='KO'||res.error)) throw new Error(JSON.stringify(res));
        return res;
      }catch(e){
        lastErr=e;
        if(!String(e).includes('HTTP 500') && !String(e).includes('HTTP 422')) throw e;
      }
    }
    throw lastErr || new Error('No se pudo recuperar tras varios intentos.');
  }
  const clone = obj => JSON.parse(JSON.stringify(obj));

  // ===== Aspectos y puntos =====
  function sinAcentos(s){ return (s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,""); }
  function aspectKey(raw){
    const t = (raw||"").toString();
    const lower = sinAcentos(t).toLowerCase().replace(/[\s-]+/g,"_");
    const map = {
      conjuncion:"conjunction", conj:"conjunction",
      oposicion:"opposition", opp:"opposition",
      cuadratura:"square", quartile:"square",
      trigono:"trine", tri:"trine",
      sextil:"sextile", sex:"sextile",
      quincuncio:"quincunx", inconjuncto:"quincunx", inconjunct:"quincunx",
      semicuadratura:"semisquare", semi_cuadratura:"semisquare", semisquare:"semisquare",
      sesquicuadratura:"sesquiquadrate", sesqui_cuadratura:"sesquiquadrate",
      semisextil:"semisextile", semi_sextil:"semisextile", semisextile:"semisextile",
      quintil:"quintile", biquintil:"biquintile",
      novil:"novile", binovil:"binovile",
      septil:"septile", biseptil:"biseptile", triseptil:"triseptile",
      undecil:"undecile"
    };
    return map[lower] || lower;
  }
  const ASPECT_ANGLE = {
    conjunction:0, opposition:180, square:90, trine:120, sextile:60,
    quincunx:150, inconjunct:150,
    semisextile:30, semisquare:45, sesquiquadrate:135,
    quintile:72, biquintile:144, novile:40, binovile:80,
    septile:51.4286, biseptile:102.8571, triseptile:154.2857, undecile:32.7273
  };
  const ASPECTO_ES = {
    conjunction:"Conjunción", opposition:"Oposición", square:"Cuadratura", trine:"Trígono", sextile:"Sextil",
    quincunx:"Quincuncio", semisextile:"Semisextil", semisquare:"Semicuadratura", sesquiquadrate:"Sesquicuadratura",
    quintile:"Quintil", biquintile:"Biquintil", novile:"Novil", binovile:"Binovil",
    septile:"Septil", biseptile:"Biseptil", triseptile:"Triseptil", undecile:"Undécil"
  };

  const ORDER = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto","Ascendant","Medium_Coeli","Mean_Node","Mean_South_Node","Chiron","Mean_Lilith"];
  const POINT_ES = {
    "Sun":"Sol","Moon":"Luna","Mercury":"Mercurio","Venus":"Venus","Mars":"Marte","Jupiter":"Júpiter","Saturn":"Saturno",
    "Uranus":"Urano","Neptune":"Neptuno","Pluto":"Plutón",
    "Ascendant":"Ascendente","Descendant":"Descendente",
    "Medium_Coeli":"Medio Cielo","Imum_Coeli":"Fondo del Cielo",
    "Mean_Node":"Nodo Norte","Mean_South_Node":"Nodo Sur",
    "Chiron":"Quirón","Mean_Lilith":"Lilith (media)"
  };

  // Resolver nombre canónico
  const ALIAS2CAN = (()=> {
    const out = {
      "sun":"Sun","moon":"Moon","mercury":"Mercury","venus":"Venus","mars":"Mars","jupiter":"Jupiter","saturn":"Saturn",
      "uranus":"Uranus","neptune":"Neptune","pluto":"Pluto",
      "ascendant":"Ascendant","descendant":"Descendant",
      "mc":"Medium_Coeli","medium_coeli":"Medium_Coeli","midheaven":"Medium_Coeli",
      "ic":"Imum_Coeli","imum_coeli":"Imum_Coeli",
      "mean_node":"Mean_Node","true_node":"True_Node","mean_south_node":"Mean_South_Node",
      "chiron":"Chiron","mean_lilith":"Mean_Lilith","black_moon_lilith":"Mean_Lilith",
      "asc":"Ascendant","ac":"Ascendant","as":"Ascendant","dsc":"Descendant","dc":"Descendant",
      "sol":"Sun","luna":"Moon","mercurio":"Mercury","venus":"Venus","marte":"Mars","j\u00fapiter":"Jupiter","jupiter":"Jupiter",
      "saturno":"Saturn","urano":"Uranus","neptuno":"Neptune","pluton":"Pluto","plut\u00f3n":"Pluto",
      "ascendente":"Ascendant","descendente":"Descendant",
      "medio_cielo":"Medium_Coeli","fondo_del_cielo":"Imum_Coeli",
      "nodo_norte":"Mean_Node","nodo_sur":"Mean_South_Node",
      "quiron":"Chiron","quir\u00f3n":"Chiron",
      "lilith":"Mean_Lilith","lilith_media":"Mean_Lilith","luna_negra":"Mean_Lilith",
      "nodo_norte_medio":"Mean_Node","nodo_sur_medio":"Mean_South_Node"
    };
    const exp={}; for(const [k,v] of Object.entries(out)){ exp[k]=v; exp[k.replace(/\s+/g,'_')]=v; exp[k.replace(/[\s\-()]+/g,'_')]=v; }
    return exp;
  })();
  function resolveCanonName(raw){
    if(!raw) return null;
    const s=String(raw).trim();
    if(/^\d+$/.test(s)){ const n=parseInt(s,10); if(n>=0&&n<ORDER.length) return ORDER[n]; if(n>=1&&n<=ORDER.length) return ORDER[n-1]; }
    const k=s.toLowerCase(), nrm=norm(s), u=nrm.replace(/[\s\-()]+/g,'_');
    return ALIAS2CAN[k] || ALIAS2CAN[nrm] || ALIAS2CAN[u] || (ORDER.includes(s)?s:null);
  }
  function toCanon(x){ return resolveCanonName(x) || String(x); }

  // Longitudes desde el aspecto (p1_abs_pos / p2_abs_pos → CLAVE)
  function lonFromAspect(a, idx){
    const pref = idx===1 ? 'p1' : 'p2';
    const candidates = [
      a[`${pref}_abs_pos`], a[`${pref}_abs_long`], a[`${pref}_abs_longitude`],
      a[`${pref}_longitude`], a[`${pref}_lon`], a[`${pref}_long`],
      a[`${pref}Lon`], a[`${pref}Longitude`],
    ];
    for(const v of candidates){
      const num = parseAngleAny(v);
      if(Number.isFinite(num)) return num;
    }
    const nested = a[pref] || a[idx===1?'first':'second'] || a[idx===1?'from':'to'] || a[idx===1?'object1':'object2'] || a[idx===1?'point1':'point2'];
    if(nested){
      const v = parseAngleAny(nested.lon||nested.longitude||nested.abs_pos||nested.value||nested.position||nested.ecliptic?.lon||nested.ecliptic?.longitude);
      if(Number.isFinite(v)) return v;
    }
    return null;
  }

  // ====== PDF ======
  async function descargarPDF(){
    try{
      const el = document.getElementById('resultado');
      if(!window.html2pdf){ window.print(); return; }
      const nombre = (document.getElementById('inp-name').value || 'Carta-natal').trim().replace(/\s+/g,'_');
      const fecha = (document.getElementById('inp-date').value || '').replace(/-/g,'');
      const file = `Carta-natal_${nombre || 'Consulta'}_${fecha || ''}.pdf`;
      await html2pdf().set({
        margin:       [10,10,10,10],
        filename:     file,
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, useCORS: true, logging: false },
        jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
      }).from(el).save();
    }catch(e){
      alert('No se pudo crear el PDF. Como alternativa usa Imprimir → Guardar como PDF.');
    }
  }

  // ====== Generar ======
  async function generar(){
    try{
      hideAlert(); $out.style.display='none'; $svg.innerHTML=""; $tabs.innerHTML=""; $pos.innerHTML=""; $em.innerHTML="";
      $btnGen.disabled=true; $btnGen.textContent="Calculando…"; $btnPDF.disabled=true;

      const name=$('inp-name').value.trim()||"Consulta";
      const city=$('inp-city').value.trim();
      const country=$('inp-country').value.trim();
      const {year,month,day}=splitDate($('inp-date').value);
      const {hour,minute}=splitTime($('inp-time').value);
      const house=$('inp-house').value||'P';
      const zodiac='Tropic';
      if(!year||!month||!day){ showAlert('Falta la fecha.'); return; }
      if(!city||!country){ showAlert('Escribe ciudad y país.'); return; }
      const code = {"colombia":"CO","argentina":"AR","chile":"CL","peru":"PE","ecuador":"EC","venezuela":"VE","uruguay":"UY","paraguay":"PY","bolivia":"BO","mexico":"MX","méxico":"MX","españa":"ES","espana":"ES","spain":"ES","portugal":"PT","francia":"FR","france":"FR","italia":"IT","italy":"IT","alemania":"DE","germany":"DE","reino unido":"GB","uk":"GB","inglaterra":"GB","united kingdom":"GB","estados unidos":"US","eeuu":"US","usa":"US","united states":"US","brasil":"BR","brazil":"BR","canadá":"CA","canada":"CA"}[norm(country)];

      const subject={year,month,day,hour,minute,city,name,zodiac_type:zodiac,house_system:house,geonames_username:GEOUSER};
      if(code) subject.nation=code;
      const active_points=["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto","Ascendant","Medium_Coeli","Mean_Node","Mean_South_Node","Chiron","Mean_Lilith"];

      // 1) SVG
      const svg = await callWithFallbacks(APIBASE+'/birth-chart',{ subject, language:LANG, theme:THEME, style:THEME, chart_theme:THEME, active_points }, true);
      if(svg && svg.includes('<svg')) $svg.innerHTML = svg;

      // 2) DATOS (aspectos); de aquí sacamos longitudes planetarias (p1_abs_pos / p2_abs_pos)
      const data = await callWithFallbacks(APIBASE+'/natal-aspects-data',{ subject, language:LANG, active_points }, false);
      const aspects = (data && (data.aspects||data.natal_aspects)) ? (data.aspects||data.natal_aspects) : [];

      // 3) Intentar obtener cúspides de casas y posiciones si existen en data
      const housesCandidates = [
        data?.houses, data?.house_cusps, data?.data?.houses, data?.data?.house_cusps,
        data?.data?.chart?.houses, data?.data?.chart?.house_cusps
      ].filter(x=>Array.isArray(x) && x.length);
      const houses = housesCandidates[0] || [];
      const cusps = [];
      for(let i=1;i<=12;i++){
        const hObj = houses.find(h => (h.number ?? h.house) == i) || houses[i-1];
        const lon = hObj ? (hObj.longitude ?? hObj.lon ?? hObj.abs_pos ?? hObj?.ecliptic?.lon ?? hObj?.ecliptic?.longitude) : null;
        const val = parseAngleAny(lon);
        cusps[i] = Number.isFinite(val)? val : null;
      }
      function houseOf(lon){
        if(cusps.filter(x=>Number.isFinite(x)).length < 12) return "—";
        for(let i=1;i<=12;i++){
          const start = cusps[i], end = cusps[i%12+1];
          const dx = (clamp360(lon) - clamp360(start) + 360) % 360;
          const arc = (clamp360(end) - clamp360(start) + 360) % 360;
          if(dx >= 0 && dx < arc) return i;
        }
        return 12;
      }

      // 4) Construir mapa de longitudes por planeta usando los aspectos
      const PLANETS = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"];
      const lonByPlanet = {};
      aspects.forEach(a=>{
        const n1 = toCanon(a.p1_name ?? a.point_1 ?? a.point1 ?? a.a ?? a.p1 ?? a.obj1 ?? a.object1 ?? a.planet1 ?? a.c1 ?? a.first ?? a["1"] ?? a.from ?? a.name1);
        const n2 = toCanon(a.p2_name ?? a.point_2 ?? a.point2 ?? a.b ?? a.p2 ?? a.obj2 ?? a.object2 ?? a.planet2 ?? a.c2 ?? a.second ?? a["2"] ?? a.to   ?? a.name2);
        const l1 = lonFromAspect(a,1);
        const l2 = lonFromAspect(a,2);
        if(PLANETS.includes(n1) && Number.isFinite(l1) && !(n1 in lonByPlanet)) lonByPlanet[n1]=l1;
        if(PLANETS.includes(n2) && Number.isFinite(l2) && !(n2 in lonByPlanet)) lonByPlanet[n2]=l2;
      });

      // 5) Tabla de POSICIONES (signo, grado, casa)
      const rowsPos = PLANETS.map(p=>{
        const lon = lonByPlanet[p];
        const signo = Number.isFinite(lon)? signNameFromLon(lon) : "—";
        const grados = Number.isFinite(lon)? degInSign(lon) : "—";
        const casa = Number.isFinite(lon)? houseOf(lon) : "—";
        const nombre = {"Sun":"Sol","Moon":"Luna","Mercury":"Mercurio","Venus":"Venus","Mars":"Marte","Jupiter":"Júpiter","Saturn":"Saturno","Uranus":"Urano","Neptune":"Neptuno","Pluto":"Plutón"}[p];
        return [nombre, signo, grados, casa];
      });
      const headPos = "<thead><tr><th>Planeta</th><th>Signo</th><th>Grados</th><th>Casa</th></tr></thead>";
      const bodyPos = "<tbody>"+rowsPos.map(r=>"<tr>"+r.map(c=>`<td>${c}</td>`).join("")+"</tr>").join("")+"</tbody>";
      $pos.innerHTML = `<h3>Posiciones planetarias</h3><table>${headPos}${bodyPos}</table>`;

      // 6) Elementos y Cualidades (porcentajes)
      const countElem = {Fuego:0,Tierra:0,Aire:0,Agua:0};
      const countMod  = {Cardinal:0,Fijo:0,Mutable:0};
      let counted=0;
      PLANETS.forEach(p=>{
        const lon=lonByPlanet[p];
        if(Number.isFinite(lon)){
          const si = Math.floor(clamp360(lon)/30);
          countElem[SIGN_TO_ELEMENT[si]]++;
          countMod[SIGN_TO_MODALITY[si]]++;
          counted++;
        }
      });
      function pct(n){ return counted? Math.round(n*100/counted) : 0; }
      const elemRows = Object.keys(countElem).map(k=>`<tr><td>${k}</td><td>${pct(countElem[k])}%</td></tr>`).join("");
      const modRows  = Object.keys(countMod ).map(k=>`<tr><td>${k}</td><td>${pct(countMod[k ])}%</td></tr>`).join("");
      $em.innerHTML =
        `<h3>Distribución de elementos y cualidades</h3>
         <div class="grid-2">
           <div><table><thead><tr><th>Elemento</th><th>%</th></tr></thead><tbody>${elemRows}</tbody></table></div>
           <div><table><thead><tr><th>Cualidad</th><th>%</th></tr></thead><tbody>${modRows}</tbody></table></div>
         </div>`;

      // 7) Aspectos con ORBE (lo que ya tienes)
      const rowsA = aspects.map(a=>{
        const key  = aspectKey(a.type || a.aspect || a.kind || "");
        const label= ASPECTO_ES[key] || (a.type||a.aspect||a.kind||"");
        const target = ASPECT_ANGLE[key];

        const canon1 = toCanon(a.p1_name ?? a.point_1 ?? a.point1 ?? a.a ?? a.p1 ?? a.obj1 ?? a.object1 ?? a.planet1 ?? a.c1 ?? a.first ?? a["1"] ?? a.from ?? a.name1);
        const canon2 = toCanon(a.p2_name ?? a.point_2 ?? a.point2 ?? a.b ?? a.p2 ?? a.obj2 ?? a.object2 ?? a.planet2 ?? a.c2 ?? a.second ?? a["2"] ?? a.to   ?? a.name2);
        if(canon1==="True_Node" || canon2==="True_Node") return null;

        const disp1 = {"Sun":"Sol","Moon":"Luna","Mercury":"Mercurio","Venus":"Venus","Mars":"Marte","Jupiter":"Júpiter","Saturn":"Saturno","Uranus":"Urano","Neptune":"Neptuno","Pluto":"Plutón","Ascendant":"Ascendente","Medium_Coeli":"Medio Cielo","Mean_Node":"Nodo Norte","Mean_South_Node":"Nodo Sur","Chiron":"Quirón","Mean_Lilith":"Lilith (media)"}[canon1] || String(canon1).replace(/_/g,' ');
        const disp2 = {"Sun":"Sol","Moon":"Luna","Mercury":"Mercurio","Venus":"Venus","Mars":"Marte","Jupiter":"Júpiter","Saturn":"Saturno","Uranus":"Urano","Neptune":"Neptuno","Pluto":"Plutón","Ascendant":"Ascendente","Medium_Coeli":"Medio Cielo","Mean_Node":"Nodo Norte","Mean_South_Node":"Nodo Sur","Chiron":"Quirón","Mean_Lilith":"Lilith (media)"}[canon2] || String(canon2).replace(/_/g,' ');

        let l1 = lonFromAspect(a,1), l2 = lonFromAspect(a,2);
        let sep = parseAngleAny(a.separation ?? a.sep ?? a.sep_deg ?? a.angle ?? a.angle_deg ?? a.aspect_angle);
        if(!Number.isFinite(sep) && Number.isFinite(l1) && Number.isFinite(l2)) sep = minSepDeg(l1,l2);
        let orb = (Number.isFinite(sep) && Number.isFinite(target)) ? Math.abs(sep - target) : null;
        if(!Number.isFinite(orb)){
          const backendOrb = parseAngleAny(a.orbit ?? a.diff ?? a.difference ?? a.delta ?? a.error ?? a.deg_diff ?? a.exactness);
          if(Number.isFinite(backendOrb)) orb = backendOrb;
        }
        const orbStr = Number.isFinite(orb) ? fmtDegMin(orb) : "—";
        return [label || "—", disp1 || "—", disp2 || "—", orbStr];
      }).filter(Boolean);
      const headA = "<thead><tr><th>Aspecto</th><th>Cuerpo 1</th><th>Cuerpo 2</th><th>Orbe</th></tr></thead>";
      const bodyA = "<tbody>"+rowsA.map(r=>"<tr>"+r.map(c=>`<td>${(c??"")||"—"}</td>`).join("")+"</tr>").join("")+"</tbody>";
      $tabs.innerHTML = `<h3>Aspectos</h3><table>${headA}${bodyA}</table>`;

      // Mostrar y habilitar PDF
      $out.style.display='block';
      $btnPDF.disabled=false;

    }catch(e){
      showAlert("Error: "+(e?.message||e));
    }finally{
      $btnGen.disabled=false; $btnGen.textContent="Generar carta";
    }
  }

  // Eventos
  document.getElementById('btn-gen').addEventListener('click', e=>{ e.preventDefault(); generar(); });
  document.getElementById('btn-pdf').addEventListener('click', e=>{ e.preventDefault(); descargarPDF(); });

})();
</script>
</body></html>
'''









@app.get("/widget", response_class=HTMLResponse)
def widget():
    return WIDGET_HTML
# ——— fin del bloque ———


#------------------------------------------------------------------------------
# Routers 
#------------------------------------------------------------------------------

app.include_router(main_router.router, tags=["Endpoints"])

#------------------------------------------------------------------------------
# Middleware 
#------------------------------------------------------------------------------

if settings.debug is True:
    pass

else:
    app.add_middleware(
        SecretKeyCheckerMiddleware,
        secret_key_name=settings.secret_key_name,
        secret_keys=[
            settings.rapid_api_secret_key,
        ],
    )
