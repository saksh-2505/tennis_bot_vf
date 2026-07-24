import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline" | "ghost" | "destructive";
  size?: "sm" | "default" | "lg";
  /** Disables the button and renders a spinner; removes the need to scatter
      boolean+spinner combinations across every pagination button. */
  loading?: boolean;
}

// Hoisted to module scope — previously the variant/size maps were rebuilt every
// render. Pure strings, identical across all callers.
const BASE =
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-1 focus-visible:ring-offset-slate-950 disabled:pointer-events-none disabled:opacity-50";

const VARIANTS: Record<string, string> = {
  default: "bg-emerald-600 text-white shadow hover:bg-emerald-500",
  outline: "border border-slate-700 bg-transparent hover:bg-slate-800 text-slate-200",
  ghost: "hover:bg-slate-800 text-slate-300 hover:text-slate-100",
  destructive: "bg-red-600 text-white shadow hover:bg-red-500",
};

const SIZES: Record<string, string> = {
  sm: "h-8 px-3 text-xs rounded-md",
  default: "h-9 px-4 py-2",
  lg: "h-10 px-6 rounded-md",
};

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", type = "button", loading, disabled, children, ...props }, ref) => {
    return (
      <button
        className={cn(BASE, VARIANTS[variant], SIZES[size], className)}
        ref={ref}
        type={type}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <span className="mr-2 h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent opacity-70" />
        )}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";

export { Button };
