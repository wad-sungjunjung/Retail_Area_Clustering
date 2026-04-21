from pathlib import Path
from src.visualize.area_map import build_area_map


if __name__ == "__main__":
    build_area_map(
        classification_path=Path("data/processed/area_commercial_type.parquet"),
        geojson_path=Path("data/raw/boundaries/hangjeongdong.geojson"),
        out_html=Path("data/processed/area_map_polygon.html"),
    )
