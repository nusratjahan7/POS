"use client";

import { Delete } from "lucide-react";

import { cn } from "@/lib/utils";
import {
  calculatorExpression,
  formatCalculatorValue,
  OPERATOR_LABELS,
  type CalculatorAction,
  type CalculatorOperator,
  type CalculatorState,
} from "@/lib/calculator";

type CalculatorProps = {
  state: CalculatorState;
  onAction: (action: CalculatorAction) => void;
  className?: string;
};

type KeyVariant = "digit" | "operator" | "control" | "equals";

type Key = {
  label: string;
  action: CalculatorAction;
  variant: KeyVariant;
  /** Screen-reader label; the visible glyph stays compact. */
  ariaLabel?: string;
  /** Grid columns to occupy. */
  span?: number;
};

const KEY_BASE =
  "flex items-center justify-center rounded-md font-medium tabular-nums transition-[background-color,color,box-shadow,transform] duration-150 outline-none select-none focus-visible:ring-2 focus-visible:ring-ring/60 active:translate-y-px";

const KEY_VARIANTS: Record<KeyVariant, string> = {
  digit:
    "border border-input bg-card text-foreground shadow-xs hover:bg-accent hover:text-accent-foreground",
  operator: "bg-primary/10 text-primary hover:bg-primary/15",
  control: "bg-destructive/10 text-destructive hover:bg-destructive/15",
  equals: "bg-primary text-primary-foreground shadow-xs hover:bg-primary/90",
};

function digitKey(digit: string): Key {
  return { label: digit, action: { type: "digit", digit }, variant: "digit" };
}

function operatorKey(operator: CalculatorOperator): Key {
  const glyph: Record<CalculatorOperator, string> = {
    add: "+",
    subtract: "−",
    multiply: "×",
    divide: "÷",
  };
  return {
    label: glyph[operator],
    action: { type: "operator", operator },
    variant: "operator",
    ariaLabel: OPERATOR_LABELS[operator],
  };
}

const ROWS: Key[][] = [
  [digitKey("7"), digitKey("8"), digitKey("9"), operatorKey("divide")],
  [digitKey("4"), digitKey("5"), digitKey("6"), operatorKey("multiply")],
  [digitKey("1"), digitKey("2"), digitKey("3"), operatorKey("subtract")],
  [
    digitKey("0"),
    { label: ".", action: { type: "decimal" }, variant: "digit", ariaLabel: "Decimal point" },
    { label: "%", action: { type: "percent" }, variant: "operator", ariaLabel: "Percent" },
    operatorKey("add"),
  ],
  [
    { label: "C", action: { type: "clear" }, variant: "control", ariaLabel: "Clear", span: 3 },
    { label: "=", action: { type: "equals" }, variant: "equals", ariaLabel: "Equals" },
  ],
];

/**
 * The calculator surface — display and keypad. Fully controlled: the caller owns
 * the state and receives actions, so it can be reused with any state container.
 */
function Calculator({ state, onAction, className }: CalculatorProps) {
  const value = state.error ? "Error" : formatCalculatorValue(state.display);
  const expression = calculatorExpression(state);

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      <div className="flex items-center gap-2">
        <div className="min-w-0 flex-1 text-right">
          <div className="text-muted-foreground h-4 truncate text-xs">{expression}</div>
          <div
            aria-live="polite"
            aria-atomic="true"
            className={cn(
              "truncate text-3xl font-semibold tracking-tight tabular-nums",
              state.error && "text-destructive",
            )}
          >
            {value}
          </div>
        </div>

        <button
          type="button"
          aria-label="Backspace"
          title="Backspace"
          onClick={() => onAction({ type: "backspace" })}
          className="text-muted-foreground hover:bg-accent hover:text-foreground focus-visible:ring-ring/60 flex size-9 shrink-0 items-center justify-center rounded-md transition-colors outline-none focus-visible:ring-2"
        >
          <Delete className="size-4" />
        </button>
      </div>

      <div className="grid grid-cols-4 gap-2">
        {ROWS.flat().map((key, index) => (
          <button
            key={index}
            type="button"
            aria-label={key.ariaLabel}
            onClick={() => onAction(key.action)}
            className={cn(
              KEY_BASE,
              "h-11 text-base",
              KEY_VARIANTS[key.variant],
              key.span === 3 && "col-span-3",
            )}
          >
            {key.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export { Calculator };
