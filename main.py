import argparse

from src.pipeline.run_classification import (
    run_collection,
    run_feature_build,
    run_classification,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Retail Area Clustering pipeline")
    parser.add_argument(
        "stage",
        choices=["collect", "features", "classify", "all"],
        help="실행 단계",
    )
    parser.add_argument("--config", default="config/config.yaml")
    args = parser.parse_args()

    if args.stage in ("collect", "all"):
        run_collection(args.config)
    if args.stage in ("features", "all"):
        run_feature_build(args.config)
    if args.stage in ("classify", "all"):
        run_classification(args.config)


if __name__ == "__main__":
    main()
