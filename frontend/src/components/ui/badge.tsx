import * as React from "react";
import { cn } from "../../lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "outline" | "accent";
}

export function Badge({
  className,
  variant = "default",
  ...props
}: BadgeProps) {
  const variantStyles = {
    default: "bg-black text-white",
    secondary: "bg-neutral-100 text-neutral-800",
    outline: "border border-neutral-300 text-neutral-800",
    accent: "bg-[var(--color-accent)] text-black border border-black/10",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold tracking-compact transition-colors focus:outline-none focus:ring-2 focus:ring-black focus:ring-offset-2",
        variantStyles[variant],
        className
      )}
      {...props}
    />
  );
}
