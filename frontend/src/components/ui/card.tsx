import * as React from "react";
import { cn } from "../../lib/utils";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "dark" | "glass" | "interactive" | "outline";
}

const cardVariants: Record<NonNullable<CardProps["variant"]>, string> = {
  default:
    "border-neutral-200/80 bg-white text-neutral-900 shadow-[var(--shadow-card)]",
  dark:
    "border-slate-800 bg-slate-900/90 text-slate-100 shadow-xl",
  glass:
    "border-white/40 bg-white/70 backdrop-blur-md text-neutral-900 shadow-md",
  interactive:
    "border-neutral-200/80 bg-white text-neutral-900 shadow-[var(--shadow-card)] hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 cursor-pointer",
  outline:
    "border-neutral-200 bg-transparent text-neutral-900 shadow-none",
};

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = "default", children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "rounded-[var(--radius-lg)] border transition-colors",
          cardVariants[variant],
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);
Card.displayName = "Card";

export const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, children, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={cn("flex flex-col space-y-1.5 p-6", className)}
      {...props}
    >
      {children}
    </div>
  );
});
CardHeader.displayName = "CardHeader";

export const CardTitle = React.forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, children, ...props }, ref) => {
  return (
    <h3
      ref={ref}
      className={cn(
        "font-semibold leading-none tracking-compact text-inherit",
        className
      )}
      {...props}
    >
      {children}
    </h3>
  );
});
CardTitle.displayName = "CardTitle";

export const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, children, ...props }, ref) => {
  return (
    <p
      ref={ref}
      className={cn(
        "text-sm text-neutral-500 tracking-compact opacity-80",
        className
      )}
      {...props}
    >
      {children}
    </p>
  );
});
CardDescription.displayName = "CardDescription";

export const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, children, ...props }, ref) => {
  return (
    <div ref={ref} className={cn("p-6 pt-0", className)} {...props}>
      {children}
    </div>
  );
});
CardContent.displayName = "CardContent";

export const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, children, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={cn("flex items-center p-6 pt-0", className)}
      {...props}
    >
      {children}
    </div>
  );
});
CardFooter.displayName = "CardFooter";

export default Card;
