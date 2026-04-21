import importlib

FEATURE_MODULES = [
    "src.features.premium",
    "src.features.date_trendy",
    "src.features.office_lunch",
    "src.features.nightlife",
    "src.features.family_residential",
    "src.features.tourist",
    "src.features.campus",
    "src.features.market_street",
]


def test_feature_modules_expose_build():
    for name in FEATURE_MODULES:
        mod = importlib.import_module(name)
        assert hasattr(mod, "build"), f"{name} must define build(ctx)"
