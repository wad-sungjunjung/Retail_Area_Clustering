"""행정동 폴리곤 기반 지도 HTML.

 - Rank1/2/3/Union 전환
 - 카테고리별 on/off 필터
 - Popup: 동명 + Top1/2/3
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.visualize.map_builder import CATEGORY_COLORS, CATEGORY_LABEL_KO


def _normalize(s: str) -> str:
    """행정구역 이름 정규화 — 공백·구분자 차이 흡수."""
    if not isinstance(s, str):
        return ""
    return (
        s.replace(" ", "")
         .replace("·", ".")
         .replace(",", ".")
         .replace("세종특별자치시세종시", "세종특별자치시")
         .replace("세종특별자치시세종특별자치시", "세종특별자치시")
    )


def _match_key(sido: str, sigungu: str, eupmyeondong: str) -> str:
    return _normalize(f"{sido} {sigungu} {eupmyeondong}")


def build_area_map(
    classification_path: Path,
    geojson_path: Path,
    out_html: Path,
    simplify_tolerance: float = 0.0005,  # ~50m
    coord_precision: int = 5,
) -> None:
    cls = pd.read_parquet(classification_path)

    # 매칭 key
    cls = cls.copy()
    cls["_key"] = cls.apply(
        lambda r: _match_key(r.sido, r.sigungu, r.eupmyeondong), axis=1
    )
    # 중복 키는 평균 score 사용하지 말고 첫 행 사용
    cls_map = {row._key: row for _, row in cls.iterrows()}

    # GeoJSON 로드 + 단순화
    gdf = gpd.read_file(geojson_path)
    print(f"[area-map] features={len(gdf):,}")
    gdf["geometry"] = gdf["geometry"].simplify(simplify_tolerance, preserve_topology=True)

    # classification 매칭
    matched = 0
    features = []
    for _, row in gdf.iterrows():
        adm_nm = row["adm_nm"]
        props = {"adm_nm": adm_nm}
        cls_row = cls_map.get(_normalize(adm_nm))
        if cls_row is not None:
            matched += 1
            for k in ["sido", "sigungu", "eupmyeondong",
                      "rank1_category", "rank1_score",
                      "rank2_category", "rank2_score",
                      "rank3_category", "rank3_score"]:
                v = cls_row.get(k)
                if isinstance(v, float) and pd.isna(v):
                    v = None
                props[k] = v
        geom = row["geometry"]
        if geom is None or geom.is_empty:
            continue
        geo = json.loads(gpd.GeoSeries([geom]).to_json())["features"][0]["geometry"]
        # coordinate precision 축소
        geo = _round_coords(geo, coord_precision)
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": geo,
        })
    print(f"[area-map] matched classification: {matched:,}/{len(gdf):,}")

    featurecollection = {"type": "FeatureCollection", "features": features}
    geojson_str = json.dumps(featurecollection, ensure_ascii=False)
    print(f"[area-map] geojson payload: {len(geojson_str)/1024/1024:.1f} MB")

    html = _render_html(geojson_str, len(features), matched)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html, encoding="utf-8")
    print(f"[area-map] wrote → {out_html} ({out_html.stat().st_size/1024/1024:.1f} MB)")


def _round_coords(geom: dict, precision: int) -> dict:
    def _r(v):
        if isinstance(v, list):
            return [_r(x) for x in v]
        if isinstance(v, (int, float)):
            return round(v, precision)
        return v
    geom["coordinates"] = _r(geom["coordinates"])
    return geom


def _render_html(geojson_str: str, total_features: int, matched: int) -> str:
    colors_js = json.dumps(CATEGORY_COLORS, ensure_ascii=False)
    labels_js = json.dumps(CATEGORY_LABEL_KO, ensure_ascii=False)

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>전국 읍/면/동 상권 분류 지도</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
  html, body {{ margin:0; padding:0; height:100%; font-family:-apple-system,BlinkMacSystemFont,sans-serif; }}
  #map {{ position:absolute; top:0; bottom:0; left:0; right:0; }}
  .panel {{ position:fixed; z-index:999; background:rgba(255,255,255,.97);
    padding:10px 14px; border-radius:6px; box-shadow:0 2px 8px rgba(0,0,0,.2); font-size:13px; }}
  #controls {{ top:14px; left:14px; min-width:240px; }}
  #legend {{ bottom:20px; left:14px; }}
  #title {{ top:14px; right:14px; max-width:320px; }}
  h3 {{ margin:0 0 8px 0; font-size:14px; }}
  .hint {{ color:#666; font-size:11px; margin-top:6px; }}
  .row {{ margin:4px 0; }}
  .cat-row {{ display:flex; align-items:center; margin:3px 0; font-size:12px; }}
  .sw {{ display:inline-block; width:14px; height:14px; border:1px solid #333; margin-right:6px; flex-shrink:0; }}
  .count {{ color:#888; margin-left:6px; font-size:11px; }}
  .rank-row {{ display:flex; gap:4px; margin-bottom:6px; }}
  .rank-btn {{ flex:1; padding:5px 8px; border:1px solid #999; background:#fff;
    cursor:pointer; border-radius:4px; font-size:12px; }}
  .rank-btn.active {{ background:#1976d2; color:#fff; border-color:#1976d2; }}
  .popup-title {{ font-size:13px; font-weight:600; margin-bottom:4px; }}
  .popup-sub {{ color:#666; margin-bottom:6px; font-size:12px; }}
  .popup-rank {{ font-size:12px; margin:2px 0; }}
  .popup-dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:5px; vertical-align:middle; }}
</style>
</head>
<body>
<div id="map"></div>
<div id="title" class="panel">
  <h3>전국 읍/면/동 상권 분류</h3>
  <div style="color:#666;font-size:11.5px;">
    매칭 {matched:,}/{total_features:,} 동 · v0.3
  </div>
</div>
<div id="controls" class="panel">
  <div class="row"><strong>순위 보기</strong></div>
  <div class="rank-row">
    <button class="rank-btn active" data-mode="rank1">1순위</button>
    <button class="rank-btn" data-mode="rank2">2순위</button>
    <button class="rank-btn" data-mode="rank3">3순위</button>
    <button class="rank-btn" data-mode="union">1~3순위 합</button>
  </div>
  <div class="row" style="margin-top:10px;"><strong>카테고리 필터</strong>
    <span style="color:#888;font-size:11px;">(체크 해제 시 숨김)</span>
  </div>
  <div id="cat-list"></div>
  <div class="hint">"1~3순위 합": 선택한 카테고리가 Top-1/2/3 중 하나라도 포함된 동 표시</div>
</div>
<div id="legend" class="panel">
  <div style="font-weight:600;margin-bottom:4px;">색상 = 현재 순위 카테고리</div>
  <div style="color:#888;font-size:11px;">회색 = 매칭/분류 없음</div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const CATEGORY_COLORS = {colors_js};
const CATEGORY_LABELS = {labels_js};
const GEOJSON = {geojson_str};

const map = L.map('map', {{ preferCanvas: true }}).setView([36.5, 127.8], 7);
L.tileLayer('https://cartodb-basemaps-{{s}}.global.ssl.fastly.net/light_all/{{z}}/{{x}}/{{y}}.png', {{
  maxZoom: 18, attribution: '© OpenStreetMap · © CartoDB'
}}).addTo(map);

let mode = 'rank1';
const enabled = new Set(Object.keys(CATEGORY_COLORS));

function catForFeature(feat, rank) {{
  const p = feat.properties || {{}};
  if (rank === 'rank1') return p.rank1_category;
  if (rank === 'rank2') return p.rank2_category;
  if (rank === 'rank3') return p.rank3_category;
  return null;
}}

function visibleCat(feat) {{
  const p = feat.properties || {{}};
  if (mode === 'union') {{
    // 현재 활성 카테고리가 Top 1/2/3 중 하나라도 있으면 visible (색은 top1 사용)
    const cats = [p.rank1_category, p.rank2_category, p.rank3_category];
    for (const c of cats) if (c && enabled.has(c)) return p.rank1_category || c;
    return null;
  }}
  const c = catForFeature(feat, mode);
  return c && enabled.has(c) ? c : null;
}}

function styleFn(feat) {{
  const cat = visibleCat(feat);
  if (!cat) {{
    return {{ color:'#888', weight:0.3, fillColor:'#eee', fillOpacity:0 }};
  }}
  const color = CATEGORY_COLORS[cat] || '#888';
  return {{ color:'#555', weight:0.4, fillColor:color, fillOpacity:0.65 }};
}}

function popupHtml(p) {{
  const dot = c => `<span class="popup-dot" style="background:${{CATEGORY_COLORS[c]||'#888'}}"></span>`;
  const line = (label, cat, score) => {{
    if (!cat) return `<div class="popup-rank">${{label}} —</div>`;
    return `<div class="popup-rank">${{label}} ${{dot(cat)}} ${{CATEGORY_LABELS[cat]||cat}}
             <span style="color:#999;">(${{cat}})</span>
             <span style="color:#333;">${{score!=null?score.toFixed(2):''}}</span></div>`;
  }};
  return `
    <div class="popup-title">${{p.eupmyeondong||'—'}}</div>
    <div class="popup-sub">${{p.sido||''}} &gt; ${{p.sigungu||''}}</div>
    <div style="border-top:1px solid #ddd; padding-top:5px;">
      ${{line('1위', p.rank1_category, p.rank1_score)}}
      ${{line('2위', p.rank2_category, p.rank2_score)}}
      ${{line('3위', p.rank3_category, p.rank3_score)}}
    </div>`;
}}

const layer = L.geoJSON(GEOJSON, {{
  style: styleFn,
  onEachFeature: (feat, l) => {{
    l.bindPopup(() => popupHtml(feat.properties||{{}}), {{maxWidth:320}});
    l.bindTooltip(feat.properties.eupmyeondong||'', {{sticky:true}});
  }}
}}).addTo(map);

function refresh() {{ layer.setStyle(styleFn); updateCounts(); }}

// rank 버튼
document.querySelectorAll('.rank-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.rank-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    mode = btn.dataset.mode;
    refresh();
  }});
}});

// 카테고리 체크박스
const catList = document.getElementById('cat-list');
const catCounts = {{}};
for (const c of Object.keys(CATEGORY_COLORS)) catCounts[c] = 0;
(GEOJSON.features||[]).forEach(f => {{
  const c = f.properties.rank1_category;
  if (c && catCounts[c]!==undefined) catCounts[c]++;
}});
for (const c of Object.keys(CATEGORY_COLORS)) {{
  const row = document.createElement('div');
  row.className = 'cat-row';
  row.innerHTML = `
    <input type="checkbox" id="cb-${{c}}" checked style="margin-right:6px;">
    <span class="sw" style="background:${{CATEGORY_COLORS[c]}}"></span>
    <label for="cb-${{c}}" style="cursor:pointer;">${{CATEGORY_LABELS[c]||c}}</label>
    <span class="count" id="cnt-${{c}}"></span>`;
  catList.appendChild(row);
  row.querySelector('input').addEventListener('change', e => {{
    if (e.target.checked) enabled.add(c); else enabled.delete(c);
    refresh();
  }});
}}

function updateCounts() {{
  // 현재 mode 기준 동 수
  const cnt = {{}};
  for (const c of Object.keys(CATEGORY_COLORS)) cnt[c] = 0;
  (GEOJSON.features||[]).forEach(f => {{
    const p = f.properties;
    let c;
    if (mode === 'union') {{
      // union 모드에선 rank1_category를 대표로 세움
      c = p.rank1_category;
    }} else if (mode === 'rank1') c = p.rank1_category;
    else if (mode === 'rank2') c = p.rank2_category;
    else if (mode === 'rank3') c = p.rank3_category;
    if (c && cnt[c]!==undefined) cnt[c]++;
  }});
  for (const c of Object.keys(CATEGORY_COLORS)) {{
    const el = document.getElementById(`cnt-${{c}}`);
    if (el) el.textContent = `(${{cnt[c]}})`;
  }}
}}
updateCounts();
</script>
</body>
</html>
"""
