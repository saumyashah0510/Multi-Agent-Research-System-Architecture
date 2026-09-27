import React from "react";
import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { cn } from "../lib/utils";

export interface ButtonProps {
  children: React.ReactNode;
  to?: string;
  href?: string;
  onClick?: () => void;
  className?: string;
  type?: "button" | "submit" | "reset";
  icon?: React.ReactNode;
  iconPosition?: "left" | "right";
  ariaLabel?: string;
  target?: string;
  rel?: string;
}

export default function Button({
  children,
  to,
  href,
  onClick,
  className = "",
  type = "button",
  icon,
  iconPosition = "left",
  ariaLabel,
  target,
  rel,
}: ButtonProps) {
  const shouldReduceMotion = useReducedMotion();

  const buttonStyle: React.CSSProperties = {
    backgroundColor: "var(--color-button-primary)",
    color: "var(--color-button-primary-text)",
    borderRadius: "var(--radius-sm)",
    fontFamily: "var(--font-sans)",
    letterSpacing: "-0.04em",
    transition:
      "box-shadow var(--duration-fast) var(--ease-standard), background-color var(--duration-fast) var(--ease-standard), transform var(--duration-fast) var(--ease-standard)",
  };

  const hoverAnimation = shouldReduceMotion
    ? { scale: 1.02 }
    : {
      scale: 1.02,
    };

  const tapAnimation = {
    scale: 0.98,
  };

  const content = (
    <>
      {icon && iconPosition === "left" && (
        <span className="inline-flex items-center mr-2">{icon}</span>
      )}
      <span className="font-medium tracking-compact leading-none">
        {children}
      </span>
      {icon && iconPosition === "right" && (
        <span className="inline-flex items-center ml-2">{icon}</span>
      )}
    </>
  );

  const baseClasses = cn(
    "inline-flex items-center justify-center cursor-pointer select-none no-underline outline-none focus-visible:ring-2 focus-visible:ring-black focus-visible:ring-offset-2 tracking-compact transition-all duration-150 px-4 py-2 text-sm sm:text-base",
    className
  );

  if (to) {
    return (
      <motion.div
        whileHover={hoverAnimation}
        whileTap={tapAnimation}
        className="inline-block"
      >
        <Link
          to={to}
          className={baseClasses}
          style={buttonStyle}
          aria-label={ariaLabel}
        >
          {content}
        </Link>
      </motion.div>
    );
  }

  if (href) {
    return (
      <motion.a
        href={href}
        target={target}
        rel={rel ?? (target === "_blank" ? "noopener noreferrer" : undefined)}
        whileHover={hoverAnimation}
        whileTap={tapAnimation}
        className={baseClasses}
        style={buttonStyle}
        aria-label={ariaLabel}
      >
        {content}
      </motion.a>
    );
  }

  return (
    <motion.button
      type={type}
      onClick={onClick}
      whileHover={hoverAnimation}
      whileTap={tapAnimation}
      className={baseClasses}
      style={buttonStyle}
      aria-label={ariaLabel}
    >
      {content}
    </motion.button>
  );
}
