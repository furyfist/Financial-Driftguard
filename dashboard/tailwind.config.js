/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans:    ["Geist", "sans-serif"],
        mono:    ["Geist Mono", "monospace"],
        display: ["Bricolage Grotesque", "sans-serif"],
        body:    ["Bricolage Grotesque", "sans-serif"],
      },
      colors: {
        // Landing page tokens
        "purple-900": "#26215C",
        "purple-800": "#3C3489",
        "purple-50":  "#EEEDFE",
        "teal-600":   "#0F6E56",
        "teal-50":    "#E1F5EE",
        "red-600":    "#A32D2D",
        "red-50":     "#FCEBEB",
        "amber-600":  "#854F0B",
        "amber-50":   "#FAEEDA",
        "gray-900":   "#2C2C2A",
        "gray-600":   "#5F5E5A",
        "gray-200":   "#B4B2A9",
        "gray-50":    "#F1EFE8",
        "bg-surface": "#F8F8F7",
        // Dashboard tokens (preserved)
        canvas: "#F7F6F3",
        surface: "#FFFFFF",
        border: "#E8E6E0",
        "border-subtle": "#EEECE8",
        ink: "#1A1916",
        "ink-muted": "#6B6860",
        "ink-faint": "#A8A49E",
        accent: "#D4450C",
        "accent-soft": "#FBF0EC",
        stable: "#1A6B3C",
        "stable-soft": "#EDFAF3",
        warning: "#B45309",
        "warning-soft": "#FEF7EC",
        critical: "#C0200F",
        "critical-soft": "#FEF0EE",
      },
      fontSize: {
        hero: ["clamp(2.5rem, 6vw, 5rem)", { lineHeight: "1.1", letterSpacing: "-0.04em" }],
        h2:   ["clamp(1.75rem, 3vw, 2.5rem)", { lineHeight: "1.2", letterSpacing: "-0.03em" }],
        h3:   ["1.25rem", { lineHeight: "1.4" }],
      },
    },
  },
  plugins: [],
}
