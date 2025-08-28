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
  .box{max-width:1020px;margin:0 auto;padding:36px 34px}
  h2{font-weight:800;margin:0 0 18px}
  label{display:block;font-size:14px;margin:12px 0 6px}
  input,select,button{
    width:100%;padding:13px 12px;border:1px solid var(--line);
    background:#fff;color:#000;border-radius:12px;line-height:1.2
  }
  button{cursor:pointer;font-weight:800}
  /* MÁS ESPACIO y columnas idénticas */
  .row{
    display:grid;
    grid-template-columns:1fr 1fr;   /* mismas anchuras */
    gap:36px;                        /* más aire */
    align-items:start;
  }
  .mt{margin-top:18px}
  .alert{border:1px solid var(--line);background:#fff;color:#000;border-radius:12px;padding:12px;margin:12px 0;display:none;white-space:pre-wrap}
  .ok{border:1px solid var(--line);padding:26px;border-radius:12px;margin-top:18px}
  .ok > * + *{margin-top:18px}

  /* Tablas: columnas consistentes */
  table{width:100%;border-collapse:collapse;margin-top:16px;table-layout:fixed}
  thead th{background:#f7f7f7}
  th,td{border:1px solid var(--line);padding:10px 12px;text-align:left;font-size:14px;word-break:break-word;vertical-align:top}

  .svgwrap{border:1px solid var(--line);border-radius:12px;overflow:hidden;padding:10px;background:#fff}
  #svg svg{max-width:100%;height:auto;display:block}
  @media (max-width:780px){ .row{grid-template-columns:1fr} }
</style>
</head><body>
<div class="box">
  <h2 id="titulo">Tu carta natal</h2>
  <div id="alert" class="alert"></div>

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

  <!-- Sideral oculto por defecto; sólo aparece si pones ?sidereal=on -->
  <div class="row" id="row-sidereal" style="display:none">
    <div>
      <label>Zodiaco</label>
      <select id="inp-zodiac">
        <option value="Tropic" selected>Tropical</option>
        <option value="Sidereal">Sideral</option>
      </select>
    </div>
    <div>
      <label>Ayanamsha (si usas Sideral)</label>
      <select id="inp-ayanamsha">
        <option value="">—</option>
        <option value="FAGAN_BRADLEY">Fagan/Bradley</option>
        <option value="LAHIRI">Lahiri</option>
      </select>
    </div>
  </div>

  <div class="mt">
    <button id="btn-gen">Generar carta</button>
  </div>

  <div id="resultado" class="ok" style="display:none">
    <div id="svg" class="svgwrap"></div>
    <div id="tablas"></div>
  </div>
</div>

<script>
(function(){
  // ===== Parámetros por URL =====
  const q       = new URLSearchParams(location.search);
  const LANG    = q.get('lang')    || 'ES';
  const THEME   = q.get('theme')   || 'light';   // claro por defecto
  const GEOUSER = q.get('geouser') || 'mofeto';
  const TITLE   = q.get('title')   || 'Tu carta natal';
  const SHOW_SID= (q.get('sidereal') === 'on');

  document.getElementById('titulo').textContent = decodeURIComponent(TITLE||'');
  if(SHOW_SID){ document.getElementById('row-sidereal').style.display='grid'; }

  // ===== Helpers UI =====
  const $ = id => document.getElementById(id);
  const $alert=$('alert'), $out=$('resultado'), $svg=$('svg'), $tabs=$('tablas'), $btn=$('btn-gen');
  const showAlert = t => { $alert.style.display='block'; $alert.textContent=t; };
  const hideAlert = ()=>{ $alert.style.display='none'; $alert.textContent=''; };

  // ===== Utils =====
  const norm = s => (s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
  const ISO2 = {"colombia":"CO","argentina":"AR","chile":"CL","peru":"PE","ecuador":"EC","venezuela":"VE","uruguay":"UY","paraguay":"PY","bolivia":"BO","mexico":"MX","méxico":"MX","españa":"ES","espana":"ES","spain":"ES","portugal":"PT","francia":"FR","france":"FR","italia":"IT","italy":"IT","alemania":"DE","germany":"DE","reino unido":"GB","uk":"GB","inglaterra":"GB","united kingdom":"GB","estados unidos":"US","eeuu":"US","usa":"US","united states":"US","brasil":"BR","brazil":"BR","canadá":"CA","canada":"CA"};
  const splitDate = d => { const [y,m,day]=(d||'').split('-').map(n=>parseInt(n,10)); return {year:y,month:m,day}; };
  const splitTime = t => { const [h,mi]=(t||'00:00').split(':').map(n=>parseInt(n,10)); return {hour:h,minute:mi}; };

  async function call(path, payload, expectSVG=false){
    const r = await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(!r.ok){ const txt=await r.text().catch(()=> ""); throw new Error(`HTTP ${r.status}: ${txt}`); }
    const ct=r.headers.get('content-type')||'';
    if(expectSVG){
      const t=await r.text();
      if(t.trim().startsWith('{')){ try{ const j=JSON.parse(t); return j.svg||j.chart||''; }catch{} }
      return t;
    } else if(ct.includes('application/json')) return r.json();
    else return r.text();
  }

  // ===== Tablas =====
  function tableHTML(head, rows){
    const thead = "<thead><tr>"+head.map(h=>`<th>${h}</th>`).join("")+"</tr></thead>";
    const tbody = "<tbody>"+rows.map(r=>"<tr>"+r.map(c=>`<td>${(c??"")||"—"}</td>`).join("")+"</tr>").join("")+"</tbody>";
    return `<table>${thead}${tbody}</table>`;
  }
  function signFromLon(lon){ const i=Math.floor((((lon%360)+360)%360)/30); return ["Aries","Tauro","G\u00e9minis","C\u00e1ncer","Leo","Virgo","Libra","Escorpio","Sagitario","Capricornio","Acuario","Piscis"][i]||""; }
  function degStr(lon){ const d=((lon%360)+360)%360; const g=Math.floor(d%30); const m=Math.floor((d%30-g)*60); return `${g}°${String(m).padStart(2,'0')}'`; }

  // Nombres de puntos y mapa para resolver índices/códigos
  const label = x => {
    if(x==null) return "";
    if(typeof x === "string" || typeof x === "number") return String(x);
    return x.name || x.point || x.body || x.id || x.code || x.symbol || x.title || x.label || "";
  };

  // Orden “canónico” y mapa 1→nombre (para cuando vienen números 1,2,12,13…)
  const ORDER = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto","Ascendant","Medium_Coeli","Mean_Node","Mean_South_Node","Chiron","Mean_Lilith"];
  const INDEX_MAP = ORDER.reduce((acc,name,i)=>{ acc[String(i+1)]=name; acc[String(i)]=name; return acc; },{}); // 1-based y 0-based

// —— Traducciones de aspectos al español (robusto con variantes)
const ASPECT_ES = {
  "conjunction":"Conjunción",
  "opp":"Oposición","opposition":"Oposición",
  "square":"Cuadratura","quartile":"Cuadratura",
  "trine":"Trígono",
  "sextile":"Sextil",
  "quincunx":"Quincuncio","inconjunct":"Quincuncio",
  "semi-square":"Semicuadratura","semisquare":"Semicuadratura","semi_square":"Semicuadratura",
  "sesquiquadrate":"Sesquicuadratura","sesqui-quadrate":"Sesquicuadratura","sesqui_quadrate":"Sesquicuadratura",
  "semi-sextile":"Semisextil","semisextile":"Semisextil","semi_sextile":"Semisextil",
  "quintile":"Quintil","biquintile":"Biquintil",
  "novile":"Novil","binovile":"Binovil",
  "septile":"Septil","biseptile":"Biseptil","triseptile":"Triseptil",
  "undecile":"Undécil"
};

// —— Ángulo teórico de cada aspecto (para calcular el orbe)
const ASPECT_DEG = {
  "conjunction":0,
  "opposition":180,"opp":180,
  "square":90,"quartile":90,
  "trine":120,
  "sextile":60,
  "quincunx":150,"inconjunct":150,
  "semisextile":30,"semi-sextile":30,"semi_sextile":30,
  "semisquare":45,"semi-square":45,"semi_square":45,
  "sesquiquadrate":135,"sesqui-quadrate":135,"sesqui_quadrate":135,
  "quintile":72,"biquintile":144,
  "novile":40,"binovile":80,
  "septile":51.4286,"biseptile":102.8571,"triseptile":154.2857,
  "undecile":32.7273
};

// —— utilidades para orbe
function minSepDeg(a,b){ return Math.abs(((a - b + 540) % 360) - 180); } // 0..180
function fmtDegMin(x){
  const d = Math.floor(x), m = Math.round((x - d)*60);
  const mm = (m===60)? 0 : m;
  const dd = (m===60)? d+1 : d;
  return `${dd}°${String(mm).padStart(2,"0")}'`;
}



  function buildPointMaps(points){
    const byKey = {};
    points.forEach((p,idx)=>{
      const display = p.name || p.point || p.id || p.code || p.symbol || ORDER[idx] || `P${idx+1}`;
      const keys = [
        p.name,p.point,p.id,p.code,p.symbol,p.key,p.body,p.planet,p.obj,
        String(idx), String(p.index||""), String(idx+1)
      ].filter(Boolean).map(v=>String(v).toLowerCase());
      keys.forEach(k=>{ byKey[k]=display; });
    });
    // sinónimos útiles
    byKey['asc']='Ascendant'; byKey['as']='Ascendant'; byKey['ascendant']='Ascendant';
    byKey['mc']='Medium_Coeli'; byKey['medium_coeli']='Medium_Coeli'; byKey['midheaven']='Medium_Coeli';
    byKey['nn']='Mean_Node'; byKey['north node']='Mean_Node'; byKey['node']='Mean_Node';
    byKey['sn']='Mean_South_Node'; byKey['south node']='Mean_South_Node';
    return {byKey};
  }
  function guessName(raw, maps){
    if(raw==null) return "";
    if(typeof raw==="object") return label(raw);
    const rawS = String(raw).trim();
    const k = rawS.toLowerCase();
    // Si viene número (1,2,12…) mapear por índice
    if(/^\d+$/.test(rawS) && (INDEX_MAP[rawS] || INDEX_MAP[String(parseInt(rawS,10))])){
      return INDEX_MAP[rawS] || INDEX_MAP[String(parseInt(rawS,10))];
    }
    return maps.byKey[k] || rawS;
  }

  function pickBody1(a){ return a.point_1||a.body_1||a.point1||a.a||a.A||a.p1||a.obj1||a.object1||a.planet1||a.c1||a.first||a.source||a["1"]||a.from||a.name1||a.p1_name||a.object1_name||a.body1||a.pointOne||a.left||a.idx1||a.index1||a.i1||""; }
  function pickBody2(a){ return a.point_2||a.body_2||a.point2||a.b||a.B||a.p2||a.obj2||a.object2||a.planet2||a.c2||a.second||a.target||a["2"]||a.to||a.name2||a.p2_name||a.object2_name||a.body2||a.pointTwo||a.right||a.idx2||a.index2||a.i2||""; }
  const pickOrb = a => a.orb ?? a.orb_deg ?? a.orbital ?? a.orb_value ?? a.delta ?? a.delta_deg ?? a.distance ?? a.error ?? a.difference ?? a.deg_diff ?? a.exactness ?? "";

  async function generar(){
    try{
      hideAlert(); $out.style.display='none'; $svg.innerHTML=""; $tabs.innerHTML=""; $btn.disabled=true; $btn.textContent="Calculando…";

      const name=$('inp-name').value.trim()||"Consulta";
      const city=$('inp-city').value.trim();
      const country=$('inp-country').value.trim();
      const {year,month,day}=splitDate($('inp-date').value);
      const {hour,minute}=splitTime($('inp-time').value);
      const house=$('inp-house').value||'P';
      const zodiac= (document.getElementById('row-sidereal').style.display==='grid')
        ? ($('inp-zodiac').value||'Tropic')
        : 'Tropic';
      const ayan  = (zodiac==='Sidereal') ? ($('inp-ayanamsha').value||'') : '';

      if(!year||!month||!day){ showAlert('Falta la fecha.'); return; }
      if(!city||!country){ showAlert('Escribe ciudad y país.'); return; }
      const code = ISO2[norm(country)] || null;

      const subject={year,month,day,hour,minute,city,name,zodiac_type:zodiac,house_system:house,geonames_username:GEOUSER};
      if(code) subject.nation=code;
      if(zodiac==='Sidereal' && ayan) subject.sidereal_mode=ayan;

      const active_points=[...ORDER]; // mismos nombres para coherencia

      // 1) SVG (tema claro por defecto)
      const svg = await call('/api/v4/birth-chart',{ subject, language:LANG, theme:THEME, style:THEME, chart_theme:THEME, active_points },true);
      if(!svg || !svg.includes('<svg')) throw new Error('El servidor no devolvió el SVG.');
      $svg.innerHTML=svg;

      // 2) Datos
      const data = await call('/api/v4/natal-aspects-data',{ subject, language:LANG, active_points },false);

      // PUNTOS
      const ptsRaw = (function pickPoints(d){
        if(Array.isArray(d)) return d;
        if(d?.planets && Array.isArray(d.planets)) return d.planets;
        if(d?.planets && typeof d.planets==='object') return Object.values(d.planets);
        if(d?.points) return d.points;
        if(d?.celestial_points) return d.celestial_points;
        return [];
      })(data);
      const maps = buildPointMaps(ptsRaw);

      const pts = ptsRaw.map((p,idx)=>{
        const lon = p.longitude ?? p.lon ?? p.longitude_deg ?? (p.ecliptic && p.ecliptic.lon) ?? p.abs_pos ?? 0;
        const house = p.house ?? p.house_number ?? "";
        const name = p.name || p.point || p.id || p.code || ORDER[idx] || `P${idx+1}`;
        return [name, signFromLon(lon), degStr(lon), house];
      });

      // orden bonito
      pts.sort((a,b)=> (ORDER.indexOf(a[0])==-1?99:ORDER.indexOf(a[0])) - (ORDER.indexOf(b[0])==-1?99:ORDER.indexOf(b[0])) );

      // CASAS
      const hsRaw = (function pickHouses(d){
        if(d?.houses && Array.isArray(d.houses)) return d.houses;
        if(d?.houses && typeof d.houses==='object') return Object.values(d.houses);
        if(d?.house_cusps) return d.house_cusps;
        return [];
      })(data);
      const hs = hsRaw.map((h,i)=>{
        const lon = h.longitude ?? h.lon ?? h.longitude_deg ?? (h.ecliptic && h.ecliptic.lon) ?? h.abs_pos ?? 0;
        const num = h.number ?? h.house ?? (i+1);
        return [num, signFromLon(lon), degStr(lon)];
      });

      // ASPECTOS → resolver números 1..N y mil variantes de nombres
      const aspects = (data && (data.aspects||data.natal_aspects)) ? (data.aspects||data.natal_aspects) : [];
      let rowsA = aspects.map(a=>{
        const t  = a.type || a.aspect || a.kind || "";
        let b1   = guessName(pickBody1(a), maps);
        let b2   = guessName(pickBody2(a), maps);
        // si aún son números, mapear por índice
        if(/^\d+$/.test(String(b1))) b1 = INDEX_MAP[String(b1)] || b1;
        if(/^\d+$/.test(String(b2))) b2 = INDEX_MAP[String(b2)] || b2;
        const o  = pickOrb(a);
        return [t,b1,b2,o];
      });

      let html="";
      if(pts.length) html += "<h3>Planetas / Puntos</h3>"+tableHTML(["Cuerpo","Signo","Grado","Casa"], pts);
      if(hs.length)  html += "<h3>Casas (cúspides)</h3>"+tableHTML(["Casa","Signo","Grado"], hs);
      if(rowsA.length && rowsA.some(r=>r[1]||r[2]||r[3])) {
        html += "<h3>Aspectos</h3>"+tableHTML(["Aspecto","Cuerpo 1","Cuerpo 2","Orbe"], rowsA);
      }
      document.getElementById('tablas').innerHTML = html || "<p style="+'"'+"color:#555"+'"'+">Recibí datos, pero no había tablas para mostrar.</p>";
      $out.style.display='block';

    }catch(e){
      showAlert("Error: "+(e?.message||e));
    }finally{
      $btn.disabled=false; $btn.textContent="Generar carta";
    }
  }

  document.getElementById('btn-gen').addEventListener('click', e=>{ e.preventDefault(); generar(); });
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
