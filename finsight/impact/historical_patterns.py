"""Historical context for regime-specific default rate patterns."""

# Brief human-readable context appended to impact summaries.
REGIME_CONTEXT: dict[str, str] = {
    "stable":        "Model operating within normal parameters.",
    "rate_shock":    "Rate shock regimes historically raise prepayment risk, not defaults.",
    "credit_stress": "Credit stress episodes historically widen default rates 1.5–3× baseline.",
    "recession":     "Recessions have historically doubled default rates vs. the stable baseline.",
    "black_swan":    "Black swan events produce tail losses far outside model history — freeze decisions.",
    "unknown":       "Insufficient macro data — apply conservative estimates.",
}
