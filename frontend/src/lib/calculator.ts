/**
 * Calculator engine.
 *
 * A pure, UI-free state machine so the keypad surface stays dumb and the maths
 * can be unit-tested directly. `display` holds the raw entry ("1250", "12.5"),
 * while `formatCalculatorValue` is only applied for presentation.
 */

export type CalculatorOperator = "add" | "subtract" | "multiply" | "divide";

export type CalculatorAction =
  | { type: "digit"; digit: string }
  | { type: "decimal" }
  | { type: "operator"; operator: CalculatorOperator }
  | { type: "equals" }
  | { type: "percent" }
  | { type: "backspace" }
  | { type: "clear" };

export type CalculatorState = {
  /** Raw entry currently shown, e.g. "1250", "12.5", "-4". */
  display: string;
  /** Left-hand operand awaiting an operator. */
  accumulator: number | null;
  operator: CalculatorOperator | null;
  /** An operator was chosen but no new operand typed yet. */
  pendingOperand: boolean;
  /** The next digit replaces instead of appends (after operator/equals/percent). */
  replaceDisplay: boolean;
  /** Right-hand operand replayed on repeated equals presses. */
  repeat: { operator: CalculatorOperator; operand: number } | null;
  /** Last evaluation failed — display shows "Error" until cleared. */
  error: boolean;
};

/** Operators are shown as compact glyphs to match the keypad. */
export const OPERATOR_SYMBOLS: Record<CalculatorOperator, string> = {
  add: "+",
  subtract: "−",
  multiply: "×",
  divide: "÷",
};

/** Spoken form of each operator, for accessible key labels. */
export const OPERATOR_LABELS: Record<CalculatorOperator, string> = {
  add: "Add",
  subtract: "Subtract",
  multiply: "Multiply",
  divide: "Divide",
};

const MAX_DIGITS = 15;

export function createInitialCalculatorState(): CalculatorState {
  return {
    display: "0",
    accumulator: null,
    operator: null,
    pendingOperand: false,
    replaceDisplay: true,
    repeat: null,
    error: false,
  };
}

function errorState(): CalculatorState {
  return { ...createInitialCalculatorState(), error: true };
}

function evaluate(
  left: number,
  right: number,
  operator: CalculatorOperator,
): number | null {
  switch (operator) {
    case "add":
      return left + right;
    case "subtract":
      return left - right;
    case "multiply":
      return left * right;
    case "divide":
      return right === 0 ? null : left / right;
  }
}

/** Renders a number without the noise binary floating point leaves behind. */
function toDisplay(value: number): string {
  if (!Number.isFinite(value)) return "0";
  return String(Number.parseFloat(value.toPrecision(12)));
}

export function calculatorReducer(
  state: CalculatorState,
  action: CalculatorAction,
): CalculatorState {
  switch (action.type) {
    case "clear":
      return createInitialCalculatorState();

    case "digit": {
      if (!/^\d$/.test(action.digit)) return state;
      const base = state.error ? createInitialCalculatorState() : state;

      if (base.replaceDisplay) {
        return {
          ...base,
          display: action.digit,
          replaceDisplay: false,
          pendingOperand: false,
          repeat: null,
        };
      }

      const digits = base.display.replace(/\D/g, "").length;
      if (digits >= MAX_DIGITS) return base;

      const display = base.display === "0" ? action.digit : base.display + action.digit;
      return { ...base, display, pendingOperand: false, repeat: null };
    }

    case "decimal": {
      const base = state.error ? createInitialCalculatorState() : state;
      if (base.replaceDisplay) {
        return {
          ...base,
          display: "0.",
          replaceDisplay: false,
          pendingOperand: false,
          repeat: null,
        };
      }
      if (base.display.includes(".")) return base;
      return {
        ...base,
        display: `${base.display}.`,
        pendingOperand: false,
        repeat: null,
      };
    }

    case "operator": {
      if (state.error) return state;

      let accumulator = state.accumulator;
      let display = state.display;

      if (state.operator === null) {
        accumulator = Number(state.display);
      } else if (!state.pendingOperand && accumulator !== null) {
        // Chaining — resolve the running operation before taking the next operator.
        const result = evaluate(accumulator, Number(state.display), state.operator);
        if (result === null) return errorState();
        accumulator = result;
        display = toDisplay(result);
      }

      return {
        display,
        accumulator,
        operator: action.operator,
        pendingOperand: true,
        replaceDisplay: true,
        repeat: null,
        error: false,
      };
    }

    case "equals": {
      if (state.error) return state;

      if (state.operator !== null && state.accumulator !== null) {
        const operand = state.pendingOperand ? state.accumulator : Number(state.display);
        const result = evaluate(state.accumulator, operand, state.operator);
        if (result === null) return errorState();
        return {
          display: toDisplay(result),
          accumulator: result,
          operator: null,
          pendingOperand: false,
          replaceDisplay: true,
          repeat: { operator: state.operator, operand },
          error: false,
        };
      }

      if (state.repeat) {
        const result = evaluate(
          Number(state.display),
          state.repeat.operand,
          state.repeat.operator,
        );
        if (result === null) return errorState();
        return {
          ...state,
          display: toDisplay(result),
          accumulator: result,
          operator: null,
          pendingOperand: false,
          replaceDisplay: true,
        };
      }

      return { ...state, replaceDisplay: true, pendingOperand: false };
    }

    case "percent": {
      if (state.error) return state;

      const current = Number(state.display);
      // "Add/subtract" reads as a share of the running total; other operators
      // treat the entry as a plain fraction.
      const value =
        state.operator === "add" || state.operator === "subtract"
          ? ((state.accumulator ?? 0) * current) / 100
          : current / 100;

      return {
        ...state,
        display: toDisplay(value),
        pendingOperand: false,
        replaceDisplay: true,
        repeat: null,
      };
    }

    case "backspace": {
      if (state.error) return createInitialCalculatorState();
      if (state.replaceDisplay) return { ...state, display: "0", repeat: null };

      const next = state.display.slice(0, -1);
      return {
        ...state,
        display: next === "" || next === "-" ? "0" : next,
        replaceDisplay: false,
        repeat: null,
      };
    }
  }
}

/** Groups the integer part and keeps any in-progress decimal exactly as typed. */
export function formatCalculatorValue(value: string): string {
  if (value === "" || value === "-") return "0";

  const negative = value.startsWith("-");
  const body = negative ? value.slice(1) : value;
  if (body.includes("e") || body.includes("E")) return value;

  const [integer, decimal] = body.split(".");
  const grouped = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const sign = negative ? "-" : "";

  return body.includes(".") ? `${sign}${grouped}.${decimal ?? ""}` : `${sign}${grouped}`;
}

/** The small secondary line: the pending operation, or the failure reason. */
export function calculatorExpression(state: CalculatorState): string {
  if (state.error) return "Cannot divide by zero";
  if (state.operator === null || state.accumulator === null) return "";
  return `${formatCalculatorValue(toDisplay(state.accumulator))} ${OPERATOR_SYMBOLS[state.operator]}`;
}
