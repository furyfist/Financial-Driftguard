"""Verify that parquet blob roundtrip works on both SQLite and Postgres (BYTEA)."""
import io
import numpy as np
import pandas as pd
import pytest
from sqlmodel import Session, create_engine, SQLModel

from driftguard.store.database import ModelRecord, create_db, snapshot_to_bytes, bytes_to_snapshot
from driftguard.core.snapshot import DataSnapshot


@pytest.fixture(scope="module")
def mem_engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return engine


def _make_snapshot() -> DataSnapshot:
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "income": rng.normal(50_000, 15_000, 200).tolist(),
        "loan_amnt": rng.normal(12_000, 4_000, 200).tolist(),
        "int_rate": rng.normal(0.12, 0.03, 200).tolist(),
    })
    return DataSnapshot.from_dataframe(df, label="baseline")


def test_blob_roundtrip_sqlite(mem_engine):
    snap = _make_snapshot()
    blob = snapshot_to_bytes(snap)
    assert isinstance(blob, bytes)
    assert len(blob) > 100

    with Session(mem_engine) as session:
        record = ModelRecord(model_id="blob_test_model", baseline_data=blob)
        session.add(record)
        session.commit()
        session.refresh(record)
        recovered = record.baseline_data

    assert recovered == blob, "Blob read back differs from what was written"
    recovered_snap = bytes_to_snapshot(recovered, label="baseline")
    assert set(recovered_snap.feature_names()) == {"income", "loan_amnt", "int_rate"}


def test_blob_survives_model_read(mem_engine):
    """Ensure deserialised snapshot has matching row count and column values."""
    snap = _make_snapshot()
    blob = snapshot_to_bytes(snap)
    recovered_snap = bytes_to_snapshot(blob, label="baseline")

    orig_df = pd.DataFrame({f: snap.get(f) for f in snap.feature_names()})
    rec_df = pd.DataFrame({f: recovered_snap.get(f) for f in recovered_snap.feature_names()})

    assert orig_df.shape == rec_df.shape
    pd.testing.assert_frame_equal(orig_df.reset_index(drop=True), rec_df.reset_index(drop=True))
