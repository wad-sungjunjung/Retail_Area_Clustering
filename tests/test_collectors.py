def test_collectors_importable():
    from src.collectors import (
        KakaoPoiCollector,
        TourApiCollector,
        SmallBusinessCollector,
        FranchiseCollector,
        AptHousingCollector,
        UniversityCollector,
        GuideRestaurantCollector,
    )

    assert all([
        KakaoPoiCollector,
        TourApiCollector,
        SmallBusinessCollector,
        FranchiseCollector,
        AptHousingCollector,
        UniversityCollector,
        GuideRestaurantCollector,
    ])
