// Reusable Button UI Component Skeleton
// TODO (Assignee - Frontend Developer): Style button component according to your design preference

import * as React from "react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ children, ...props }, ref) => {
    return (
      <button ref={ref} {...props}>
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
