# Itus Capital Client Transaction Pipeline

A FastAPI and PostgreSQL pipeline for cleaning and reporting on the May-October 2026 client transaction CSV.

## Setup

Python 3.11+ and PostgreSQL 14+ are required.

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Start PostgreSQL locally and create the database:

```sql
CREATE DATABASE itus_transactions;
```

Update `DATABASE_URL` in `.env` if your PostgreSQL credentials differ. The default is:

```text
postgresql+psycopg://postgres:postgres@localhost:5432/itus_transactions
```

Docker is also available:

```powershell
docker compose up -d postgres
python scripts/ingest.py
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for Swagger UI.

Application startup creates tables and re-ingests the CSV automatically. To run ingestion explicitly:

```powershell
python scripts/ingest.py --csv client_transactions_may_oct_2026.csv
python -m pytest
```

## API endpoints

- `GET /api/distributors/summary` — clients, invested value, current portfolio value, and net flows grouped by distributor.
- `GET /api/clients/{client_id}/transactions` — ordered history and running portfolio value.
- `GET /api/data-quality` — source row, problem, action, and severity.
- `GET /api/business/negative-flow-distributors?month=2026-10` — distributors with negative net flows and their redeeming clients. If `month` is omitted, it uses the latest month represented in the cleaned data.

Example:

```powershell
curl "http://127.0.0.1:8000/api/business/negative-flow-distributors?month=2026-10"
```

Standalone October/default latest-month report:

```powershell
python scripts/business_query.py --month 2026-10
python scripts/business_query.py
```

## Schema

### `client_transactions`

One row represents one cleaned transaction. It has a surrogate primary key plus the source `transaction_id`, normalized date, client and distributor details, fund, stock, transaction side, quantity, price, source `total_value`, and source CSV row number.

The transaction table is append-history oriented: every trade remains a separate fact. Distributor and client IDs are indexed because the API filters and aggregates by them. The normalized transaction side is `BUY` or `SELL`, while the source aliases `PURCHASE` and `REDEMPTION` are grouped into the corresponding economic side.

### `data_quality_issues`

This audit table records source row, problem, corrective action, and severity. It intentionally exists separately from cleaned transactions, preserving evidence of data-quality decisions without contaminating facts.

## Cleaning decisions

All decisions below are implemented in `app/pipeline.py`.

1. **Transaction IDs:** the first valid occurrence of a `transaction_id` is retained and later occurrences are skipped. This prevents duplicate facts when the data repeats an identical transaction ID.
2. **Dates:** ISO `YYYY-MM-DD`, dash-delimited `DD-MM-YYYY`, and slash-delimited values are normalized to PostgreSQL `DATE`. For slash values, if only one component exceeds 12 it is unambiguous; otherwise the source convention is interpreted as month/day (`MM/DD/YYYY`). This is the convention used by the other unambiguous US-formatted values.
3. **Missing client IDs:** the source has rows with empty or `NULL` client IDs. They are written to the issue log and skipped because the data cannot be assigned reliably to a client or distributor history.
4. **Missing required fields:** required identity, fund, distributor, stock, and transaction fields are checked. Rows missing them are quarantined rather than guessed.
5. **Numeric values:** quantity, price, and total are parsed as `Decimal` and negative or non-finite values are rejected.
6. **Quantity x price mismatch:** if `quantity * price_per_unit` differs from `total_value` by more than 2 paise, the mismatch is reported. The source `total_value` is retained because it is the transaction's stated economic value; silently replacing it could hide a possible source error.
7. **Transaction types:** `BUY` and `PURCHASE` become purchases; `SELL` and `REDEMPTION` become sales/redemptions. Unknown types are quarantined.
8. **Fund type:** normalized to `PMS` or `AIF`, with unknown values reported.
9. **Duplicate and invalid rows:** only valid, unique transactions are loaded. Every skipped or modified source row is represented in the issue report.

### Portfolio-value meaning

The CSV has no independent market-price or end-of-period holding snapshot. Therefore, "total invested", "net flows", and "running portfolio value" use transaction cash values:

- invested value = purchases
- redemption value = sales/redemptions
- net flow = purchases minus redemptions
- running/current portfolio value = cumulative purchases minus cumulative redemptions

This is a cash-flow approximation, not a mark-to-market valuation.

## Business query

For a requested month, the query sums purchase values and redemption values by distributor and returns distributors whose purchase-minus-redemption result is negative. It separately lists clients who made any sale/redemption in that month.

## Surprises and caveats for the business

- The source mixes four transaction labels (`BUY`, `PURCHASE`, `SELL`, `REDEMPTION`) and several date formats.
- Repeated transaction IDs and missing client IDs require operational attention.
- Because the data has no market prices or opening positions, the API's "current portfolio value" is a net cash-flow balance. It should not be presented as an audited market valuation.
- A meaningful current value would require daily holdings or market prices after the final transaction.

## Production next step

I would add idempotent batch versioning and signed/immutable ledger ingestion, including a batch ID and raw payload hash. This would make reprocessing observable, prevent accidental row replacement, and allow late corrections to follow an audit trail instead of overwriting history.
