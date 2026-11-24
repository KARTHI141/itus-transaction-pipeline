from sqlalchemy import Column, Date, DateTime, Float, Integer, Numeric, String, Text, func

from app.database import Base


class ClientTransaction(Base):
    __tablename__ = "client_transactions"

    id = Column(Integer, primary_key=True)
    transaction_id = Column(String(64), nullable=False)
    transaction_date = Column(Date, nullable=False, index=True)
    client_id = Column(String(64), nullable=False, index=True)
    client_name = Column(String(255), nullable=False)
    fund_type = Column(String(16), nullable=False)
    distributor = Column(String(255), nullable=False, index=True)
    stock_code = Column(String(32), nullable=False)
    stock_name = Column(String(255), nullable=False)
    transaction_type = Column(String(32), nullable=False)
    quantity = Column(Numeric(18, 6), nullable=False)
    price_per_unit = Column(Numeric(18, 6), nullable=False)
    total_value = Column(Numeric(18, 2), nullable=False)
    source_row = Column(Integer, nullable=False)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now())


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issues"

    id = Column(Integer, primary_key=True)
    source_row = Column(Integer, nullable=True)
    problem = Column(Text, nullable=False)
    action_taken = Column(Text, nullable=False)
    severity = Column(String(16), nullable=False)
