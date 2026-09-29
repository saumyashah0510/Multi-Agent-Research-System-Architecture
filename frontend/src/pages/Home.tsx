import Navbar from "../components/Navbar";
import Hero from "../components/Hero";
import HowItWorksSection from "../components/HowItWorksSection";
import Button from "../components/Button";
import Footer from "../components/Footer";

export default function Home() {
  return (
    <div
      className="min-h-screen flex flex-col font-sans-ui"
      style={{
        background: "var(--gradient-hero-bg)",
      }}
    >
      {/* Sticky Top Navigation */}
      <Navbar />

      {/* Hero Section */}
      <Hero />

      {/* Main Content Area */}
      <main
        className="relative z-10 w-full max-w-[var(--container-max-width)] mx-auto px-6 md:px-12 pt-10 md:pt-14 pb-0 flex flex-col items-center"
        aria-label="How Scholaris Works"
      >
        {/* Feature Narrative Cards */}
        <HowItWorksSection />

        {/* Closing CTA */}
        <div className="w-full flex flex-col items-center justify-center pt-12 md:pt-16 pb-4 md:pb-6 text-center">
          <Button
            to="/dashboard"
            ariaLabel="Get Started Now — navigate to dashboard"
            className="text-base sm:text-lg px-8 py-3.5 sm:py-4 font-semibold tracking-compact rounded-lg shadow-lg shadow-black/25 hover:shadow-xl hover:shadow-black/35"
          >
            Get Started Now →
          </Button>
        </div>
      </main>

      {/* Site Footer */}
      <Footer />
    </div>
  );
}
