from dataclasses import dataclass, field
from datetime import datetime, timezone
import numpy as np
import pandas as pd


@dataclass
class DataSnapshot:
    """
    A window of feature data at a point in time.
    Pass a DataFrame and it extracts numpy arrays per feature.
    """
    label: str                          # "baseline" or "2024-Q1"
    captured_at: datetime =  field(default_factory=lambda: datetime.now(timezone.utc))
    _features: dict[str, np.ndarray] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, label: str) -> "DataSnapshot":
        snap = cls(label=label)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        for col in numeric_cols:
            snap._features[col] = df[col].dropna().to_numpy(dtype=float)
        if numeric_cols:
            min_rows = min(len(snap._features[col]) for col in numeric_cols)
            if min_rows < 100:
                raise ValueError(
                    f"DataSnapshot requires at least 100 rows per feature; "
                    f"got {min_rows} in '{label}'."
                )
        return snap

    def feature_names(self) -> list[str]:
        return list(self._features.keys())

    def get(self, feature_name: str) -> np.ndarray:
        if feature_name not in self._features:
            raise KeyError(f"Feature '{feature_name}' not in snapshot '{self.label}'")
        return self._features[feature_name]

    def __len__(self) -> int:
        return len(self._features)