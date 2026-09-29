import { motion, useReducedMotion, type Variants } from "framer-motion";
import Button from "./Button";
import scholarisLogo from "../images/Scholaris_logo.png";

export default function Hero() {
  const shouldReduceMotion = useReducedMotion();

  const containerVariants: Variants = {
    hidden: { opacity: 1 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: shouldReduceMotion ? 0.05 : 0.1,
      },
    },
  };

  const itemVariants: Variants = {
    hidden: { opacity: 0, y: shouldReduceMotion ? 8 : 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.45,
        ease: [0.4, 0, 0.2, 1] as const,
      },
    },
  };

  return (
    <section
      className="w-full pt-12 sm:pt-16 md:pt-20 pb-16 md:pb-24 px-6 md:px-12 flex flex-col items-center text-center bg-transparent"
      aria-label="Hero Section"
    >
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="max-w-[var(--container-max-width)] mx-auto flex flex-col items-center"
      >
        {/* Large Logo Emblem + Wordmark */}
        <motion.div
          variants={itemVariants}
          className="flex items-center gap-3 select-none mb-8 sm:mb-10"
        >
          <img
            src={scholarisLogo}
            alt="Scholaris Logo Emblem"
            className="w-12 h-12 sm:w-14 sm:h-14 md:w-16 md:h-16 object-contain"
          />
          <span className="font-sans-ui font-bold text-3xl sm:text-4xl md:text-5xl tracking-compact text-black">
            Scholaris
          </span>
        </motion.div>

        {/* Display Headline */}
        <motion.h1
          variants={itemVariants}
          className="font-serif-heading font-semibold text-3xl sm:text-5xl md:text-6xl text-black tracking-compact leading-[1.15] max-w-4xl"
          style={{
            fontSize: "clamp(2rem, 5vw, 3.75rem)",
          }}
        >
          Autonomous literature reviews,
          <br className="hidden sm:inline" /> built for researchers
        </motion.h1>

        {/* Sub-headline */}
        <motion.p
          variants={itemVariants}
          className="font-sans-ui text-base sm:text-lg md:text-xl mt-5 sm:mt-6 max-w-2xl leading-relaxed tracking-compact text-neutral-600"
        >
          Automate paper discovery, detect methodological contradictions, and
          chat securely with your literature
        </motion.p>

        {/* Primary CTA */}
        <motion.div variants={itemVariants} className="mt-8 sm:mt-10">
          <Button
            to="/dashboard"
            ariaLabel="Get Started Now — navigate to dashboard"
            className="text-base sm:text-lg px-8 py-3.5 sm:py-4 font-semibold tracking-compact rounded-lg shadow-lg shadow-black/25 hover:shadow-xl hover:shadow-black/35"
          >
            Get Started Now →
          </Button>
        </motion.div>
      </motion.div>
    </section>
  );
}
