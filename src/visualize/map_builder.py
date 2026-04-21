"""전국 동 단위 상권 분류 결과를 Folium 지도 HTML로 렌더링."""
from __future__ import annotations

from pathlib import Path

import folium
from folium.plugins import MarkerCluster, Search
import pandas as pd


CATEGORY_COLORS = {
    "PREMIUM":            "#d4af37",
    "OFFICE_LUNCH":       "#1976d2",
    "NIGHTLIFE_DINING":   "#7b1fa2",
    "FAMILY_RESIDENTIAL": "#43a047",
    "TOURIST_DINING":     "#fb8c00",
    "CAMPUS_CASUAL":      "#00897b",
    "GENERAL":            "#9e9e9e",
}

CATEGORY_LABEL_KO = {
    "PREMIUM":            "고급 외식",
    "OFFICE_LUNCH":       "오피스 점심",
    "NIGHTLIFE_DINING":   "유흥 결합",
    "FAMILY_RESIDENTIAL": "대규모 주거",
    "TOURIST_DINING":     "관광지",
    "CAMPUS_CASUAL":      "대학가 가성비",
    "GENERAL":            "일반 (Fallback)",
}


def _legend_html() -> str:
    items = ""
    for code, color in CATEGORY_COLORS.items():
        label = CATEGORY_LABEL_KO.get(code, code)
        items += (
            f'<div style="margin:4px 0;">'
            f'<span style="display:inline-block;width:14px;height:14px;'
            f'background:{color};border:1px solid #333;margin-right:6px;'
            f'vertical-align:middle;"></span>'
            f'<span style="vertical-align:middle;font-size:12px;">'
            f'{label} <span style="color:#666">({code})</span></span>'
            f"</div>"
        )
    return f"""
    <div id="legend" style="
        position: fixed; bottom: 24px; left: 24px; z-index: 9999;
        background: white; padding: 10px 14px; border: 1px solid #999;
        border-radius: 4px; box-shadow: 0 2px 6px rgba(0,0,0,.2);
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;">
      <div style="font-weight:600;margin-bottom:6px;font-size:13px;">상권 유형</div>
      {items}
    </div>
    """


def _popup_html(row: pd.Series) -> str:
    def _fmt(cat, score):
        if pd.isna(cat) or cat is None:
            return "—"
        color = CATEGORY_COLORS.get(cat, "#888")
        label = CATEGORY_LABEL_KO.get(cat, cat)
        return (f'<span style="color:{color};font-weight:600;">●</span> '
                f'{label} <span style="color:#999;">({cat})</span> '
                f'<span style="color:#333;">{score:.2f}</span>')

    return (
        f'<div style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;'
        f'font-size:12.5px;min-width:230px;">'
        f'<div style="font-weight:600;margin-bottom:4px;">'
        f'{row["sido"]} &gt; {row["sigungu"]}</div>'
        f'<div style="font-size:13px;font-weight:700;margin-bottom:6px;">'
        f'{row["eupmyeondong"]}</div>'
        f'<div style="border-top:1px solid #ddd;padding-top:6px;">'
        f'<div>1위 {_fmt(row["rank1_category"], row["rank1_score"])}</div>'
        f'<div>2위 {_fmt(row["rank2_category"], row["rank2_score"])}</div>'
        f'<div>3위 {_fmt(row["rank3_category"], row["rank3_score"])}</div>'
        f'</div>'
        f'</div>'
    )


def build_map(
    classification_path: Path,
    features_path: Path,
    out_html: Path,
    use_cluster: bool = True,
) -> None:
    cls = pd.read_parquet(classification_path)
    feat = pd.read_parquet(features_path)
    df = cls.merge(
        feat[["sido", "sigungu", "eupmyeondong", "lon", "lat"]],
        on=["sido", "sigungu", "eupmyeondong"], how="left",
    )
    df = df.dropna(subset=["lon", "lat"])

    m = folium.Map(
        location=[36.5, 127.8],  # 대한민국 중심 근처
        zoom_start=7,
        tiles="CartoDB positron",
        control_scale=True,
    )

    # 카테고리별 FeatureGroup (토글 가능)
    groups: dict[str, folium.FeatureGroup] = {}
    categories = sorted(df["rank1_category"].dropna().unique().tolist())
    for cat in categories:
        label = CATEGORY_LABEL_KO.get(cat, cat)
        fg = folium.FeatureGroup(name=f"{label} ({cat})", show=True)
        if use_cluster:
            fg.add_child(MarkerCluster(disableClusteringAtZoom=11))
        groups[cat] = fg
        m.add_child(fg)

    # 마커 추가
    for _, row in df.iterrows():
        cat = row["rank1_category"]
        color = CATEGORY_COLORS.get(cat, "#888")
        popup = folium.Popup(_popup_html(row), max_width=320)
        tip = f"{row['sigungu']} {row['eupmyeondong']} · {cat}"
        marker = folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.75,
            weight=1,
            popup=popup,
            tooltip=tip,
        )
        target = groups.get(cat, m)
        # FeatureGroup 의 첫 자식이 MarkerCluster 면 거기로, 아니면 그룹 직접
        if use_cluster and target is not m and target._children:
            first_child = next(iter(target._children.values()))
            first_child.add_child(marker)
        else:
            target.add_child(marker)

    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(folium.Element(_legend_html()))

    # 타이틀
    title = (
        '<h3 style="position:fixed;top:10px;left:60px;z-index:9999;'
        'background:white;padding:6px 14px;border-radius:4px;'
        'box-shadow:0 2px 6px rgba(0,0,0,.2);font-family:-apple-system,'
        'BlinkMacSystemFont,sans-serif;margin:0;font-size:14px;">'
        '전국 읍/면/동 상권 분류 지도 '
        f'<span style="color:#999;font-weight:400;">({len(df):,} dongs)</span>'
        '</h3>'
    )
    m.get_root().html.add_child(folium.Element(title))

    out_html.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(out_html))
