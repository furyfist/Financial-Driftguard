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
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <Problem />
        <HowItWorks />
        <Demo />
        <Proof />
        <Stack />
        <CTA />
      </main>
      <Footer />
    </>
  )
}
