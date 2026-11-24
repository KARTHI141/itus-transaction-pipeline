from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import ClientTransaction, DataQualityIssue
from app.pipeline import ingest_csv


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ingest_csv()
    yield


app = FastAPI(
    title="Itus Capital Client Transaction API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/distributors/summary")
def distributor_summary(db: Session = Depends(get_db)):
    sign = case(
        (ClientTransaction.transaction_type == "BUY", ClientTransaction.total_value),
        else_= -ClientTransaction.total_value,
    )
    gross = case(
        (ClientTransaction.transaction_type == "BUY", ClientTransaction.total_value),
        else_= 0,
    )
    redemption = case(
        (ClientTransaction.transaction_type == "SELL", ClientTransaction.total_value),
        else_= 0,
    )

    rows = db.execute(
        select(
            ClientTransaction.distributor,
            func.count(func.distinct(ClientTransaction.client_id)),
            func.sum(gross),
            func.sum(sign),
            func.sum(gross) - func.sum(redemption),
        )
        .group_by(ClientTransaction.distributor)
        .order_by(ClientTransaction.distributor)
    ).all()

    return [
        {
            "distributor": distributor,
            "client_count": client_count,
            "total_invested_value": float(invested or 0),
            "total_current_value": float(current or 0),
            "net_flows": float(net or 0),
        }
        for distributor, client_count, invested, current, net in rows
    ]


@app.get("/api/clients/{client_id}/transactions")
def client_history(client_id: str, db: Session = Depends(get_db)):
    rows = db.execute(
        select(ClientTransaction)
        .where(ClientTransaction.client_id == client_id)
        .order_by(ClientTransaction.transaction_date, ClientTransaction.id)
    ).scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail="Client not found")

    running = Decimal("0")
    history = []
    for row in rows:
        total = Decimal(row.total_value)
        running += total if row.transaction_type == "BUY" else -total
        history.append({
            "transaction_id": row.transaction_id,
            "date": row.transaction_date.isoformat(),
            "fund_type": row.fund_type,
            "distributor": row.distributor,
            "stock_code": row.stock_code,
            "stock_name": row.stock_name,
            "transaction_type": row.transaction_type,
            "quantity": float(row.quantity),
            "price_per_unit": float(row.price_per_unit),
            "total_value": float(row.total_value),
            "running_portfolio_value": float(running),
        })
    return {"client_id": client_id, "client_name": rows[0].client_name, "transactions": history}


@app.get("/api/data-quality")
def data_quality(db: Session = Depends(get_db)):
    rows = db.execute(
        select(DataQualityIssue).order_by(DataQualityIssue.source_row, DataQualityIssue.id)
    ).scalars().all()
    return [
        {
            "row_number": row.source_row,
            "problem": row.problem,
            "action_taken": row.action_taken,
            "severity": row.severity,
        }
        for row in rows
    ]


@app.get("/api/business/negative-flow-distributors")
def negative_flow_distributors(
    month: str | None = Query(default=None, description="YYYY-MM; defaults to latest month"),
    db: Session = Depends(get_db),
):
    if month:
        try:
            year, month_number = (int(p) for p in month.split("-"))
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Month must use YYYY-MM")
        if month_number < 1 or month_number > 12:
            raise HTTPException(status_code=400, detail="Month must use YYYY-MM")
    else:
        latest = db.execute(select(func.max(ClientTransaction.transaction_date))).scalar()
        if latest is None:
            return {"month": None, "distributors": []}
        year, month_number = latest.year, latest.month

    from datetime import date
    start = date(year, month_number, 1)
    if month_number == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month_number + 1, 1)

    gross = case(
        (ClientTransaction.transaction_type == "BUY", ClientTransaction.total_value),
        else_= 0,
    )
    redemption = case(
        (ClientTransaction.transaction_type == "SELL", ClientTransaction.total_value),
        else_= 0,
    )
    distributors = db.execute(
        select(
            ClientTransaction.distributor,
            func.sum(gross) - func.sum(redemption),
        )
        .where(ClientTransaction.transaction_date >= start,
               ClientTransaction.transaction_date < end)
        .group_by(ClientTransaction.distributor)
        .having(func.sum(gross) - func.sum(redemption) < 0)
        .order_by(ClientTransaction.distributor)
    ).all()

    result = []
    for distributor, net_flow in distributors:
        redeemed = db.execute(
            select(
                ClientTransaction.client_id,
                ClientTransaction.client_name,
                func.sum(ClientTransaction.total_value),
            )
            .where(
                ClientTransaction.distributor == distributor,
                ClientTransaction.transaction_type == "SELL",
                ClientTransaction.transaction_date >= start,
                ClientTransaction.transaction_date < end,
            )
            .group_by(ClientTransaction.client_id, ClientTransaction.client_name)
            .order_by(ClientTransaction.client_name)
        ).all()
        result.append({
            "distributor": distributor,
            "net_flow": float(net_flow),
            "clients_who_redeemed": [
                {
                    "client_id": client_id,
                    "client_name": client_name,
                    "redeemed_value": float(redeemed_value),
                }
                for client_id, client_name, redeemed_value in redeemed
            ],
        })

    return {"month": f"{year:04d}-{month_number:02d}", "distributors": result}
