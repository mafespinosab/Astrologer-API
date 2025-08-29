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
  .box{max-width:820px;margin:0 auto;padding:24px 20px}
  h1,h2,h3{margin:0 0 12px}
  h1{font-size:26px}
  h2{font-size:20px}
  h3{font-size:17px}
  label{display:block;font-size:14px;margin:10px 0 6px}
  input,select,button{
    width:100%;padding:12px;border:1px solid var(--line);
    background:#fff;color:#000;border-radius:10px;line-height:1.2
  }
  button{cursor:pointer;font-weight:800}
  .row{display:grid;grid-template-columns:1fr 1fr;gap:24px;align-items:start}
  .mt{margin-top:16px}
  .btns{display:flex;gap:12px;flex-wrap:wrap;align-items:center}
  .alert{border:1px solid var(--line);background:#fff;color:#000;border-radius:10px;padding:10px;margin:12px 0;display:none;white-space:pre-wrap}
  .ok{border:1px solid var(--line);padding:18px;border-radius:10px;margin-top:18px}
  .ok > * + *{margin-top:14px}

  table{width:100%;border-collapse:collapse;margin-top:10px;table-layout:fixed}
  thead th{background:#f7f7f7}
  th,td{border:1px solid var(--line);padding:8px 9px;text-align:left;font-size:14px;word-break:break-word;vertical-align:top}
  tr{break-inside:avoid; page-break-inside:avoid}

  .svgwrap{border:1px solid var(--line);border-radius:10px;overflow:hidden;padding:8px;background:#fff}
  #svg svg{max-width:100%;height:auto;display:block}

  .pb{page-break-before:always; break-before:page; height:0; visibility:hidden}
  .pdf-only{display:none}
  #diag{display:none !important;}
  .grid-2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
  @media (max-width:820px){ .row{grid-template-columns:1fr} .grid-2{grid-template-columns:1fr} }
</style>
</head><body>
<div class="box">
  <h1 id="titulo">Tu carta natal</h1>

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
  </div>

  <div id="resultado" class="ok" style="display:none">
    <div id="svg" class="svgwrap"></div>
    <div id="pb1" class="pb"></div>

    <div class="grid-2">
      <div id="pos-table"></div>
      <div id="elemmod"></div>
    </div>

    <div id="tablas"></div>

    <div class="pdf-only" id="pdf-footer" style="margin-top:12px;border-top:1px solid #000;padding-top:8px;font-size:12px;">
      <div><strong>www.astrologiamutante.com</strong></div>
      <div>tiktok: @astrologia_mutante · instagram: @astrologia_mutante</div>
    </div>

    <details id="diag">
      <summary><b>Diagnóstico</b></summary>
      <div id="diag-content"></div>
    </details>
  </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js" referrerpolicy="no-referrer"></script>

<script>
(function(){
  // ===== Parámetros =====
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

  // ===== Utilidades astro =====
  const norm = s => (s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
  const ISO2 = {"colombia":"CO","argentina":"AR","chile":"CL","peru":"PE","ecuador":"EC","venezuela":"VE","uruguay":"UY","paraguay":"PY","bolivia":"BO","mexico":"MX","méxico":"MX","españa":"ES","espana":"ES","spain":"ES","portugal":"PT","francia":"FR","france":"FR","italia":"IT","italy":"IT","alemania":"DE","germany":"DE","reino unido":"GB","uk":"GB","inglaterra":"GB","united kingdom":"GB","estados unidos":"US","eeuu":"US","usa":"US","united states":"US","brasil":"BR","brazil":"BR","canadá":"CA","canada":"CA"};
  const splitDate = d => { const [y,m,day]=(d||'').split('-').map(n=>parseInt(n,10)); return {year:y,month:m,day}; };
  const splitTime = t => { const [h,mi]=(t||'00:00').split(':').map(n=>parseInt(n,10)); return {hour:h,minute:mi}; };
  const clamp360 = x => ((x%360)+360)%360;
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
      p=>{ const c=structuredClone(p); if(c.active_points) c.active_points=c.active_points.filter(x=>x!=="Mean_South_Node"); return c; },
      p=>{ const c=structuredClone(p); if(c.active_points) c.active_points=c.active_points.filter(x=>!["Chiron","Mean_Lilith"].includes(x)); return c; },
      p=>{ const c=structuredClone(p); delete c.active_points; return c; },
      p=>{ const c=structuredClone(p); if(c.subject){ const s=structuredClone(c.subject); delete s.house_system; c.subject=s; } return c; },
      p=>{ const c=structuredClone(p); if(c.subject){ const s=structuredClone(c.subject); delete s.geonames_username; c.subject=s; } return c; },
    ];
    let lastErr=null;
    for(const v of variants){
      const payload=v(structuredClone(basePayload));
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

  // ===== Nombres / aspectos =====
  const ASPECT_ANGLE = {conjunction:0,opposition:180,square:90,trine:120,sextile:60,quincunx:150,inconjunct:150,semisextile:30,semisquare:45,sesquiquadrate:135,quintile:72,biquintile:144,novile:40,binovile:80,septile:51.4286,biseptile:102.8571,triseptile:154.2857,undecile:32.7273};
  const ASPECTO_ES = {conjunction:"Conjunción",opposition:"Oposición",square:"Cuadratura",trine:"Trígono",sextil:"Sextil",quincunx:"Quincuncio",semisextile:"Semisextil",semisquare:"Semicuadratura",sesquiquadrate:"Sesquicuadratura",quintile:"Quintil",biquintile:"Biquintil",novile:"Novil",binovile:"Binovil",septile:"Septil",biseptile:"Biseptil",triseptile:"Triseptil",undecile:"Undécil"};
  function sinAcentos(s){ return (s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,""); }
  function aspectKey(raw){
    const t=(raw||"").toString();
    const lower=sinAcentos(t).toLowerCase().replace(/[\s-]+/g,"_");
    const map={conjuncion:"conjunction",conj:"conjunction",oposicion:"opposition",opp:"opposition",cuadratura:"square",trigono:"trine",tri:"trine",sextil:"sextile",sex:"sextile",quincuncio:"quincunx",inconjuncto:"quincunx",inconjunct:"quincunx",semicuadratura:"semisquare",sesquicuadratura:"sesquiquadrate",semisextil:"semisextile"};
    return map[lower] || lower;
  }
  const POINT_ES = {"Sun":"Sol","Moon":"Luna","Mercury":"Mercurio","Venus":"Venus","Mars":"Marte","Jupiter":"Júpiter","Saturn":"Saturno","Uranus":"Urano","Neptune":"Neptuno","Pluto":"Plutón","Ascendant":"Ascendente","Medium_Coeli":"Medio Cielo","Mean_Node":"Nodo Norte","Mean_South_Node":"Nodo Sur","Chiron":"Quirón","Mean_Lilith":"Lilith (media)"};
  const ORDER = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto","Ascendant","Medium_Coeli","Mean_Node","Mean_South_Node","Chiron","Mean_Lilith"];
  const ALIAS2CAN = (()=>{ const out={"sun":"Sun","moon":"Moon","mercury":"Mercury","venus":"Venus","mars":"Mars","jupiter":"Jupiter","saturn":"Saturn","uranus":"Uranus","neptune":"Neptune","pluto":"Pluto","asc":"Ascendant","ascendant":"Ascendant","mc":"Medium_Coeli","medium_coeli":"Medium_Coeli","midheaven":"Medium_Coeli","mean_node":"Mean_Node","true_node":"True_Node","mean_south_node":"Mean_South_Node","chiron":"Chiron","mean_lilith":"Mean_Lilith","sol":"Sun","luna":"Moon","mercurio":"Mercury","marte":"Mars","j\u00fapiter":"Jupiter","jupiter":"Jupiter","saturno":"Saturn","urano":"Uranus","neptuno":"Neptune","pluton":"Pluto","plut\u00f3n":"Pluto","ascendente":"Ascendant","medio_cielo":"Medium_Coeli","nodo_norte":"Mean_Node"}; const exp={}; for(const [k,v] of Object.entries(out)){ exp[k]=v; exp[k.replace(/\s+/g,'_')]=v; exp[k.replace(/[\s\-()]+/g,'_')]=v; } return exp; })();
  function resolveCanonName(raw){
    if(!raw) return null;
    const s=String(raw).trim(); if(/^\d+$/.test(s)){ const i=parseInt(s,10); if(i>=0&&i<ORDER.length) return ORDER[i]; if(i>=1&&i<=ORDER.length) return ORDER[i-1]; }
    const k=s.toLowerCase(), nrm=sinAcentos(s).toLowerCase(), u=nrm.replace(/[\s\-()]+/g,'_');
    return ALIAS2CAN[k] || ALIAS2CAN[nrm] || ALIAS2CAN[u] || s;
  }
  function toCanon(x){ return resolveCanonName(x) || String(x); }

  function getLonFromObj(o){
    if(o==null) return null;
    if(typeof o==='number' || typeof o==='string') return parseAngleAny(o);
    const v = o.longitude ?? o.lon ?? o.abs_pos ?? o.value ?? o.position ?? o?.ecliptic?.lon ?? o?.ecliptic?.longitude ?? o?.cusp ?? o?.cusp_longitude;
    return parseAngleAny(v);
  }

  // === detectores de cúspides (robusto) ===
  function extractCuspsFromContainer(cont){
    if(!cont) return null;
    // Caso A: array [12] con números/strings/objetos
    if(Array.isArray(cont) && cont.length>=12){
      const out = [null];
      for(let i=0;i<12;i++){ const val=getLonFromObj(cont[i]); out[i+1]=Number.isFinite(val)?clamp360(val):null; }
      if(out.slice(1).every(v=>Number.isFinite(v))) return out;
    }
    // Caso B: objeto con keys 1..12 o cusp1..cusp12 o house1..house12
    if(typeof cont==='object'){
      const out=[null];
      let filled=0;
      for(let i=1;i<=12;i++){
        const keys=[
          String(i), `${i}`, `cusp${i}`, `cusp_${i}`, `house${i}`, `house_${i}`, `H${i}`, `House${i}`, `house_${String(i).padStart(2,'0')}`
        ];
        let val=null;
        for(const k of keys){
          if(k in cont){ val = getLonFromObj(cont[k]); if(Number.isFinite(val)) break; }
          // si hay sub-objeto {longitude: x}
          if(cont[k] && typeof cont[k]==='object'){
            const tryLon = getLonFromObj(cont[k]);
            if(Number.isFinite(tryLon)){ val=tryLon; break; }
          }
        }
        if(!Number.isFinite(val) && cont[i-1]!=null){
          const tryArr = getLonFromObj(cont[i-1]);
          if(Number.isFinite(tryArr)) val = tryArr;
        }
        out[i] = Number.isFinite(val)?clamp360(val):null;
        if(Number.isFinite(out[i])) filled++;
      }
      if(filled===12) return out;
      // Caso C: lista de objetos {number: i, ...}
      if(Array.isArray(cont)){
        const map=[null];
        cont.forEach(h=>{
          const n = h?.number ?? h?.house ?? h?.index;
          const v = getLonFromObj(h);
          if(n>=1&&n<=12 && Number.isFinite(v)) map[n]=clamp360(v);
        });
        if(map.filter(Boolean).length===12) return map;
      }
    }
    return null;
  }

  function extractCuspsFromResponse(res){
    const candidates = [
      res?.house_cusps, res?.houses, res?.cusps, res?.houses_cusps,
      res?.data?.house_cusps, res?.data?.houses, res?.data?.cusps,
      res?.chart?.house_cusps, res?.chart?.houses, res?.chart?.cusps
    ];
    for(const c of candidates){
      const got = extractCuspsFromContainer(c);
      if(got && got.filter(Boolean).length===12) return got;
    }
    // A veces viene todo el objeto como {1:...,2:..., ...}
    const direct = extractCuspsFromContainer(res);
    if(direct && direct.filter(Boolean).length===12) return direct;
    return null;
  }

  // === SVG → PNG para el PDF ===
  function svgToPngDataUrl(svgEl, widthPx=1000){
    return new Promise((resolve)=>{
      if(!svgEl) return resolve(null);
      const xml = new XMLSerializer().serializeToString(svgEl);
      const svg64 = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(xml);
      const img = new Image(); img.crossOrigin = 'anonymous';
      img.onload = ()=>{
        const ratio = img.height ? (img.width/ img.height) : 1;
        const canvas = document.createElement('canvas');
        canvas.width = widthPx;
        canvas.height = Math.round(widthPx / ratio);
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        try{ resolve(canvas.toDataURL('image/png')); }catch(e){ resolve(svg64); }
      };
      img.onerror = ()=> resolve(null);
      img.src = svg64;
    });
  }

  // === Exportar PDF (ajuste a la derecha) ===
  async function descargarPDF(){
    try{
      const container = document.getElementById('resultado');
      if(!container || container.style.display==='none'){ alert('Primero genera la carta.'); return; }

      // Sustituir rueda por PNG temporalmente
      const svgEl = container.querySelector('#svg svg');
      const svgBox = container.querySelector('#svg');
      const oldSVG = svgBox ? svgBox.innerHTML : '';
      if(svgEl){
        const dataUrl = await svgToPngDataUrl(svgEl, 950);
        svgBox.innerHTML = '';
        const img = document.createElement('img');
        img.src = dataUrl || '';
        img.style.width = '700px';
        img.style.height = 'auto';
        img.style.display = 'block';
        img.style.margin = '0 auto';
        svgBox.appendChild(img);
      }

      // Mostrar pie y aplicar un pequeño padding izquierdo para “correr” a la derecha
      const pdfOnly = container.querySelectorAll('.pdf-only'); pdfOnly.forEach(el=> el.style.display='block');
      const oldWidth = container.style.width, oldMaxWidth = container.style.maxWidth, oldPad = container.style.padding;
      container.style.width='794px'; container.style.maxWidth='794px';
      container.style.padding='0 14px 0 28px'; // más margen a la izquierda para que no quede pegado

      const nombre = (document.getElementById('inp-name').value || 'Carta-natal').trim().replace(/\s+/g,'_');
      const fecha = (document.getElementById('inp-date').value || '').replace(/-/g,'');
      const file = `Carta-natal_${nombre || 'Consulta'}_${fecha || ''}.pdf`;

      await html2pdf().set({
        margin:       [12,16,18,10], // un poco más de margen izquierdo
        filename:     file,
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, useCORS: true, logging: false, windowWidth: 1000 },
        jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' },
        pagebreak:    { mode: ['css','legacy'] }
      }).from(container).save();

      // Revertir
      if(svgBox){ svgBox.innerHTML = oldSVG; }
      pdfOnly.forEach(el=> el.style.display='none');
      container.style.width = oldWidth; container.style.maxWidth = oldMaxWidth; container.style.padding = oldPad;

    }catch(e){
      alert('No se pudo crear el PDF. Como alternativa usa Imprimir → Guardar como PDF.');
    }
  }

  // === Endpoints auxiliares ===
  async function fetchHousesResponse(subject){
    const tryEndpoints = ['/natal-houses','/houses','/natal-chart-data','/natal-positions','/chart-data','/natal-aspects-data'];
    for(const ep of tryEndpoints){
      try{
        const res = await callWithFallbacks(APIBASE+ep, {subject, language:LANG, active_points:["Ascendant","Medium_Coeli"]}, false);
        // si viene JSON plano, lo devolvemos; si viene array, lo envolvemos
        if(res) return res;
      }catch(_){}
    }
    return null;
  }
  async function fetchAsc(subject){
    const tryEndpoints = ['/natal-positions','/positions','/natal-points','/points','/chart-data','/natal-aspects-data'];
    for(const ep of tryEndpoints){
      try{
        const res = await callWithFallbacks(APIBASE+ep, {subject, language:LANG, active_points:["Ascendant"]}, false);
        const lists = [res?.points, res?.planets, res?.data?.points, res?.data?.planets, Array.isArray(res)?res: null].filter(Boolean);
        const arr = lists[0] || [];
        for(const p of arr){
          const name = toCanon(p.name ?? p.point ?? p.id ?? p.code ?? p.label);
          if(name==="Ascendant"){
            const v = getLonFromObj(p);
            if(Number.isFinite(v)) return clamp360(v);
          }
        }
      }catch(_){}
    }
    return null;
  }
  async function fetchPlanetPositions(subject){
    const tryEndpoints = ['/natal-positions','/positions','/natal-points','/points','/chart-data'];
    for(const ep of tryEndpoints){
      try{
        const res = await callWithFallbacks(APIBASE+ep, {subject, language:LANG, active_points:["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"]}, false);
        const lists = [res?.planets, res?.points, res?.data?.planets, res?.data?.points, Array.isArray(res)?res: null].filter(Boolean);
        const arr = lists[0] || [];
        const out = {};
        for(const p of arr){
          const name = toCanon(p.name ?? p.point ?? p.id ?? p.code ?? p.label);
          if(["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"].includes(name)){
            const v = getLonFromObj(p);
            if(Number.isFinite(v)) out[name] = clamp360(v);
          }
        }
        if(Object.keys(out).length) return out;
      }catch(_){}
    }
    return {};
  }

  // === Generar ===
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
      const code = ISO2[norm(country)] || null;

      const subject={year,month,day,hour,minute,city,name,zodiac_type:zodiac,house_system:house,geonames_username:GEOUSER};
      if(code) subject.nation=code;

      const active_points=["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto","Ascendant","Medium_Coeli","Mean_Node","Mean_South_Node","Chiron","Mean_Lilith"];

      // 1) Gráfico (SVG)
      const svg = await callWithFallbacks(APIBASE+'/birth-chart',{ subject, language:LANG, theme:THEME, style:THEME, chart_theme:THEME, active_points }, true);
      if(svg && svg.includes('<svg')) $svg.innerHTML = svg;

      // 2) Aspectos
      const data = await callWithFallbacks(APIBASE+'/natal-aspects-data',{ subject, language:LANG, active_points }, false);
      const aspects = (data && (data.aspects||data.natal_aspects)) ? (data.aspects||data.natal_aspects) : [];

      // 3) Posiciones planetarias
      let lonByPlanet = await fetchPlanetPositions(subject);
      if(Object.keys(lonByPlanet).length < 10){
        aspects.forEach(a=>{
          const n1 = toCanon(a.p1_name ?? a.point_1 ?? a.point1 ?? a.p1 ?? a.object1 ?? a.planet1);
          const n2 = toCanon(a.p2_name ?? a.point_2 ?? a.point2 ?? a.p2 ?? a.object2 ?? a.planet2);
          const l1 = parseAngleAny(a.p1_abs_pos ?? a.p1_longitude ?? a.p1_lon ?? a?.p1?.longitude);
          const l2 = parseAngleAny(a.p2_abs_pos ?? a.p2_longitude ?? a.p2_lon ?? a?.p2?.longitude);
          if(Number.isFinite(l1) && !lonByPlanet[n1]) lonByPlanet[n1]=clamp360(l1);
          if(Number.isFinite(l2) && !lonByPlanet[n2]) lonByPlanet[n2]=clamp360(l2);
        });
      }

      // 4) Cúspides (robusto) + Asc
      const housesRes = await fetchHousesResponse(subject);
      const cusps = extractCuspsFromResponse(housesRes) || [];
      const ascLon = await fetchAsc(subject);

      // 5) Asignación de casas (sin rotar; tolerancia en vértices)
      function houseOfByCusps(lon){
        if(!cusps || cusps.filter(x=>Number.isFinite(x)).length!==12) return null;
        const eps = 1/60; // 1' de arco
        const L = clamp360(lon);
        for(let i=1;i<=12;i++){
          const start = clamp360(cusps[i]);
          const end   = clamp360(cusps[i%12+1]);
          const dx  = (L - start + 360) % 360;
          const arc = (end - start + 360) % 360 || 30;
          if(dx < eps) return i;                          // en la cúspide inicial → casa i
          if(dx > eps && dx < arc - eps) return i;        // dentro del tramo
          if(Math.abs(dx - arc) <= eps) return i;         // en la cúspide final lo mantenemos en i
        }
        return 12;
      }
      function houseOfByWholeSign(lon){
        if(!Number.isFinite(ascLon)) return null;
        const ascSign = Math.floor(clamp360(ascLon)/30);
        const lonSign = Math.floor(clamp360(lon   )/30);
        return ((lonSign - ascSign + 12) % 12) + 1;
      }
      function houseOf(lon){
        return houseOfByCusps(lon) ?? houseOfByWholeSign(lon) ?? "—";
      }

      // 6) Tabla de POSICIONES (con casas)
      const PLANETS = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"];
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
      $pos.innerHTML = `<h2>Posiciones planetarias</h2><table>${headPos}${bodyPos}</table>`;

      // 7) Elementos y Cualidades
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
      const pct = n => counted? Math.round(n*100/counted) : 0;
      const elemRows = Object.keys(countElem).map(k=>`<tr><td>${k}</td><td>${pct(countElem[k])}%</td></tr>`).join("");
      const modRows  = Object.keys(countMod ).map(k=>`<tr><td>${k}</td><td>${pct(countMod[k ])}%</td></tr>`).join("");
      $em.innerHTML =
        `<h2>Distribución de elementos y cualidades</h2>
         <div class="grid-2">
           <div><table><thead><tr><th>Elemento</th><th>%</th></tr></thead><tbody>${elemRows}</tbody></table></div>
           <div><table><thead><tr><th>Cualidad</th><th>%</th></tr></thead><tbody>${modRows}</tbody></table></div>
         </div>`;

      // 8) Aspectos + orbe
      function lonFromAspect(a, idx){
        const pref = idx===1 ? 'p1' : 'p2';
        const candidates = [a[`${pref}_abs_pos`], a[`${pref}_abs_long`], a[`${pref}_abs_longitude`], a[`${pref}_longitude`], a[`${pref}_lon`], a[`${pref}_long`]];
        for(const v of candidates){ const num = parseAngleAny(v); if(Number.isFinite(num)) return num; }
        const nested = a[pref] || a[idx===1?'first':'second'] || a[idx===1?'from':'to'] || a[idx===1?'object1':'object2'] || a[idx===1?'point1':'point2'];
        if(nested){ const v = getLonFromObj(nested); if(Number.isFinite(v)) return v; }
        return null;
      }
      const rowsA = aspects.map(a=>{
        const key = aspectKey(a.type || a.aspect || a.kind || "");
        const label= ASPECTO_ES[key] || (a.type||a.aspect||a.kind||"");
        const target = ASPECT_ANGLE[key];
        const c1 = toCanon(a.p1_name ?? a.point_1 ?? a.point1 ?? a.p1 ?? a.object1 ?? a.planet1);
        const c2 = toCanon(a.p2_name ?? a.point_2 ?? a.point2 ?? a.p2 ?? a.object2 ?? a.planet2);
        if(c1==="True_Node" || c2==="True_Node") return null;
        const disp1 = POINT_ES[c1] || String(c1).replace(/_/g,' ');
        const disp2 = POINT_ES[c2] || String(c2).replace(/_/g,' ');
        let l1 = lonFromAspect(a,1), l2 = lonFromAspect(a,2);
        let sep = parseAngleAny(a.separation ?? a.sep ?? a.sep_deg ?? a.angle ?? a.angle_deg ?? a.aspect_angle);
        if(!Number.isFinite(sep) && Number.isFinite(l1) && Number.isFinite(l2)) sep = Math.abs(((l1 - l2 + 540) % 360) - 180);
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
      $tabs.innerHTML = `<h2>Aspectos</h2><table>${headA}${bodyA}</table>`;

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
