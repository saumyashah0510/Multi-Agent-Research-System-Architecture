import * as React from "react";
import { cn } from "../../lib/utils";

export interface InputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "size"> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  inputSize?: "sm" | "default" | "lg";
  variant?: "default" | "dark";
}

const inputSizeClasses = {
  sm: "h-8 px-2.5 text-xs",
  default: "h-10 px-3.5 text-sm",
  lg: "h-12 px-4 text-base",
};

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      type = "text",
      label,
      error,
      helperText,
      leftIcon,
      rightIcon,
      inputSize = "default",
      variant = "default",
      disabled = false,
      id,
      ...props
    },
    ref
  ) => {
    const generatedId = React.useId();
    const inputId = id || generatedId;
    const errorId = `${inputId}-error`;
    const helperId = `${inputId}-helper`;

    const variantClasses =
      variant === "dark"
        ? "bg-slate-900 border-slate-700 text-slate-100 placeholder:text-slate-500 focus-visible:ring-slate-400 focus-visible:border-slate-400"
        : "bg-white border-neutral-300 text-neutral-900 placeholder:text-neutral-400 focus-visible:ring-black focus-visible:border-black";

    return (
      <div className="w-full space-y-1.5 text-left">
        {label && (
          <label
            htmlFor={inputId}
            className={cn(
              "block text-xs font-medium tracking-compact",
              variant === "dark" ? "text-slate-300" : "text-neutral-700"
            )}
          >
            {label}
          </label>
        )}

        <div className="relative flex items-center">
          {leftIcon && (
            <div
              className={cn(
                "pointer-events-none absolute left-3 flex items-center justify-center",
                variant === "dark" ? "text-slate-400" : "text-neutral-400"
              )}
            >
              {leftIcon}
            </div>
          )}

          <input
            ref={ref}
            id={inputId}
            type={type}
            disabled={disabled}
            aria-invalid={Boolean(error)}
            aria-describedby={
              error ? errorId : helperText ? helperId : undefined
            }
            className={cn(
              "flex w-full rounded-[var(--radius-sm)] border text-sm transition-all duration-150 outline-none tracking-compact shadow-sm",
              "focus-visible:ring-2 focus-visible:ring-offset-1",
              inputSizeClasses[inputSize],
              leftIcon ? (inputSize === "lg" ? "pl-11" : "pl-9") : undefined,
              rightIcon ? (inputSize === "lg" ? "pr-11" : "pr-9") : undefined,
              disabled ? "cursor-not-allowed opacity-50 bg-neutral-100" : undefined,
              error
                ? "border-rose-500 text-rose-900 focus-visible:ring-rose-500"
                : variantClasses,
              className
            )}
            {...props}
          />

          {rightIcon && (
            <div
              className={cn(
                "pointer-events-none absolute right-3 flex items-center justify-center",
                variant === "dark" ? "text-slate-400" : "text-neutral-400"
              )}
            >
              {rightIcon}
            </div>
          )}
        </div>

        {error && (
          <p id={errorId} className="text-xs text-rose-500 tracking-compact">
            {error}
          </p>
        )}

        {!error && helperText && (
          <p
            id={helperId}
            className={cn(
              "text-xs tracking-compact",
              variant === "dark" ? "text-slate-400" : "text-neutral-500"
            )}
          >
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";

export default Input;
