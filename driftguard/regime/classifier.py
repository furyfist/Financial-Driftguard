import json
import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder

from .features import build_features
from .labeller import RegimeLabeller
from .tagger import Regime

logger = logging.getLogger(__name__)

_MODEL_PATH  = Path("demo/data/regime_classifier.pkl")
_ENCODER_PATH = Path("demo/data/regime_label_encoder.json")

# Regime class order — consistent across train/predict
_REGIME_CLASSES = [
    Regime.STABLE.value,
    Regime.CREDIT_STRESS.value,
    Regime.RATE_SHOCK.value,
    Regime.RECESSION.value,
    Regime.BLACK_SWAN.value,
]


class RegimeClassifier:
    """
    LightGBM multi-class classifier trained on 30 years of
    labelled macro history.

    Training uses walk-forward validation — never sees future data.
    The key validation test: trained on 1990-2019, must correctly
    identify 2020 COVID crash as black_swan without ever seeing it.
    """

    def __init__(self):
        self.model: Optional[LGBMClassifier] = None
        self.label_encoder = LabelEncoder()
        self.label_encoder.classes_ = np.array(_REGIME_CLASSES)
        self.feature_cols: list[str] = []

    def train(
        self,
        labelled_df: pd.DataFrame,
        train_end: str = "2019-12-31",
        verbose: bool = True,
    ) -> dict:
        """
        Train on data up to train_end, validate on everything after.
        This is the walk-forward split — no data leakage possible.

        Returns dict of validation metrics.
        """
        features_df = build_features(labelled_df)

        # Align labels — drop rows lost in feature warmup
        labels = labelled_df["regime"].reindex(features_df.index)

        # Walk-forward split on date
        train_mask = features_df.index <= pd.Timestamp(train_end)
        val_mask   = features_df.index >  pd.Timestamp(train_end)

        X_train = features_df[train_mask]
        y_train = labels[train_mask]
        X_val   = features_df[val_mask]
        y_val   = labels[val_mask]

        self.feature_cols = list(X_train.columns)

        if verbose:
            logger.info(f"Train: {len(X_train):,} days  ({X_train.index[0].date()} → {X_train.index[-1].date()})")
            logger.info(f"Val:   {len(X_val):,} days  ({X_val.index[0].date()} → {X_val.index[-1].date()})")
            logger.info(f"Train class distribution:\n{y_train.value_counts().to_string()}")

        # Encode labels
        y_train_enc = self.label_encoder.transform(y_train)
        y_val_enc   = self.label_encoder.transform(y_val)

        # Class weights — inverse frequency to handle imbalance
        # black_swan and recession are rare but critical to detect
        class_counts = y_train.value_counts()
        total        = len(y_train)
        class_weight = {
            self.label_encoder.transform([c])[0]: total / (len(_REGIME_CLASSES) * class_counts.get(c, 1))
            for c in _REGIME_CLASSES
        }

        # Boost weight for rare but critical classes
        bs_idx  = self.label_encoder.transform([Regime.BLACK_SWAN.value])[0]
        rec_idx = self.label_encoder.transform([Regime.RECESSION.value])[0]
        class_weight[bs_idx]  *= 3.0   # black_swan: 3x boost
        class_weight[rec_idx] *= 2.0   # recession:  2x boost

        if verbose:
            logger.info(f"Class weights: {class_weight}")

        self.model = LGBMClassifier(
            n_estimators=500,
            learning_rate=0.05,
            max_depth=6,
            num_leaves=63,
            min_child_samples=20,
            colsample_bytree=0.8,
            subsample=0.8,
            subsample_freq=1,
            class_weight=class_weight,
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )

        self.model.fit(
            X_train, y_train_enc,
            eval_set=[(X_val, y_val_enc)],
            callbacks=[],
        )

        # Validation metrics
        y_pred_enc = self.model.predict(X_val)
        y_pred     = self.label_encoder.inverse_transform(y_pred_enc)

        report = classification_report(
            y_val, y_pred,
            labels=_REGIME_CLASSES,
            output_dict=True,
            zero_division=0,
        )

        cm = confusion_matrix(
            y_val, y_pred,
            labels=_REGIME_CLASSES,
        )

        if verbose:
            logger.info(f"\nValidation classification report:")
            print(classification_report(
                y_val, y_pred,
                labels=_REGIME_CLASSES,
                zero_division=0,
            ))
            logger.info(f"Confusion matrix (rows=actual, cols=predicted):")
            cm_df = pd.DataFrame(cm, index=_REGIME_CLASSES, columns=_REGIME_CLASSES)
            print(cm_df.to_string())

        return {
            "report":           report,
            "confusion_matrix": cm.tolist(),
            "val_size":         len(X_val),
            "train_size":       len(X_train),
        }

    def predict(self, macro_snapshot) -> tuple[str, float, dict[str, float]]:
        """
        Predict regime from a MacroSnapshot.
        Returns (regime_label, confidence, probabilities_per_class).
        """
        if self.model is None:
            raise RuntimeError("Model not trained — call train() or load() first")

        row = {
            "vix":           macro_snapshot.vix              or 20.0,
            "credit_spread": macro_snapshot.credit_spread    or 2.5,
            "yield_curve":   macro_snapshot.yield_curve      or 0.5,
            "fed_funds":     macro_snapshot.fed_funds_rate   or 2.0,
            "unemployment":  macro_snapshot.unemployment_rate or 4.5,
        }

        # Repeat the snapshot enough times to satisfy the 63-day rolling warmup
        # Use integer index — no business day calendar mismatch
        n_rows = 100
        df_input = pd.DataFrame([row] * n_rows)

        # Assign a proper datetime index after construction
        # Use consecutive calendar days — no weekend skipping issue
        df_input.index = pd.date_range(
            end=pd.Timestamp.today().normalize(),
            periods=n_rows,
            freq="D",       # calendar days, not business days
        )

        features = build_features(df_input)
        if features.empty:
            logger.warning("Feature engineering produced empty output — using fallback")
            return Regime.UNKNOWN.value, 0.0, {}

        # Align feature columns to training order
        X = features[self.feature_cols].iloc[[-1]]

        proba = self.model.predict_proba(X)[0]

        proba_dict = {
            cls: round(float(p), 4)
            for cls, p in zip(_REGIME_CLASSES, proba)
        }

        predicted_idx   = int(np.argmax(proba))
        predicted_label = _REGIME_CLASSES[predicted_idx]
        confidence      = round(float(proba[predicted_idx]), 4)

        return predicted_label, confidence, proba_dict

    def feature_importance(self, top_n: int = 15) -> pd.DataFrame:
        if self.model is None:
            raise RuntimeError("Model not trained")
        importance = pd.DataFrame({
            "feature":    self.feature_cols,
            "importance": self.model.feature_importances_,
        }).sort_values("importance", ascending=False)
        return importance.head(top_n)

    def save(
        self,
        model_path:   str | Path = _MODEL_PATH,
        encoder_path: str | Path = _ENCODER_PATH,
    ):
        import pickle
        with open(model_path, "wb") as f:
            pickle.dump({
                "model":        self.model,
                "feature_cols": self.feature_cols,
            }, f)
        with open(encoder_path, "w") as f:
            json.dump({"classes": _REGIME_CLASSES}, f)
        logger.info(f"Classifier saved to {model_path}")

    @classmethod
    def load(
        cls,
        model_path:   str | Path = _MODEL_PATH,
        encoder_path: str | Path = _ENCODER_PATH,
    ) -> "RegimeClassifier":
        import pickle
        instance = cls()
        with open(model_path, "rb") as f:
            data = pickle.load(f)
        instance.model        = data["model"]
        instance.feature_cols = data["feature_cols"]
        logger.info(f"Classifier loaded from {model_path}")
        return instance