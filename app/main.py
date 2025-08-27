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

WIDGET_HTML = r"""<!doctype html>
<html lang="es"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Carta natal</title>
<style>
  body{font-family:system-ui,Arial,sans-serif;color:#111;background:#fff;margin:0}
  .box{max-width:860px;margin:0 auto;padding:18px}
  h2{font-weight:700;margin:0 0 12px}
  label{display:block;font-size:14px;margin:10px 0 4px}
  input,select,button{width:100%;padding:10px;border:1px solid #000;background:#fff;color:#000;border-radius:6px}
  button{cursor:pointer;font-weight:700}
  .row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
  .mt{margin-top:14px}
  .muted{color:#555;font-size:12px}
  .alert{border:1px solid #000;background:#fff;color:#000;border-radius:8px;padding:10px;margin:10px 0;display:none;white-space:pre-wrap}
  .ok{border:1px solid #000;padding:12px;border-radius:6px;margin-top:14px}
  table{width:100%;border-collapse:collapse;margin-top:10px;table-layout:fixed}
  th,td{border:1px solid #000;padding:6px 8px;text-align:left;font-size:14px;word-break:break-word}
  thead th{background:#f7f7f7}
  .svgwrap{border:1px solid #000;border-radius:8px;overflow:hidden;margin-top:14px}
  #svg svg{max-width:100%;height:auto;display:block}
  @media (max-width:700px){ .row{grid-template-columns:1fr} }
</style>
</head><body>
<div class="box">
  <h2>Carta natal instantánea</h2>
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

  <div class="row">
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
    <div class="muted mt">Tip: deja Ayanamsha vacío si usas Zodiaco Tropical.</div>
  </div>

  <div id="resultado" class="ok" style="display:none">
    <div id="svg" class="svgwrap"></div>
    <div id="tablas"></div>
  </div>
</div>

<script>
(function(){
  // Lee parámetros de la URL del iframe (?lang=ES&theme=classic&geouser=mofeto)
  const params = new URLSearchParams(location.search);
  const LANG  = params.get('lang')  || 'ES';
  const THEME = params.get('theme') || 'classic';
  const GEONAMES_USER = params.get('geouser') || 'mofeto';

  const $ = id => document.getElementById(id);
  const $alert = $('alert'), $out = $('resultado'), $svg = $('svg'), $tabs = $('tablas'), $btn=$('btn-gen');

  function showAlert(t){ $alert.style.display='block'; $alert.textContent=t; }
  function hideAlert(){ $alert.style.display='none'; $alert.textContent=''; }

  function splitDate(d){ const [y,m,day]=(d||'').split('-').map(n=>parseInt(n,10)); return {year:y,month:m,day}; }
  function splitTime(t){ const [h,mi]=(t||'00:00').split(':').map(n=>parseInt(n,10)); return {hour:h,minute:mi}; }
  const ISO2 = {"colombia":"CO","argentina":"AR","chile":"CL","peru":"PE","ecuador":"EC","venezuela":"VE","uruguay":"UY","paraguay":"PY","bolivia":"BO","mexico":"MX","méxico":"MX","españa":"ES","espana":"ES","spain":"ES","portugal":"PT","francia":"FR","france":"FR","italia":"IT","italy":"IT","alemania":"DE","germany":"DE","reino unido":"GB","uk":"GB","inglaterra":"GB","united kingdom":"GB","estados unidos":"US","eeuu":"US","usa":"US","united states":"US","brasil":"BR","brazil":"BR","canadá":"CA","canada":"CA"};
  const norm = s => (s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');

  async function call(path, payload, expectSVG=false){
    const r = await fetch(path, {method:"POST",headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)});
    if(!r.ok){ const txt=await r.text().catch(()=> ""); throw new Error(`HTTP ${r.status}: ${txt}`); }
    const ct=r.headers.get('content-type')||'';
    if(expectSVG){
      const t=await r.text();
      if(t.trim().startsWith('{')){ try{ const j=JSON.parse(t); return j.svg||j.chart||''; }catch{} }
      return t;
    } else if(ct.includes('application/json')) {
      return r.json();
    } else {
      return r.text();
    }
  }

  function tableHTML(head, rows){
    const thead = "<thead><tr>"+head.map(h=>`<th>${h}</th>`).join("")+"</tr></thead>";
    const tbody = "<tbody>"+rows.map(r=>"<tr>"+r.map(c=>`<td>${c??""}</td>`).join("")+"</tr>").join("")+"</tbody>";
    return `<table>${thead}${tbody}</table>`;
  }
  function pickPoints(data){
    if(Array.isArray(data)) return data;
    if(data?.planets && Array.isArray(data.planets)) return data.planets;
    if(data?.planets && typeof data.planets==='object') return Object.values(data.planets);
    if(data?.points) return data.points;
    if(data?.celestial_points) return data.celestial_points;
    return [];
  }
  function pickHouses(data){
    if(data?.houses && Array.isArray(data.houses)) return data.houses;
    if(data?.houses && typeof data.houses==='object') return Object.values(data.houses);
    if(data?.house_cusps) return data.house_cusps;
    return [];
  }
  function signNameFromLon(lon){
    const signs=["Aries","Tauro","Géminis","Cáncer","Leo","Virgo","Libra","Escorpio","Sagitario","Capricornio","Acuario","Piscis"];
    const i=Math.floor((((lon%360)+360)%360)/30); return signs[i]||"";
  }
  function toDegMin(lon){
    const d=((lon%360)+360)%360; const deg=Math.floor(d%30); const min=Math.floor((d%30-deg)*60);
    return `${deg}°${String(min).padStart(2,'0')}'`;
  }

  async function generar(){
    try{
      hideAlert(); $out.style.display='none'; $svg.innerHTML=""; $tabs.innerHTML=""; $btn.disabled=true; $btn.textContent="Calculando…";

      const name = $('inp-name').value.trim()||"Consulta";
      const city = $('inp-city').value.trim();
      const country = $('inp-country').value.trim();
      const {year,month,day} = splitDate($('inp-date').value);
      const {hour,minute} = splitTime($('inp-time').value);
      const house = $('inp-house').value||'P';
      const zodiac = $('inp-zodiac').value||'Tropic';
      const ayan = $('inp-ayanamsha').value||'';

      if(!year||!month||!day){ showAlert('Falta la fecha.'); return; }
      if(!city||!country){ showAlert('Escribe ciudad y país.'); return; }

      const nationCode = ISO2[norm(country)] || null;

      const subject = { year,month,day,hour,minute, city, name, zodiac_type:zodiac, house_system:house, geonames_username:GEONAMES_USER };
      if(nationCode) subject.nation = nationCode;
      if(zodiac==='Sidereal' && ayan) subject.sidereal_mode = ayan;

      // 1) SVG
      const svg = await call('/api/v4/birth-chart', { subject, language: LANG, theme: THEME }, true);
      if(!svg || !svg.includes('<svg')) throw new Error('El servidor no devolvió el SVG.');
      $svg.innerHTML = svg;

      // 2) Datos
      const data = await call('/api/v4/natal-aspects-data', { subject, language: LANG }, false);

      // Tablas ordenadas
      const pts = pickPoints(data).map(p=>{
        const lon = p.longitude ?? p.lon ?? p.longitude_deg ?? (p.ecliptic && p.ecliptic.lon) ?? p.abs_pos ?? 0;
        const house = p.house ?? p.house_number ?? "";
        const name = p.name || p.point || p.id || "";
        return [name, signNameFromLon(lon), toDegMin(lon), house];
      });

      const order = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto","Ascendant","Medium_Coeli","Mean_Node","Mean_South_Node","Chiron","Mean_Lilith"];
      pts.sort((a,b)=> (order.indexOf(a[0])==-1?99:order.indexOf(a[0])) - (order.indexOf(b[0])==-1?99:order.indexOf(b[0])) );

      const hs = pickHouses(data).map((h,i)=>{
        const lon = h.longitude ?? h.lon ?? h.longitude_deg ?? (h.ecliptic && h.ecliptic.lon) ?? h.abs_pos ?? 0;
        const num = h.number ?? h.house ?? (i+1);
        return [num, signNameFromLon(lon), toDegMin(lon)];
      });

      let html="";
      if(pts.length) html += "<h3>Planetas / Puntos</h3>"+tableHTML(["Cuerpo","Signo","Grado","Casa"], pts);
      if(hs.length)  html += "<h3>Casas (cúspides)</h3>"+tableHTML(["Casa","Signo","Grado"], hs);

      const aspects = (data && (data.aspects||data.natal_aspects)) ? (data.aspects||data.natal_aspects) : [];
      if(aspects.length){
        const rowsA = aspects.map(a=>[
          a.type || a.aspect || "",
          a.point_1?.name || a.body_1 || "",
          a.point_2?.name || a.body_2 || "",
          a.orb ?? a.orb_deg ?? ""
        ]);
        html += "<h3>Aspectos</h3>"+tableHTML(["Aspecto","Cuerpo 1","Cuerpo 2","Orbe"], rowsA);
      }

      $tabs.innerHTML = html || "<p class='muted'>Recibí datos, pero no había tablas para mostrar.</p>";
      $out.style.display='block';

    }catch(e){
      showAlert("Error: "+(e?.message||e));
    }finally{
      $btn.disabled=false; $btn.textContent="Generar carta";
    }
  }

  document.getElementById('btn-gen').addEventListener('click', function(ev){ ev.preventDefault(); generar(); });
})();
</script>
</body></html>
"""

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
