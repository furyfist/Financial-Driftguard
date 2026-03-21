import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlmodel import Session

from ..store.database import engine, MacroCache
from ..regime.macro_signals import MacroSignalFetcher
from ..regime.tagger import RegimeTagger

load_dotenv()
logger = logging.getLogger(__name__)


def fetch_and_cache_macro():
    """
    Fetches latest macro signals from FRED + Yahoo Finance,
    runs the ML regime classifier, and stores result in MacroCache.

    Called every 6 hours by the scheduler.
    Also called once on server startup.
    """
    fred_key = os.getenv("FRED_API_KEY")
    if not fred_key:
        logger.warning("FRED_API_KEY not set — skipping macro fetch")
        return None

    try:
        fetcher  = MacroSignalFetcher(fred_api_key=fred_key)
        snapshot = fetcher.fetch()

        if not snapshot.is_complete():
            logger.warning(
                f"Incomplete macro snapshot — "
                f"vix={snapshot.vix}, "
                f"spread={snapshot.credit_spread}, "
                f"yield_curve={snapshot.yield_curve}"
            )

        # Run ML regime classifier
        tagger     = RegimeTagger(use_classifier=True)
        dummy_result = _dummy_drift_result()
        assessment = tagger.tag(dummy_result, snapshot)

        logger.info(
            f"Macro snapshot fetched — "
            f"VIX={snapshot.vix}, "
            f"spread={snapshot.credit_spread}, "
            f"yield_curve={snapshot.yield_curve}, "
            f"fed_funds={snapshot.fed_funds_rate} | "
            f"regime={assessment.regime.value} "
            f"(conf={assessment.confidence:.2f})"
        )

        # Persist to MacroCache
        with Session(engine) as session:
            record = MacroCache(
                fetched_at=datetime.now(timezone.utc),
                vix=snapshot.vix,
                credit_spread=snapshot.credit_spread,
                fed_funds_rate=snapshot.fed_funds_rate,
                yield_curve=snapshot.yield_curve,
                unemployment_rate=snapshot.unemployment_rate,
                regime=assessment.regime.value,
                regime_confidence=assessment.confidence,
            )
            session.add(record)
            session.commit()

        return snapshot, assessment

    except Exception as e:
        logger.error(f"Macro fetch failed: {e}", exc_info=True)
        return None


def _dummy_drift_result():
    """
    RegimeTagger.tag() requires a DriftResult to generate recommendations.
    We pass a neutral one for macro-only assessments.
    """
    from ..core.drift_result import DriftResult, DriftSeverity
    from datetime import datetime, timezone
    return DriftResult(
        model_id="__macro__",
        checked_at=datetime.now(timezone.utc),
        feature_results=[],
        overall_severity=DriftSeverity.NONE,
    )