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
  /* más espacio y columnas iguales */
  .row{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:36px;
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
  function degStr(lon){ const d=((lon%360)+360)%360; const g=Math.floor(d%30); const m=Math.round((d%30-g)*60); return `${g}°${String(m).padStart(2,'0')}'`; }
  function minSepDeg(a,b){ return Math.abs(((a - b + 540) % 360) - 180); } // 0..180
  function fmtDegMin(x){ const d=Math.floor(x), m=Math.round((x-d)*60); const dd=(m===60)?d+1:d; const mm=(m===60)?0:m; return `${dd}°${String(mm).padStart(2,"0")}'`; }

  // ——— Puntos canónicos (EN) y sus traducciones ES
  const ORDER = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto","Ascendant","Medium_Coeli","Mean_Node","Mean_South_Node","Chiron","Mean_Lilith"];
  const POINT_ES = {
    "Sun":"Sol","Moon":"Luna","Mercury":"Mercurio","Venus":"Venus","Mars":"Marte","Jupiter":"Júpiter","Saturn":"Saturno",
    "Uranus":"Urano","Neptune":"Neptuno","Pluto":"Plutón","Ascendant":"Ascendente","Medium_Coeli":"Medio Cielo",
    "Mean_Node":"Nodo Norte (medio)","Mean_South_Node":"Nodo Sur (medio)","Chiron":"Quirón","Mean_Lilith":"Lilith (media)"
  };
  const INDEX_MAP = ORDER.reduce((acc,name,i)=>{ acc[String(i+1)]=name; acc[String(i)]=name; return acc; },{});
  // sinónimos EN/ES → canónico EN
  const SYN = {
    "sol":"Sun","sun":"Sun",
    "luna":"Moon","moon":"Moon",
    "mercurio":"Mercury","mercury":"Mercury",
    "venus":"Venus",
    "marte":"Mars","mars":"Mars",
    "jupiter":"Jupiter","júpiter":"Jupiter","júpiter":"Jupiter",
    "saturno":"Saturn","saturn":"Saturn",
    "urano":"Uranus","uranus":"Uranus",
    "neptuno":"Neptune","neptune":"Neptune",
    "pluton":"Pluto","plutón":"Pluto","pluto":"Pluto",
    "ascendente":"Ascendant","asc":"Ascendant","as":"Ascendant","ascendant":"Ascendant",
    "mc":"Medium_Coeli","medio cielo":"Medium_Coeli","medium_coeli":"Medium_Coeli","midheaven":"Medium_Coeli",
    "nodo norte":"Mean_Node","north node":"Mean_Node","nn":"Mean_Node","mean_node":"Mean_Node",
    "nodo sur":"Mean_South_Node","south node":"Mean_South_Node","sn":"Mean_South_Node","mean_south_node":"Mean_South_Node",
    "quiron":"Chiron","quirón":"Chiron","chiron":"Chiron",
    "lilith":"Mean_Lilith","lilith (media)":"Mean_Lilith","mean_lilith":"Mean_Lilith"
  };
  function toCanonicalName(x){
    if(x==null) return "";
    const s = String(x).trim();
    if(/^\d+$/.test(s)) return INDEX_MAP[s] || INDEX_MAP[String(parseInt(s,10))] || s;
    const k = s.toLowerCase();
    if(POINT_ES[s]) return s; // ya es canónico EN
    return SYN[k] || s;
  }
  function toSpanishName(canonicalEN){
    return POINT_ES[canonicalEN] || canonicalEN;
  }

  // ——— Aspectos en español + ángulos teóricos (para ORBE)
  const ASPECT_ES = {
    "conjunction":"Conjunción","opp":"Oposición","opposition":"Oposición",
    "square":"Cuadratura","quartile":"Cuadratura","trine":"Trígono","sextile":"Sextil",
    "quincunx":"Quincuncio","inconjunct":"Quincuncio",
    "semi-square":"Semicuadratura","semisquare":"Semicuadratura","semi_square":"Semicuadratura",
    "sesquiquadrate":"Sesquicuadratura","sesqui-quadrate":"Sesquicuadratura","sesqui_quadrate":"Sesquicuadratura",
    "semi-sextile":"Semisextil","semisextile":"Semisextil","semi_sextile":"Semisextil",
    "quintile":"Quintil","biquintile":"Biquintil","novile":"Novil","binovile":"Binovil",
    "septile":"Septil","biseptile":"Biseptil","triseptile":"Triseptil","undecile":"Undécil"
  };
  const ASPECT_DEG = {
    "conjunction":0,"opposition":180,"opp":180,"square":90,"quartile":90,"trine":120,"sextile":60,
    "quincunx":150,"inconjunct":150,"semisextile":30,"semi-sextile":30,"semi_sextile":30,
    "semisquare":45,"semi-square":45,"semi_square":45,"sesquiquadrate":135,"sesqui-quadrate":135,"sesqui_quadrate":135,
    "quintile":72,"biquintile":144,"novile":40,"binovile":80,"septile":51.4286,"biseptile":102.8571,"triseptile":154.2857,"undecile":32.7273
  };

  const label = x => {
    if(x==null) return "";
    if(typeof x === "string" || typeof x === "number") return String(x);
    return x.name || x.point || x.body || x.id || x.code || x.symbol || x.title || x.label || "";
  };

  function buildPointMaps(points){
    const lonByCanon = {}; // longitudes por nombre canónico EN
    const rows = [];
    points.forEach((p,idx)=>{
      const lon = p.longitude ?? p.lon ?? p.longitude_deg ?? (p.ecliptic && p.ecliptic.lon) ?? p.abs_pos ?? null;
      const raw = p.name || p.point || p.id || ORDER[idx] || `P${idx+1}`;
      const canon = toCanonicalName(raw);
      const canonFinal = ORDER.includes(canon) ? canon : (ORDER[idx] || canon);
      if(lon!=null) lonByCanon[canonFinal] = Number(lon);
      const house = p.house ?? p.house_number ?? "";
      rows.push([canonFinal, signFromLon(Number(lon||0)), degStr(Number(lon||0)), house]);
    });
    // orden
    rows.sort((a,b)=> (ORDER.indexOf(a[0])==-1?99:ORDER.indexOf(a[0])) - (ORDER.indexOf(b[0])==-1?99:ORDER.indexOf(b[0])) );
    // traducir nombres a ES para mostrar
    const rowsES = rows.map(([canon,sign,deg,house])=>[toSpanishName(canon),sign,deg,house]);
    return {rowsES, lonByCanon};
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

      const active_points=[...ORDER];

      // 1) SVG
      const svg = await call('/api/v4/birth-chart',{ subject, language:LANG, theme:THEME, style:THEME, chart_theme:THEME, active_points },true);
      if(!svg || !svg.includes('<svg')) throw new Error('El servidor no devolvió el SVG.');
      $svg.innerHTML=svg;

      // 2) Datos
      const data = await call('/api/v4/natal-aspects-data',{ subject, language:LANG, active_points },false);

      // Puntos: filas (ya en ES) + longitudes por nombre canónico
      const ptsRaw = (function pickPoints(d){
        if(Array.isArray(d)) return d;
        if(d?.planets && Array.isArray(d.planets)) return d.planets;
        if(d?.planets && typeof d.planets==='object') return Object.values(d.planets);
        if(d?.points) return d.points;
        if(d?.celestial_points) return d.celestial_points;
        return [];
      })(data);
      const {rowsES:pts, lonByCanon} = buildPointMaps(ptsRaw);

      // Casas
      const hsRaw = (function pickHouses(d){
        if(d?.houses && Array.isArray(d.houses)) return d.houses;
        if(d?.houses && typeof d.houses==='object') return Object.values(d.houses);
        if(d?.house_cusps) return d.house_cusps;
        return [];
      })(data);
      const hs = hsRaw.map((h,i)=>{
        const lon = h.longitude ?? h.lon ?? h.longitude_deg ?? (h.ecliptic && h.ecliptic.lon) ?? h.abs_pos ?? 0;
        const num = h.number ?? h.house ?? (i+1);
        return [num, signFromLon(Number(lon||0)), degStr(Number(lon||0))];
      });

      // Aspectos → español + ORBE (si falta, lo calculo)
      const aspects = (data && (data.aspects||data.natal_aspects)) ? (data.aspects||data.natal_aspects) : [];
      let rowsA = aspects.map(a=>{
        const tRaw = (a.type || a.aspect || a.kind || "").toString().trim();
        const tKey = tRaw.toLowerCase().replace(/\s+/g,"_").replace(/-/g,"_");
        const tEs  = ASPECT_ES[tKey] || (tRaw ? tRaw.charAt(0).toUpperCase()+tRaw.slice(1) : "");

        // nombres canónicos EN -> luego traduzco a ES para mostrar
        const canon1 = toCanonicalName(label(pickBody1(a)));
        const canon2 = toCanonicalName(label(pickBody2(a)));
        const disp1  = toSpanishName(ORDER.includes(canon1)?canon1:(INDEX_MAP[canon1]||canon1));
        const disp2  = toSpanishName(ORDER.includes(canon2)?canon2:(INDEX_MAP[canon2]||canon2));

        // orbe
        let orb = pickOrb(a);
        if(orb === "" || orb == null){
          const c1 = ORDER.includes(canon1) ? canon1 : SYN[canon1?.toLowerCase?.()] || INDEX_MAP[canon1] || canon1;
          const c2 = ORDER.includes(canon2) ? canon2 : SYN[canon2?.toLowerCase?.()] || INDEX_MAP[canon2] || canon2;
          const l1 = lonByCanon[c1]; const l2 = lonByCanon[c2];
          const target = ASPECT_DEG[tKey];
          if(l1!=null && l2!=null && target!=null){
            const sep  = minSepDeg(l1,l2);
            const odeg = Math.abs(sep - target);
            orb = fmtDegMin(odeg);
          } else { orb = "—"; }
        } else {
          const n = Number(orb);
          if(Number.isFinite(n)) orb = fmtDegMin(Math.abs(n));
        }
        return [tEs, disp1 || "—", disp2 || "—", orb || "—"];
      });

      // Render
      let html="";
      if(pts.length) html += "<h3>Planetas / Puntos</h3>"+tableHTML(["Cuerpo","Signo","Grado","Casa"], pts);
      if(hs.length)  html += "<h3>Casas (cúspides)</h3>"+tableHTML(["Casa","Signo","Grado"], hs);
      if(rowsA.length && rowsA.some(r=>r[1]||r[2]||r[3])) {
        html += "<h3>Aspectos</h3>"+tableHTML(["Aspecto","Cuerpo 1","Cuerpo 2","Orbe"], rowsA);
      }
      document.getElementById('tablas').innerHTML = html || "<p style='color:#555'>Recibí datos, pero no había tablas para mostrar.</p>";
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
