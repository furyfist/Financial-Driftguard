import { useEffect } from "react"
import { Nav }        from "../components/landing/Nav"
import { Hero }       from "../components/landing/Hero"
import { Problem }    from "../components/landing/Problem"
import { HowItWorks } from "../components/landing/HowItWorks"
import { Demo }       from "../components/landing/Demo"
import { Proof }      from "../components/landing/Proof"
import { Stack }      from "../components/landing/Stack"
import { CTA }        from "../components/landing/CTA"
import { Footer }     from "../components/landing/Footer"

export default function LandingPage() {
  useEffect(() => {
    document.title = "Financial DriftGuard — Model Governance"
  }, [])

  return (
    <>
      <Nav />
      <main>
        <section id="hero"><Hero /></section>
        <section id="problem"><Problem /></section>
        <section id="how-it-works"><HowItWorks /></section>
        <section id="demo"><Demo /></section>
        <section id="proof"><Proof /></section>
        <section id="stack"><Stack /></section>
        <CTA />
      </main>
      <Footer />
    </>
  )
}
