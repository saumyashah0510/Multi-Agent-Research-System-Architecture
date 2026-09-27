import React from "react";
import { motion, type Variants } from "framer-motion";
import { cn } from "../lib/utils";

export interface FeatureCardProps {
  id?: string;
  heading: string;
  subheading: string;
  description: string;
  image: string;
  imageAlt?: string;
  imagePosition?: "left" | "right";
  tint: "mint" | "lavender" | "sky";
  className?: string;
}

export default function FeatureCard({
  id,
  heading,
  subheading,
  description,
  image,
  imageAlt = "Feature illustration",
  imagePosition = "right",
  tint,
  className = "",
}: FeatureCardProps) {
  const gradientMap: Record<"mint" | "lavender" | "sky", string> = {
    mint: "linear-gradient(135deg, #BFE8B2 0%, #D2F0C6 50%, #E2F6DB 100%)",
    lavender: "linear-gradient(135deg, #C2C5F6 0%, #D4D7F8 50%, #E6E7FA 100%)",
    sky: "linear-gradient(135deg, #B2DBFA 0%, #C8E5FC 50%, #E0EFFD 100%)",
  };

  const cardStyle: React.CSSProperties = {
    background: gradientMap[tint],
    borderRadius: "var(--radius-lg)",
    boxShadow: "var(--shadow-card)",
    overflow: "hidden",
  };

  const cardVariants: Variants = {
    hidden: { opacity: 0, y: 32 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.5,
        ease: [0.4, 0, 0.2, 1] as const,
        staggerChildren: 0.12,
      },
    },
  };

  const childVariants: Variants = {
    hidden: { opacity: 0, y: 16 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.4,
        ease: [0.4, 0, 0.2, 1] as const,
      },
    },
  };

  const textBlock = (
    <motion.div
      variants={childVariants}
      className="flex-1 flex flex-col justify-center max-w-xl"
    >
      <h2
        className="font-serif-heading font-semibold text-2xl sm:text-3xl md:text-4xl tracking-compact leading-tight"
        style={{ color: "var(--color-text-primary)" }}
      >
        {heading}
      </h2>
      <h3
        className="font-sans-ui font-medium text-lg sm:text-xl md:text-2xl mt-3 md:mt-4 leading-snug tracking-compact"
        style={{ color: "var(--color-text-primary)" }}
      >
        {subheading}
      </h3>
      <p className="font-sans-ui text-sm sm:text-base mt-3 md:mt-4 leading-relaxed tracking-compact text-neutral-800">
        {description}
      </p>
    </motion.div>
  );

  const imageBlock = (
    <motion.div
      variants={childVariants}
      className="flex items-center justify-center w-full h-full"
    >
      <img
        src={image}
        alt={imageAlt}
        loading="lazy"
        style={{ borderRadius: "var(--radius-lg)", aspectRatio: "1 / 1" }}
        className="aspect-square w-[230px] h-[230px] sm:w-[260px] sm:h-[260px] md:w-[280px] md:h-[280px] max-h-[286px] max-w-full object-cover transition-transform duration-300 hover:scale-[1.02] shadow-sm shrink-0"
      />
    </motion.div>
  );

  const isImageLeft = imagePosition === "left";

  return (
    <motion.section
      id={id}
      variants={cardVariants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.15 }}
      whileHover={{ y: -4, transition: { duration: 0.25 } }}
      style={cardStyle}
      className={cn(
        "w-full min-h-[350px] md:h-[350px] p-5 sm:p-6 md:p-8 flex flex-col md:flex-row gap-4 md:gap-8 items-center justify-between transition-shadow duration-300 hover:shadow-lg",
        className
      )}
    >
      {/* On mobile: image is stacked first. On tablet/desktop (md): order is dictated by imagePosition */}
      <div
        className={cn(
          "order-1 w-full md:w-1/2 flex justify-center items-center",
          isImageLeft ? "md:order-1" : "md:order-2"
        )}
      >
        {imageBlock}
      </div>
      <div
        className={cn(
          "order-2 w-full md:w-1/2",
          isImageLeft ? "md:order-2" : "md:order-1"
        )}
      >
        {textBlock}
      </div>
    </motion.section>
  );
}
