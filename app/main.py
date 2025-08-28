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
  .row{display:grid;grid-template-columns:1fr 1fr;gap:36px;align-items:start}
  .mt{margin-top:18px}
  .alert{border:1px solid var(--line);background:#fff;color:#000;border-radius:12px;padding:12px;margin:12px 0;display:none;white-space:pre-wrap}
  .ok{border:1px solid var(--line);padding:26px;border-radius:12px;margin-top:18px}
  .ok > * + *{margin-top:18px}
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

  <!-- Sideral oculto (sólo si añades ?sidereal=on) -->
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
  const THEME   = q.get('theme')   || 'light';
  const GEOUSER = q.get('geouser') || 'mofeto';
  const TITLE   = q.get('title')   || 'Tu carta natal';
  const SHOW_SID= (q.get('sidereal') === 'on');
  document.getElementById('titulo').textContent = decodeURIComponent(TITLE||'');
  if(SHOW_SID){ document.getElementById('row-sidereal').style.display='grid'; }

  // ===== Helpers =====
  const $ = id => document.getElementById(id);
  const $alert=$('alert'), $out=$('resultado'), $svg=$('svg'), $tabs=$('tablas'), $btn=$('btn-gen');
  const showAlert = t => { $alert.style.display='block'; $alert.textContent=t; };
  const hideAlert = ()=>{ $alert.style.display='none'; $alert.textContent=''; };

  // ===== Utils =====
  const norm = s => (s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
  const ISO2 = {"colombia":"CO","argentina":"AR","chile":"CL","peru":"PE","ecuador":"EC","venezuela":"VE","uruguay":"UY","paraguay":"PY","bolivia":"BO","mexico":"MX","méxico":"MX","españa":"ES","espana":"ES","spain":"ES","portugal":"PT","francia":"FR","france":"FR","italia":"IT","italy":"IT","alemania":"DE","germany":"DE","reino unido":"GB","uk":"GB","inglaterra":"GB","united kingdom":"GB","estados unidos":"US","eeuu":"US","usa":"US","united states":"US","brasil":"BR","brazil":"BR","canadá":"CA","canada":"CA"};
  const splitDate = d => { const [y,m,day]=(d||'').split('-').map(n=>parseInt(n,10)); return {year:y,month:m,day}; };
  const splitTime = t => { const [h,mi]=(t||'00:00').split(':').map(n=>parseInt(n,10)); return {hour:h,minute:mi}; };
  function clamp360(x){ return ((x%360)+360)%360; }
  function minSepDeg(a,b){ return Math.abs(((a - b + 540) % 360) - 180); } // 0..180
  function fmtDegMin(x){ const d=Math.floor(x), m=Math.round((x-d)*60); const dd=(m===60)?d+1:d; const mm=(m===60)?0:m; return `${dd}°${String(mm).padStart(2,"0")}'`; }

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

  // ===== Signos / grados
  function signFromLon(lon){ const i=Math.floor(clamp360(lon)/30); return ["Aries","Tauro","G\u00e9minis","C\u00e1ncer","Leo","Virgo","Libra","Escorpio","Sagitario","Capricornio","Acuario","Piscis"][i]||""; }
  function degStr(lon){ const d=clamp360(lon); const g=Math.floor(d%30); const m=Math.round((d%30-g)*60); return `${g}°${String(m).padStart(2,'0')}'`; }

  // ===== Aspectos: normalización ES/EN + ángulos
  function sinAcentos(s){ return (s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,""); }
  function aspectKey(raw){
    const k = sinAcentos(String(raw||"")).toLowerCase().replace(/[\s-]+/g,"_");
    const map = {
      conjuncion:"conjunction", oposicion:"opposition", opp:"opposition",
      cuadratura:"square", quartile:"square",
      trigono:"trine", sextil:"sextile",
      quincuncio:"quincunx", inconjuncto:"quincunx", inconjunct:"quincunx",
      semicuadratura:"semisquare", semi_cuadratura:"semisquare", semi_square:"semisquare", semisquare:"semisquare",
      sesquicuadratura:"sesquiquadrate", sesqui_cuadratura:"sesquiquadrate", sesqui_quadrate:"sesquiquadrate",
      semisextil:"semisextile", semi_sextil:"semisextile", semisextile:"semisextile",
      quintil:"quintile", biquintil:"biquintile",
      novil:"novile", binovil:"binovile",
      septil:"septile", biseptil:"biseptile", triseptil:"triseptile",
      undecil:"undecile"
    };
    return map[k] || k;
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

  // ===== Lista aceptada por la API (EXCLUYE True_Node)
  const ORDER = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto","Ascendant","Medium_Coeli","Mean_Node","Mean_South_Node","Chiron","Mean_Lilith"];
  // backends a veces devuelven índices; mapeo 0/1-based y ángulos
  const NUM2CAN = {"0":"Sun","17":"Ascendant","18":"Medium_Coeli","19":"Descendant","20":"Imum_Coeli"};

  const POINT_ES = {
    "Sun":"Sol","Moon":"Luna","Mercury":"Mercurio","Venus":"Venus","Mars":"Marte","Jupiter":"Júpiter","Saturn":"Saturno",
    "Uranus":"Urano","Neptune":"Neptuno","Pluto":"Plutón",
    "Ascendant":"Ascendente","Descendant":"Descendente",
    "Medium_Coeli":"Medio Cielo","Imum_Coeli":"Fondo del Cielo",
    "Mean_Node":"Nodo Norte","Mean_South_Node":"Nodo Sur",
    "Chiron":"Quirón","Mean_Lilith":"Lilith (media)"
  };

  // ===== Lector robusto de longitudes
  function firstFinite(...vals){
    for(const v of vals){
      const n = (typeof v==="object" && v && "decimal" in v) ? v.decimal : v;
      if(n!==undefined && n!==null && Number.isFinite(Number(n))) return Number(n);
    }
    return null;
  }
  function getLon(p){
    return firstFinite(
      p.longitude_deg, p.longitude, p.lon, p.abs_pos,
      p?.ecliptic?.lon, p?.ecliptic?.longitude, p?.ecliptic?.longitude?.deg, p?.ecliptic?.longitude?.degrees, p?.ecliptic?.longitude?.decimal,
      p?.position?.ecliptic?.lon, p?.position?.ecliptic?.longitude, p?.position?.lon
    );
  }

  // ===== Construcción de mapas (alias → canónico) y longitudes; usa casas para ASC/MC/DSC/IC
  function buildPointMaps(points, houses){
    const aliasToCanon = {};
    const lonByCanon   = {};
    const rowsCanon    = [];

    points.forEach((p,enumIdx)=>{
      let raw = p.name || p.point || p.id || p.code || `P${enumIdx+1}`;
      raw = String(raw);
      let canon = ORDER.includes(raw) ? raw : raw;
      if(!ORDER.includes(canon) && ORDER[enumIdx]) canon = ORDER[enumIdx];

      const lon = getLon(p);
      if(lon!=null) lonByCanon[canon] = lon;

      [
        raw, p.id, p.point, p.code, p.symbol, p.name, p.body, p.planet,
        String(enumIdx), String(enumIdx+1),
        String(p.index), String(p.idx), String(p.point_index), String(p.body_index), String(p.global_index), String(p.no)
      ].filter(Boolean).forEach(a => aliasToCanon[String(a).toLowerCase()] = canon);

      rowsCanon.push([canon, lon, p.house ?? p.house_number ?? ""]);
    });

    // Fallback de ángulos desde casas (si no vienen como puntos)
    const getHouseLon = (arr, n) => {
      if(!arr || !arr.length) return null;
      const h = arr.find(hh => (hh.number ?? hh.house) == n) || arr[n-1] || null;
      return h ? getLon(h) : null;
    };
    const lonAsc = getHouseLon(houses,1), lonMc = getHouseLon(houses,10), lonDesc = getHouseLon(houses,7), lonIc = getHouseLon(houses,4);
    if(Number.isFinite(lonAsc)) lonByCanon["Ascendant"] = lonAsc;
    if(Number.isFinite(lonMc )) lonByCanon["Medium_Coeli"] = lonMc;
    if(Number.isFinite(lonDesc)) lonByCanon["Descendant"] = lonDesc;
    if(Number.isFinite(lonIc  )) lonByCanon["Imum_Coeli"] = lonIc;

    // alias numéricos más comunes
    Object.keys(NUM2CAN).forEach(k => aliasToCanon[k]=NUM2CAN[k]);

    // tabla ES (oculta True_Node desde el origen)
    const rowsES = rowsCanon
      .filter(([canon]) => canon !== "True_Node")
      .map(([canon,lon,house])=>[canon, signFromLon(Number(lon||0)), degStr(Number(lon||0)), house])
      .map(([canon,sign,deg,house])=>[(POINT_ES[canon]||canon.replace(/_/g,' ')),sign,deg,house]);

    return { aliasToCanon, lonByCanon, rowsES };
  }

  function toCanon(x, maps){
    if(x==null) return "";
    const s = String(x).trim();
    const k = s.toLowerCase();
    if(NUM2CAN[s]) return NUM2CAN[s]; // índices especiales y 0-based
    if(/^\d+$/.test(s)){
      const n = parseInt(s,10);
      if(n>=0 && n < ORDER.length) return ORDER[n];     // 0-based
      if(n>=1 && n <= ORDER.length) return ORDER[n-1];  // 1-based
    }
    return maps.aliasToCanon[k] || k;
  }
  const toES = canon => POINT_ES[canon] || canon.replace(/_/g,' ');

  // ================== GENERAR ==================
  async function generar(){
    try{
      hideAlert(); $out.style.display='none'; $svg.innerHTML=""; $tabs.innerHTML=""; $btn.disabled=true; $btn.textContent="Calculando…";

      const name=$('inp-name').value.trim()||"Consulta";
      const city=$('inp-city').value.trim();
      const country=$('inp-country').value.trim();
      const {year,month,day}=splitDate($('inp-date').value);
      const {hour,minute}=splitTime($('inp-time').value);
      const house=$('inp-house').value||'P';
      const zodiac= (document.getElementById('row-sidereal').style.display==='grid') ? ($('inp-zodiac').value||'Tropic') : 'Tropic';
      const ayan  = (zodiac==='Sidereal') ? ($('inp-ayanamsha').value||'') : '';

      if(!year||!month||!day){ showAlert('Falta la fecha.'); return; }
      if(!city||!country){ showAlert('Escribe ciudad y país.'); return; }
      const code = ISO2[norm(country)] || null;

      const subject={year,month,day,hour,minute,city,name,zodiac_type:zodiac,house_system:house,geonames_username:GEOUSER};
      if(code) subject.nation=code;
      if(zodiac==='Sidereal' && ayan) subject.sidereal_mode=ayan;

      // Lista exacta aceptada por la API (sin True_Node)
      const active_points=[...ORDER];

      // 1) SVG
      const svg = await call('/api/v4/birth-chart',{ subject, language:LANG, theme:THEME, style:THEME, chart_theme:THEME, active_points },true);
      if(!svg || !svg.includes('<svg')) throw new Error('El servidor no devolvió el SVG.');
      $svg.innerHTML=svg;

      // 2) Datos
      const data = await call('/api/v4/natal-aspects-data',{ subject, language:LANG, active_points },false);

      // --- Preparar puntos y casas
      const ptsRaw = Array.isArray(data) ? data :
                     (data?.planets && Array.isArray(data.planets)) ? data.planets :
                     (data?.points) ? data.points :
                     (data?.celestial_points) ? data.celestial_points :
                     (data?.planets && typeof data.planets==='object') ? Object.values(data.planets) : [];

      const hsRaw = (data?.houses && Array.isArray(data.houses)) ? data.houses :
                    (data?.houses && typeof data.houses==='object') ? Object.values(data.houses) :
                    (data?.house_cusps) ? data.house_cusps : [];

      const maps = buildPointMaps(ptsRaw, hsRaw);

      // Tabla de puntos
      let html="";
      if(maps.rowsES.length){
        const thead = "<thead><tr><th>Cuerpo</th><th>Signo</th><th>Grado</th><th>Casa</th></tr></thead>";
        const tbody = "<tbody>"+maps.rowsES.map(r=>"<tr>"+r.map(c=>`<td>${(c??"")||"—"}</td>`).join("")+"</tr>").join("")+"</tbody>";
        html += `<h3>Planetas / Puntos</h3><table>${thead}${tbody}</table>`;
      }

      // Casas
      if(hsRaw.length){
        const hs = hsRaw.map((h,i)=>{
          const lon = getLon(h) ?? 0;
          const num = h.number ?? h.house ?? (i+1);
          return [num, signFromLon(lon), degStr(lon)];
        });
        const head = "<thead><tr><th>Casa</th><th>Signo</th><th>Grado</th></tr></thead>";
        const body = "<tbody>"+hs.map(r=>"<tr>"+r.map(c=>`<td>${(c??"")||"—"}</td>`).join("")+"</tr>").join("")+"</tbody>";
        html += `<h3>Casas (cúspides)</h3><table>${head}${body}</table>`;
      }

      // Aspectos → normalizar claves, filtrar True_Node y CALCULAR ORBE SIEMPRE
      const aspects = (data && (data.aspects||data.natal_aspects)) ? (data.aspects||data.natal_aspects) : [];
      if(aspects.length){
        const rowsA = aspects.map(a=>{
          const tRaw = (a.type || a.aspect || a.kind || "").toString().trim();
          const key  = aspectKey(tRaw);                      // ES/EN → clave canónica
          const label= ASPECTO_ES[key] || (tRaw? tRaw.charAt(0).toUpperCase()+tRaw.slice(1):"");
          const target = ASPECT_ANGLE[key];

          const cand1 = a.point_1??a.body_1??a.point1??a.a??a.p1??a.obj1??a.object1??a.planet1??a.c1??a.first??a["1"]??a.from??a.name1??a.p1_name??a.index1??a.idx1??a.i1??a.body1_index??a.point1_index??a.global_index1??a.no1;
          const cand2 = a.point_2??a.body_2??a.point2??a.b??a.p2??a.obj2??a.object2??a.planet2??a.c2??a.second??a["2"]??a.to??a.name2??a.p2_name??a.index2??a.idx2??a.i2??a.body2_index??a.point2_index??a.global_index2??a.no2;

          const canon1 = toCanon(cand1, maps);
          const canon2 = toCanon(cand2, maps);
          if(canon1==="True_Node" || canon2==="True_Node") return null; // excluir

          const disp1  = toES(canon1);
          const disp2  = toES(canon2);

          // separación real: uso la del backend si viene; si no, la calculo con longitudes
          const l1 = maps.lonByCanon[canon1], l2 = maps.lonByCanon[canon2];
          const sepField = Number(a.separation ?? a.sep ?? a.sep_deg ?? a.angle ?? a.angle_deg ?? a.aspect_angle);
          const sep = Number.isFinite(sepField) ? Math.abs(sepField)
                    : (Number.isFinite(l1) && Number.isFinite(l2) ? minSepDeg(l1,l2) : NaN);

          // ORBE = |sep − target| (ignoramos cualquier "orb"/"delta" del backend)
          const orb = (Number.isFinite(sep) && Number.isFinite(target))
            ? fmtDegMin(Math.abs(sep - target))
            : "—";

          return [label || "—", disp1 || "—", disp2 || "—", orb];
        }).filter(Boolean);

        const head = "<thead><tr><th>Aspecto</th><th>Cuerpo 1</th><th>Cuerpo 2</th><th>Orbe</th></tr></thead>";
        const body = "<tbody>"+rowsA.map(r=>"<tr>"+r.map(c=>`<td>${(c??"")||"—"}</td>`).join("")+"</tr>").join("")+"</tbody>";
        html += `<h3>Aspectos</h3><table>${head}${body}</table>`;
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
