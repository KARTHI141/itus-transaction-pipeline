import csv
import os
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import delete

from app.database import SessionLocal
from app.models import ClientTransaction, DataQualityIssue

MISSING_VALUES = {"", "null", "n/a", "na", "none"}


def clean_text(value):
    value = (value or "").strip()
    return None if value.lower() in MISSING_VALUES else value


def parse_date(value):
    value = (value or "").strip()
    if not value:
        raise ValueError("missing date")

    if "-" in value:
        parts = value.split("-")
        if len(parts[0]) == 4:
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
        if len(parts[2]) == 4:
            return date(int(parts[2]), int(parts[1]), int(parts[0]))

    if "/" in value:
        parts = [int(p) for p in value.split("/")]
        first, second, year = parts
        if first > 12:
            return date(year, second, first)
        if second > 12:
            return date(year, first, second)
        # Slash-delimited values with two <=12 values are ambiguous.
        # The source convention is US month/day for this CSV.
        return date(year, first, second)

    raise ValueError(f"unrecognized date format: {value}")


def parse_decimal(value, field):
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, AttributeError):
        raise ValueError(f"invalid {field}: {value}")
    if not parsed.is_finite():
        raise ValueError(f"invalid {field}: {value}")
    return parsed


def ingest_csv(csv_path=None, replace=True):
    csv_path = Path(csv_path or os.getenv("CSV_PATH", "client_transactions_may_oct_2026.csv"))
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    issues = []
    cleaned = []
    seen_transactions = set()
    source_rows = 0

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for source_row, raw in enumerate(reader, start=2):
            source_rows += 1
            transaction_id = clean_text(raw.get("transaction_id"))
            if not transaction_id:
                issues.append((source_row, "Missing transaction ID", "Skipped row", "error"))
                continue

            if transaction_id in seen_transactions:
                issues.append((source_row, f"Duplicate transaction ID {transaction_id}",
                               "Skipped duplicate; retained first occurrence", "warning"))
                continue

            try:
                transaction_date = parse_date(raw.get("date"))
            except (ValueError, TypeError) as exc:
                issues.append((source_row, str(exc), "Skipped row", "error"))
                continue

            client_id = clean_text(raw.get("client_id"))
            if not client_id:
                issues.append((source_row, "Missing client ID",
                               "Skipped row because it cannot be assigned to a client", "error"))
                continue

            required = {
                "client_name": clean_text(raw.get("client_name")),
                "fund_type": clean_text(raw.get("fund_type")),
                "distributor": clean_text(raw.get("distributor")),
                "stock_code": clean_text(raw.get("stock_code")),
                "stock_name": clean_text(raw.get("stock_name")),
                "transaction_type": clean_text(raw.get("transaction_type")),
            }
            missing_fields = [name for name, value in required.items() if value is None]
            if missing_fields:
                issues.append((source_row, f"Missing required field(s): {', '.join(missing_fields)}",
                               "Skipped row", "error"))
                continue

            try:
                quantity = parse_decimal(raw.get("quantity"), "quantity")
                price = parse_decimal(raw.get("price_per_unit"), "price_per_unit")
                total = parse_decimal(raw.get("total_value"), "total_value")
            except ValueError as exc:
                issues.append((source_row, str(exc), "Skipped row", "error"))
                continue

            if quantity < 0 or price < 0 or total < 0:
                issues.append((source_row, "Negative quantity, price, or total value",
                               "Skipped row", "error"))
                continue

            expected = quantity * price
            if abs(expected - total) > Decimal("0.02"):
                issues.append((source_row,
                               f"Value mismatch: quantity x price = {expected:.2f}; total_value = {total:.2f}",
                               "Retained row and stored source total_value", "warning"))

            fund_type = required["fund_type"].upper()
            if fund_type not in {"PMS", "AIF"}:
                issues.append((source_row, f"Unknown fund type {fund_type}",
                               "Retained row using original normalized value", "warning"))

            transaction_type = required["transaction_type"].upper()
            aliases = {"BUY": "BUY", "PURCHASE": "BUY", "SELL": "SELL", "REDEMPTION": "SELL"}
            if transaction_type not in aliases:
                issues.append((source_row, f"Unknown transaction type {transaction_type}",
                               "Skipped row", "error"))
                continue

            seen_transactions.add(transaction_id)
            cleaned.append(ClientTransaction(
                transaction_id=transaction_id,
                transaction_date=transaction_date,
                client_id=client_id,
                client_name=required["client_name"],
                fund_type=fund_type,
                distributor=required["distributor"].strip(),
                stock_code=required["stock_code"].upper(),
                stock_name=required["stock_name"],
                transaction_type=aliases[transaction_type],
                quantity=quantity,
                price_per_unit=price,
                total_value=total,
                source_row=source_row,
            ))

    db = SessionLocal()
    try:
        if replace:
            db.execute(delete(ClientTransaction))
            db.execute(delete(DataQualityIssue))
            db.add_all(cleaned)
            db.add_all([
                DataQualityIssue(source_row=row, problem=problem,
                                 action_taken=action, severity=severity)
                for row, problem, action, severity in issues
            ])
            db.commit()
        return {"source_rows": source_rows,
                "loaded_rows": len(cleaned), "issue_count": len(issues)}
    finally:
        db.close()
