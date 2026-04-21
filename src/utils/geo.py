from pathlib import Path


def load_admin_boundary(path: Path):
    """국가공간정보포털 읍/면/동 Shapefile 로더."""
    raise NotImplementedError


def region_centroid(gdf):
    """폴리곤 GeoDataFrame → (sido, sigungu, eupmyeondong, lat, lon)."""
    raise NotImplementedError
