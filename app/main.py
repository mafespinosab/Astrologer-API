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
  :root{ --ink:#111; --line:#000; --pxmm:3.78; } /* 1 mm ≈ 3.78 px */
  *{box-sizing:border-box}
  body{font-family:system-ui,Arial,sans-serif;color:var(--ink);background:#fff;margin:0}
  /* ancho pensado para la vista (web). Para PDF uso un clon “A4” con ancho fijo en px */
  .box{max-width:820px;margin:0 auto;padding:26px 22px}
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
  .row{display:grid;grid-template-columns:1fr 1fr;gap:26px;align-items:start}
  .mt{margin-top:16px}
  .btns{display:flex;gap:12px;flex-wrap:wrap;align-items:center}
  .alert{border:1px solid var(--line);background:#fff;color:#000;border-radius:10px;padding:10px;margin:12px 0;display:none;white-space:pre-wrap}
  .ok{border:1px solid var(--line);padding:20px;border-radius:10px;margin-top:18px}
  .ok > * + *{margin-top:16px}
  table{width:100%;border-collapse:collapse;margin-top:10px;table-layout:fixed}
  thead th{background:#f7f7f7}
  th,td{border:1px solid var(--line);padding:8px 9px;text-align:left;font-size:14px;word-break:break-word;vertical-align:top}
  /* Permitir que la tabla continúe en la página siguiente, pero sin partir filas */
  table{page-break-inside:auto}
  tr{break-inside:avoid; page-break-inside:avoid}
  thead{display:table-header-group} tfoot{display:table-footer-group}
  .svgwrap{border:1px solid var(--line);border-radius:10px;overflow:hidden;padding:8px;background:#fff}
  #svg svg{max-width:100%;height:auto;display:block}

  .pagebreak{display:none}
  .pdf-only{display:none}
  #diag{display:none !important;}
  .grid-2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
  @media (max-width:820px){ .row{grid-template-columns:1fr} .grid-2{grid-template-columns:1fr} }

  /* En impresión del navegador (por si alguien usa Ctrl+P) */
  @media print{
    body{background:#fff;color:#000}
    .alert, .btns{display:none !important}
    .box{padding:10mm; max-width:190mm}
    .ok{border:none;padding:0}
    thead th{background:#eee}
    .pdf-only{display:block !important}
    .pagebreak{display:block; break-before:page}
    #svg img.pdf-wheel{width:170mm; max-width:170mm; height:auto; display:block; margin:0 auto}
    #svg svg{display:none !important}
  }
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

    <!-- Página nueva para que la rueda quede sola en 1ª hoja -->
    <div class="pagebreak"></div>

    <div class="grid-2">
      <div id="pos-table"></div>
      <div id="elemmod"></div>
    </div>

    <div id="tablas"></div>

    <!-- Pie SOLO PDF -->
    <div class="pdf-only" style="margin-top:12px;border-top:1px solid #000;padding-top:8px;font-size:12px;">
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

  // ===== Utilidades =====
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

  // ===== Diccionarios =====
  const ASPECT_ANGLE = {conjunction:0,opposition:180,square:90,trine:120,sextile:60,quincunx:150,inconjunct:150,semisextile:30,semisquare:45,sesquiquadrate:135,quintile:72,biquintile:144,novile:40,binovile:80,septile:51.4286,biseptile:102.8571,triseptile:154.2857,undecile:32.7273};
  const ASPECTO_ES = {conjunction:"Conjunción",opposition:"Oposición",square:"Cuadratura",trine:"Trígono",sextile:"Sextil",quincunx:"Quincuncio",semisextile:"Semisextil",semisquare:"Semicuadratura",sesquiquadrate:"Sesquicuadratura",quintile:"Quintil",biquintile:"Biquintil",novile:"Novil",binovile:"Binovil",septile:"Septil",biseptile:"Biseptil",triseptile:"Triseptil",undecile:"Undécil"};
  function sinAcentos(s){ return (s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,""); }
  function aspectKey(raw){
    const t=(raw||"").toString();
    const lower=sinAcentos(t).toLowerCase().replace(/[\s-]+/g,"_");
    const map={conjuncion:"conjunction",conj:"conjunction",oposicion:"opposition",opp:"opposition",cuadratura:"square",trigono:"trine",tri:"trine",sextil:"sextile",sex:"sextile",quincuncio:"quincunx",inconjuncto:"quincunx",inconjunct:"quincunx",semicuadratura:"semisquare",sesquicuadratura:"sesquiquadrate",semisextil:"semisextile"};
    return map[lower] || lower;
  }
  const POINT_ES = {"Sun":"Sol","Moon":"Luna","Mercury":"Mercurio","Venus":"Venus","Mars":"Marte","Jupiter":"Júpiter","Saturn":"Saturno","Uranus":"Urano","Neptune":"Neptuno","Pluto":"Plutón","Ascendant":"Ascendente","Medium_Coeli":"Medio Cielo","Mean_Node":"Nodo Norte","Mean_South_Node":"Nodo Sur","Chiron":"Quirón","Mean_Lilith":"Lilith (media)"};
  const ORDER = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto","Ascendant","Medium_Coeli","Mean_Node","Mean_South_Node","Chiron","Mean_Lilith"];
  const ALIAS2CAN = (()=> {
    const out = {"sun":"Sun","moon":"Moon","mercury":"Mercury","venus":"Venus","mars":"Mars","jupiter":"Jupiter","saturn":"Saturn","uranus":"Uranus","neptune":"Neptune","pluto":"Pluto","asc":"Ascendant","ascendant":"Ascendant","mc":"Medium_Coeli","medium_coeli":"Medium_Coeli","midheaven":"Medium_Coeli","mean_node":"Mean_Node","true_node":"True_Node","mean_south_node":"Mean_South_Node","chiron":"Chiron","mean_lilith":"Mean_Lilith","sol":"Sun","luna":"Moon","mercurio":"Mercury","marte":"Mars","j\u00fapiter":"Jupiter","jupiter":"Jupiter","saturno":"Saturno","urano":"Uranus","neptuno":"Neptune","pluton":"Pluto","plut\u00f3n":"Pluto","ascendente":"Ascendant","medio_cielo":"Medium_Coeli","nodo_norte":"Mean_Node"};
    const exp={}; for(const [k,v] of Object.entries(out)){ exp[k]=v; exp[k].toString(); exp[k.replace(/\s+/g,'_')]=v; exp[k.replace(/[\s\-()]+/g,'_')]=v; } return exp;
  })();
  function resolveCanonName(raw){
    if(!raw) return null;
    const s=String(raw).trim(); if(/^\d+$/.test(s)){ const i=parseInt(s,10); if(i>=0&&i<ORDER.length) return ORDER[i]; if(i>=1&&i<=ORDER.length) return ORDER[i-1]; }
    const k=s.toLowerCase(), nrm=sinAcentos(s).toLowerCase(), u=nrm.replace(/[\s\-()]+/g,'_');
    return ALIAS2CAN[k] || ALIAS2CAN[nrm] || ALIAS2CAN[u] || s;
  }
  function toCanon(x){ return resolveCanonName(x) || String(x); }

  // === util para leer longitudes en objetos variados ===
  function getLonFromObj(o){
    if(!o) return null;
    const v = o.longitude ?? o.lon ?? o.abs_pos ?? o.value ?? o.position ?? o?.ecliptic?.lon ?? o?.ecliptic?.longitude;
    return parseAngleAny(v);
  }

  // === SVG → PNG solo en PDF (sin mover el clon fuera de la pantalla) ===
  function svgToPngDataUrl(svgEl, widthPx){
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

  async function descargarPDF(){
    try{
      const A4_WIDTH_PX = 794;       // A4 @ 96dpi aprox
      const MARGIN_MM   = 10;        // márgenes jsPDF
      const PX_PER_MM   = 3.78;
      const CONTENT_W   = Math.floor(A4_WIDTH_PX - 2 * MARGIN_MM * PX_PER_MM); // ~718px

      // Clon “limpio” para PDF (no lo saco fuera de viewport: solo hidden)
      let clone = document.getElementById('resultado').cloneNode(true);
      clone.style.visibility = 'hidden';
      clone.style.position   = 'fixed';
      clone.style.left       = '0';
      clone.style.top        = '0';
      clone.style.width      = CONTENT_W + 'px';
      // quitar padding/márgenes internos del clon para que no recorte por la izquierda
      clone.querySelectorAll('.box').forEach(el=>{ el.style.padding='0'; el.style.margin='0 auto'; el.style.maxWidth='initial'; });

      // mostrar pie PDF en el clon
      clone.querySelectorAll('.pdf-only').forEach(el=> el.style.display='block');
      // ocultar botones/alertas en el clon
      clone.querySelectorAll('.btns,.alert').forEach(el=> el.remove());

      // Sustituir SVG por PNG de ancho seguro
      const srcSvg = document.querySelector('#svg svg');
      if(srcSvg){
        const pngURL = await svgToPngDataUrl(srcSvg, Math.min(CONTENT_W, 700));
        const wrap = clone.querySelector('#svg'); if(wrap){ wrap.innerHTML=''; }
        const img = document.createElement('img');
        img.className = 'pdf-wheel';
        img.src = pngURL || '';
        img.style.width = Math.min(CONTENT_W, 700) + 'px';
        img.style.height = 'auto';
        img.style.display = 'block';
        img.style.margin = '0 auto';
        if(wrap) wrap.appendChild(img);
      }

      document.body.appendChild(clone);

      const nombre = (document.getElementById('inp-name').value || 'Carta-natal').trim().replace(/\s+/g,'_');
      const fecha = (document.getElementById('inp-date').value || '').replace(/-/g,'');
      const file = `Carta-natal_${nombre || 'Consulta'}_${fecha || ''}.pdf`;

      if(!window.html2pdf){ window.print(); clone.remove(); return; }
      await html2pdf().set({
        margin:       [MARGIN_MM,MARGIN_MM,Math.max(MARGIN_MM,12),MARGIN_MM],  // un pelín más abajo
        filename:     file,
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, useCORS: true, logging: false, windowWidth: A4_WIDTH_PX },
        jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' },
        pagebreak:    { mode: ['css'] }
      }).from(clone).save();

      clone.remove();
    }catch(e){
      alert('No se pudo crear el PDF. Como alternativa usa Imprimir → Guardar como PDF.');
    }
  }

  // === Endpoints auxiliares ===
  async function fetchHouses(subject){
    const tryEndpoints = ['/natal-houses','/houses','/natal-chart-data','/natal-positions','/chart-data','/natal-aspects-data'];
    for(const ep of tryEndpoints){
     














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
