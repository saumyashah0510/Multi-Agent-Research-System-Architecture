import * as React from "react";
import { cn } from "../../lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "secondary" | "outline" | "ghost" | "link";
  size?: "default" | "sm" | "lg" | "icon";
}

const buttonVariants = {
  default:
    "bg-black text-white hover:bg-neutral-800 shadow-[var(--shadow-button)]",
  secondary:
    "bg-neutral-100 text-neutral-900 hover:bg-neutral-200",
  outline:
    "border border-neutral-300 bg-transparent hover:bg-neutral-100 text-neutral-900",
  ghost:
    "hover:bg-neutral-100 text-neutral-900",
  link:
    "text-black underline-offset-4 hover:underline",
};

const buttonSizes = {
  default: "h-10 px-4 py-2 text-sm md:text-base",
  sm: "h-8 px-3 text-xs md:text-sm",
  lg: "h-12 px-6 text-base md:text-lg",
  icon: "h-10 w-10 p-0",
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "default",
      size = "default",
      type = "button",
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        type={type}
        className={cn(
          "inline-flex items-center justify-center rounded-[var(--radius-sm)] font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 select-none cursor-pointer tracking-compact",
          buttonVariants[variant],
          buttonSizes[size],
          className
        )}
        {...props}
      />
    );
  }
);

Button.displayName = "Button";
