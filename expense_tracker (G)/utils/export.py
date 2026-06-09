"""Export utilities for transactions."""
import io

import pandas as pd


def _records_to_df(records: list[dict]) -> pd.DataFrame:
    """Convert raw transaction records to a clean DataFrame."""
    if not records:
        return pd.DataFrame(
            columns=["id", "type", "amount", "category", "description", "date"]
        )
    df = pd.DataFrame(records)
    df = df[["id", "type", "amount", "category", "description", "date"]]
    df["amount"] = df["amount"].astype(float)
    return df


def to_csv_bytes(records: list[dict]) -> bytes:
    """Convert transaction records to CSV bytes."""
    df = _records_to_df(records)
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def to_excel_bytes(records: list[dict]) -> bytes:
    """Convert transaction records to Excel bytes."""
    df = _records_to_df(records)
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    return buffer.getvalue()
