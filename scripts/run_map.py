from pathlib import Path

from src.visualize import build_map


if __name__ == "__main__":
    build_map(
        classification_path=Path("data/processed/area_commercial_type.parquet"),
        features_path=Path("data/processed/area_features.parquet"),
        out_html=Path("data/processed/area_map.html"),
    )
    print("map saved → data/processed/area_map.html")
