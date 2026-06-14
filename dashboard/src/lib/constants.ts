export const SITE_NAME = "Financial DriftGuard"

export const NAV = {
  wordmark: "Financial DriftGuard",
  github: "https://github.com/himanshuraimau/financial-driftguard",
  cta: "Open Dashboard →",
  ctaHref: "/dashboard",
  demoHref: "#demo",
}

export const HERO = {
  headline1: "Your model drifted.",
  headline2: "Is the market broken,",
  headline3: "or is your model?",
  subtext:
    "Financial DriftGuard is the only governance agent that separates regime-driven drift from real model decay — and takes the right action on each.",
  ctaPrimary: "See it run live",
  ctaSecondary: "Read the docs →",
  stats: ["93.9% accuracy", "30yr macro data", "COVID caught at 1.000"],
  regimes: [
    { label: "stable",        color: "teal" },
    { label: "credit_stress", color: "amber" },
    { label: "black_swan",    color: "red" },
  ],
}

export const PROBLEM = {
  eyebrow: "SECTION 02 — THE PROBLEM",
  heading: "Every monitoring tool treats drift the same. That's the wrong call.",
  leftCard: {
    title: "What happens now",
    body: "Drift fires.\nYou get paged.\nTool says retrain.",
  },
  rightCard: {
    title: "What that costs",
    body: "You retrain a model that didn't need retraining.",
  },
  pullQuote:
    "The 2017–2018 Fed hiking cycle raised int_rate. PSI fired. Every tool said: retrain. Financial DriftGuard said: don't. The market was the variable.",
}

export const HOW_IT_WORKS = {
  eyebrow: "SECTION 03 — HOW IT WORKS",
  heading: "Four steps. One decision.",
  steps: [
    {
      num: "01",
      title: "Detects drift",
      body: "PSI + KS + JS divergence across all features, continuously.",
    },
    {
      num: "02",
      title: "Reads the macro",
      body: "Live VIX, credit spreads, yield curve, fed funds — refreshed every 6h from FRED.",
    },
    {
      num: "03",
      title: "Classifies the regime",
      body: "LightGBM on 30 years of NBER history. Stable. Credit stress. Black swan. Rate shock.",
    },
    {
      num: "04",
      title: "Takes the right action",
      body: "Macro drift? Hold. Model decay? Retrain. Black swan? HALT everything.",
    },
  ],
}

export const DEMO = {
  eyebrow: "SECTION 04 — SEE IT RUN",
  heading: "Three real scenarios.\nOne click each.",
  scenarios: [
    {
      id: "rate_hike",
      tag: "credit_stress",
      tagColor: "amber",
      title: "Rate Hike 2017",
      meta: "Q4 2018 peak · VIX=25",
      output: [
        "$ POST /demo/scenarios/rate_hike",
        "> drift: 0.0493  severity: HIGH",
        "> regime: credit_stress  confidence: 0.91",
        "> action: MONITOR — do not retrain",
      ],
    },
    {
      id: "covid",
      tag: "black_swan",
      tagColor: "red",
      title: "COVID Crash",
      meta: "March 2020 · VIX=57.1",
      output: [
        "$ POST /demo/scenarios/covid",
        "> drift: 0.0754  severity: CRITICAL",
        "> regime: black_swan  confidence: 0.99",
        "> action: HALT — freeze all automated decisions",
      ],
    },
    {
      id: "normal",
      tag: "stable",
      tagColor: "teal",
      title: "Normal Decay",
      meta: "Stable macro · Live signals",
      output: [
        "$ POST /demo/scenarios/normal",
        "> drift: 0.0368  severity: HIGH",
        "> regime: stable  confidence: 0.87",
        "> action: INVESTIGATE AND RETRAIN",
      ],
    },
  ],
}

export const PROOF = {
  eyebrow: "SECTION 05 — PROOF",
  heading: "Real numbers from the build.",
  stats: [
    { value: 93.9, suffix: "%", label: "Regime classifier walk-fwd accuracy", decimals: 1 },
    { value: 1.0,  suffix: "",  label: "COVID black swan confidence at 1.000", decimals: 3 },
    { value: 30,   suffix: "",  label: "Years of NBER macro training history", decimals: 0 },
    { value: 26.6, suffix: "s", label: "Full demo: 3 scenarios end-to-end",    decimals: 1 },
  ],
}

export const STACK = {
  eyebrow: "SECTION 06 — BUILT WITH",
  oneliner: "No frameworks were harmed.",
  pills: [
    "FastAPI", "LightGBM", "Arize Phoenix", "Groq", "Gemini 2.5 Pro",
    "Google ADK 2.0", "React + Vite", "Docker", "FRED API",
  ],
  github: "https://github.com/himanshuraimau/financial-driftguard",
}

export const CTA = {
  line1: "The market will shift.",
  line2: "Your model doesn't have to break.",
  button: "Clone and run it now ↗",
  href: "https://github.com/himanshuraimau/financial-driftguard",
}

export const FOOTER = {
  wordmark: "Financial DriftGuard",
  right: "Built June 2026 · furyfist.com · @furyfist",
}
