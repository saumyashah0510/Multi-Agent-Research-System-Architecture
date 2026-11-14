import * as React from "react";
import { cn } from "../../lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:
    | "default"
    | "secondary"
    | "outline"
    | "ghost"
    | "link"
    | "accent"
    | "destructive";
  size?: "default" | "sm" | "lg" | "icon";
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const buttonVariants: Record<NonNullable<ButtonProps["variant"]>, string> = {
  default:
    "bg-neutral-950 text-white hover:bg-neutral-800 shadow-[var(--shadow-button)] active:scale-[0.98]",
  secondary:
    "bg-neutral-100 text-neutral-900 hover:bg-neutral-200 active:scale-[0.98]",
  outline:
    "border border-neutral-300 bg-transparent hover:bg-neutral-100 text-neutral-900 active:scale-[0.98]",
  ghost:
    "hover:bg-neutral-100 text-neutral-900 active:scale-[0.98]",
  link:
    "text-neutral-950 underline-offset-4 hover:underline p-0 h-auto font-medium",
  accent:
    "bg-[var(--color-accent)] text-neutral-950 border border-black/10 hover:brightness-95 shadow-sm active:scale-[0.98]",
  destructive:
    "bg-[var(--color-danger)] text-white hover:bg-[var(--color-danger-hover)] shadow-sm active:scale-[0.98]",
};

const buttonSizes: Record<NonNullable<ButtonProps["size"]>, string> = {
  default: "h-10 px-4 py-2 text-sm md:text-base gap-2",
  sm: "h-8 px-3 text-xs md:text-sm gap-1.5",
  lg: "h-12 px-6 text-base md:text-lg gap-2.5",
  icon: "h-10 w-10 p-0 justify-center",
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      className,
      variant = "default",
      size = "default",
      type = "button",
      disabled = false,
      isLoading = false,
      leftIcon,
      rightIcon,
      onClick,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || isLoading;

    return (
      <button
        ref={ref}
        type={type}
        disabled={isDisabled}
        onClick={onClick}
        className={cn(
          "inline-flex items-center justify-center rounded-[var(--radius-sm)] font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black focus-visible:ring-offset-2 select-none cursor-pointer tracking-compact",
          isDisabled && "pointer-events-none opacity-50 cursor-not-allowed",
          buttonVariants[variant],
          buttonSizes[size],
          className
        )}
        {...props}
      >
        {isLoading && (
          <svg
            className="animate-spin -ml-1 mr-2 h-4 w-4 shrink-0 text-current"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
            />
          </svg>
        )}
        {!isLoading && leftIcon && (
          <span className="inline-flex shrink-0 items-center">{leftIcon}</span>
        )}
        {children}
        {rightIcon && (
          <span className="inline-flex shrink-0 items-center">{rightIcon}</span>
        )}
      </button>
    );
  }
);

Button.displayName = "Button";

export default Button;
