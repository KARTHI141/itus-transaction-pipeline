"""Print distributors with negative net flows for a month."""

import argparse

from app.database import Base, engine, SessionLocal
from app.main import app  # noqa: F401 (ensures models are registered)
from app.models import ClientTransaction
from app.main import negative_flow_distributors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", help="YYYY-MM")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        response = negative_flow_distributors(month=args.month, db=db)
    finally:
        db.close()

    print(f"Month: {response['month']}")
    if not response["distributors"]:
        print("No distributors had negative net flows.")
        return
    for item in response["distributors"]:
        print(f"\n{item['distributor']}: net flow {item['net_flow']:,.2f}")
        for client in item["clients_who_redeemed"]:
            print(
                f"  - {client['client_name']} ({client['client_id']}): "
                f"redeemed {client['redeemed_value']:,.2f}"
            )


if __name__ == "__main__":
    main()
