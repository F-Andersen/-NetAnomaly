"""Database models for events, predictions and experiment results."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

JsonType = JSON().with_variant(JSONB(), "postgresql")
BigIntId = BigInteger().with_variant(Integer(), "sqlite")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class ModelVersion(Base):
    __tablename__ = "model_versions"

    version: Mapped[str] = mapped_column(String(128), primary_key=True)
    algorithm: Mapped[str] = mapped_column(String(64))
    run_id: Mapped[str] = mapped_column(String(128))
    data_mode: Mapped[str] = mapped_column(String(16))
    threshold: Mapped[float] = mapped_column(Float)
    seed: Mapped[int] = mapped_column(Integer)
    params: Mapped[dict] = mapped_column(JsonType)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class FlowEvent(Base):
    __tablename__ = "flow_events"

    id: Mapped[int] = mapped_column(BigIntId, primary_key=True, autoincrement=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    source: Mapped[str] = mapped_column(String(32))
    src_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    src_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dst_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dst_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    true_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    features: Mapped[dict] = mapped_column(JsonType)

    prediction: Mapped["Prediction"] = relationship(back_populates="event", uselist=False)

    __table_args__ = (Index("ix_flow_events_event_time", "event_time"),)


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(BigIntId, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("flow_events.id", ondelete="CASCADE"), unique=True)
    model_version: Mapped[str] = mapped_column(ForeignKey("model_versions.version"))
    score: Mapped[float] = mapped_column(Float)
    threshold: Mapped[float] = mapped_column(Float)
    is_anomaly: Mapped[bool] = mapped_column(Boolean)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    event: Mapped[FlowEvent] = relationship(back_populates="prediction")

    __table_args__ = (
        Index("ix_predictions_event_time", "event_time"),
        Index("ix_predictions_anomaly", "is_anomaly", "id"),
    )


class ExperimentMetric(Base):
    __tablename__ = "experiment_metrics"

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    model: Mapped[str] = mapped_column(String(64), primary_key=True)
    data_mode: Mapped[str] = mapped_column(String(16))
    n: Mapped[int] = mapped_column(BigIntId)
    n_attack: Mapped[int] = mapped_column(BigIntId)
    n_benign: Mapped[int] = mapped_column(BigIntId)
    tp: Mapped[int] = mapped_column(BigIntId)
    fp: Mapped[int] = mapped_column(BigIntId)
    tn: Mapped[int] = mapped_column(BigIntId)
    fn: Mapped[int] = mapped_column(BigIntId)
    accuracy: Mapped[float] = mapped_column(Float)
    precision: Mapped[float] = mapped_column(Float)
    recall: Mapped[float] = mapped_column(Float)
    f1: Mapped[float] = mapped_column(Float)
    fpr: Mapped[float] = mapped_column(Float)
    pr_auc: Mapped[float] = mapped_column(Float)
    roc_auc: Mapped[float] = mapped_column(Float)
    threshold: Mapped[float] = mapped_column(Float)
    score_seconds: Mapped[float] = mapped_column(Float)
    microseconds_per_record: Mapped[float] = mapped_column(Float)


class ExperimentPerAttack(Base):
    __tablename__ = "experiment_per_attack"

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    model: Mapped[str] = mapped_column(String(64), primary_key=True)
    label: Mapped[str] = mapped_column(String(64), primary_key=True)
    n: Mapped[int] = mapped_column(BigIntId)
    flagged: Mapped[int] = mapped_column(BigIntId)
    flagged_share: Mapped[float] = mapped_column(Float)


def make_engine(url: str) -> Engine:
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        from sqlalchemy.pool import StaticPool

        kwargs = {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
    return create_engine(url, **kwargs)


def make_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)
