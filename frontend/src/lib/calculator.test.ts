import { describe, expect, it } from "vitest";

import {
  calculatorReducer,
  createInitialCalculatorState,
  formatCalculatorValue,
  type CalculatorAction,
  type CalculatorOperator,
  type CalculatorState,
} from "./calculator";

function press(...actions: CalculatorAction[]): CalculatorState {
  return actions.reduce(calculatorReducer, createInitialCalculatorState());
}

function type(text: string): CalculatorAction[] {
  return [...text].map((digit) => ({ type: "digit", digit }));
}

const add: CalculatorAction = { type: "operator", operator: "add" };
const subtract: CalculatorAction = { type: "operator", operator: "subtract" };
const multiply: CalculatorAction = { type: "operator", operator: "multiply" };
const divide: CalculatorAction = { type: "operator", operator: "divide" };
const equals: CalculatorAction = { type: "equals" };

function operate(operator: CalculatorOperator): CalculatorAction {
  return { type: "operator", operator };
}

describe("calculator engine", () => {
  it("starts at zero", () => {
    expect(createInitialCalculatorState().display).toBe("0");
  });

  it("builds a number from individual digits", () => {
    expect(press(...type("1250")).display).toBe("1250");
  });

  it("adds", () => {
    expect(press(...type("2"), add, ...type("3"), equals).display).toBe("5");
  });

  it("subtracts", () => {
    expect(press(...type("10"), subtract, ...type("4"), equals).display).toBe("6");
  });

  it("multiplies", () => {
    expect(press(...type("6"), multiply, ...type("7"), equals).display).toBe("42");
  });

  it("divides", () => {
    expect(press(...type("9"), divide, ...type("4"), equals).display).toBe("2.25");
  });

  it("supports decimal entry", () => {
    expect(press(...type("1"), { type: "decimal" }, ...type("5")).display).toBe("1.5");
    expect(
      press(...type("1"), { type: "decimal" }, ...type("5"), add, ...type("2"), { type: "decimal" }, ...type("25"), equals).display,
    ).toBe("3.75");
  });

  it("ignores a second decimal point", () => {
    expect(
      press(...type("1"), { type: "decimal" }, { type: "decimal" }, ...type("2")).display,
    ).toBe("1.2");
  });

  it("shakes off binary floating-point noise", () => {
    expect(press(...type("0"), { type: "decimal" }, ...type("1"), add, ...type("0"), { type: "decimal" }, ...type("2"), equals).display).toBe("0.3");
  });

  it("starts a fresh entry after an operator instead of appending", () => {
    expect(press(...type("5"), add).display).toBe("5");
    expect(press(...type("5"), add, ...type("2")).display).toBe("2");
  });

  it("chains operations, resolving the running total", () => {
    const state = press(...type("2"), add, ...type("3"), add, ...type("4"), equals);
    expect(state.display).toBe("9");
  });

  it("lets a freshly pressed operator replace the previous one", () => {
    const state = press(...type("5"), add, multiply, ...type("3"), equals);
    expect(state.display).toBe("15");
  });

  it("treats equals right after an operator as repeating the left operand", () => {
    expect(press(...type("5"), add, equals).display).toBe("10");
  });

  it("repeats the last operation on further equals presses", () => {
    const first = press(...type("2"), add, ...type("3"), equals);
    expect(first.display).toBe("5");
    const second = calculatorReducer(first, equals);
    expect(second.display).toBe("8");
    expect(calculatorReducer(second, equals).display).toBe("11");
  });

  it("flags divide by zero as an error", () => {
    const state = press(...type("5"), divide, ...type("0"), equals);
    expect(state.error).toBe(true);
  });

  it("recovers from an error when a new number is typed", () => {
    const errored = press(...type("5"), divide, ...type("0"), equals);
    const recovered = calculatorReducer(errored, { type: "digit", digit: "7" });
    expect(recovered.error).toBe(false);
    expect(recovered.display).toBe("7");
  });

  it("reads percent as a share of the total for add and subtract", () => {
    expect(press(...type("100"), add, ...type("10"), { type: "percent" }, equals).display).toBe("110");
    expect(press(...type("100"), subtract, ...type("10"), { type: "percent" }, equals).display).toBe("90");
  });

  it("reads percent as a fraction for multiply and divide", () => {
    expect(press(...type("200"), multiply, ...type("10"), { type: "percent" }, equals).display).toBe("20");
    expect(press(...type("50"), divide, ...type("10"), { type: "percent" }, equals).display).toBe("500");
  });

  it("backspaces one character at a time", () => {
    const state = press(...type("123"), { type: "backspace" });
    expect(state.display).toBe("12");
    expect(calculatorReducer(state, { type: "backspace" }).display).toBe("1");
    expect(
      calculatorReducer(calculatorReducer(state, { type: "backspace" }), { type: "backspace" })
        .display,
    ).toBe("0");
  });

  it("clears back to the initial state", () => {
    const state = press(...type("42"), add, ...type("8"), { type: "clear" });
    expect(state).toEqual(createInitialCalculatorState());
  });

  it("caps the number of digits", () => {
    const state = press(...type("12345678901234567890"));
    expect(state.display).toBe("123456789012345");
  });

  it("keeps pending operators and values through every branch", () => {
    const state = press(...type("12"), operate("add"));
    expect(state.operator).toBe("add");
    expect(state.accumulator).toBe(12);
    expect(state.pendingOperand).toBe(true);
  });
});

describe("formatCalculatorValue", () => {
  it("groups thousands", () => {
    expect(formatCalculatorValue("1250")).toBe("1,250");
    expect(formatCalculatorValue("1234567.89")).toBe("1,234,567.89");
  });

  it("preserves a negative sign and an in-progress decimal", () => {
    expect(formatCalculatorValue("-500")).toBe("-500");
    expect(formatCalculatorValue("0.")).toBe("0.");
  });

  it("falls back to zero for empty input", () => {
    expect(formatCalculatorValue("")).toBe("0");
    expect(formatCalculatorValue("-")).toBe("0");
  });

  it("leaves exponential notation untouched", () => {
    expect(formatCalculatorValue("1e+21")).toBe("1e+21");
  });
});
