import argparse

from app.database import Base, engine
from app.pipeline import ingest_csv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", dest="csv_path", help="Path to the source CSV")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    result = ingest_csv(csv_path=args.csv_path)
    print(
        f"Loaded {result['loaded_rows']} of {result['source_rows']} source rows "
        f"and recorded {result['issue_count']} data-quality issues."
    )


if __name__ == "__main__":
    main()
