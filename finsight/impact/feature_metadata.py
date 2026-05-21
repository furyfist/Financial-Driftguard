"""Domain descriptions for all 17 standard Lending Club features used in FinSight AI."""

from __future__ import annotations

FEATURE_METADATA: dict[str, str] = {
    "int_rate": (
        "Loan interest rate — directly influenced by Fed policy; rises during "
        "rate-hiking cycles and compresses spreads in low-rate regimes."
    ),
    "loan_amnt": (
        "Requested loan amount — sensitive to consumer confidence and credit "
        "availability; shrinks during recessions when borrowers self-ration."
    ),
    "annual_inc": (
        "Borrower's self-reported annual income — deteriorates in recessions as "
        "wage growth stalls and unemployment rises, skewing the income distribution."
    ),
    "dti": (
        "Debt-to-income ratio — sensitive to employment and consumer income trends; "
        "deteriorates in recessions and credit-stress regimes as debt burdens rise."
    ),
    "delinq_2yrs": (
        "Number of delinquencies in the past 2 years — a lagging credit-quality "
        "indicator that spikes during and after recessions or credit-stress episodes."
    ),
    "fico_range_low": (
        "Lower bound of applicant FICO score band — tightens during credit stress "
        "as lenders raise underwriting standards and riskier borrowers exit the market."
    ),
    "inq_last_6mths": (
        "Hard credit inquiries in the last 6 months — rises during rate-shock "
        "regimes as consumers shop for credit before anticipated tightening."
    ),
    "open_acc": (
        "Number of open credit lines — a structural credit-capacity indicator that "
        "shifts slowly; elevated counts correlate with pre-recession credit expansion."
    ),
    "pub_rec": (
        "Number of derogatory public records (bankruptcies, liens) — rises sharply "
        "in recessions and remains elevated for years in the aftermath."
    ),
    "revol_bal": (
        "Total revolving credit balance — expands during consumer credit booms and "
        "compresses rapidly during credit-stress or black-swan events."
    ),
    "revol_util": (
        "Revolving credit utilisation rate — a real-time stress indicator; spikes "
        "during financial distress as consumers draw down available credit lines."
    ),
    "total_acc": (
        "Total number of credit lines ever opened — a historical depth-of-credit "
        "metric; shifts gradually and may reflect vintage bias in loan cohorts."
    ),
    "out_prncp": (
        "Outstanding principal balance — closely linked to prepayment behaviour, "
        "which accelerates in low-rate environments when refinancing is attractive."
    ),
    "total_pymnt": (
        "Total amount paid to date — a loan-seasoning indicator; distribution "
        "shifts as regime changes alter prepayment speeds and default timing."
    ),
    "total_rec_int": (
        "Total interest received — declines when interest rates fall mid-loan or "
        "when prepayments cut short the interest-earning period."
    ),
    "last_pymnt_amnt": (
        "Amount of the most recent payment — sensitive to forbearance programs "
        "and moratoriums introduced during black-swan or recession regimes."
    ),
    "installment": (
        "Monthly payment obligation — mechanically linked to loan_amnt and int_rate; "
        "distribution shifts when origination rate environments change materially."
    ),
}


def get_feature_description(feature_name: str) -> str:
    """Return the domain description for a feature, or a sensible default."""
    return FEATURE_METADATA.get(
        feature_name,
        f"{feature_name} — a lending model input feature whose distribution may shift "
        "with macro regime changes, credit cycles, or data pipeline changes.",
    )
