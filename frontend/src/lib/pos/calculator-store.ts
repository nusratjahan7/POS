"use client";

import { create } from "zustand";

import {
  calculatorReducer,
  createInitialCalculatorState,
  type CalculatorAction,
  type CalculatorState,
} from "@/lib/calculator";

/**
 * Shared calculator state. Kept in a module store (not component state) so the
 * popup survives navigation within the POS shell and can be opened from
 * anywhere — the header button is only one possible entry point. The calculator
 * has no full-screen mode of its own; app full screen is a separate concern.
 */
type CalculatorStore = {
  open: boolean;
  state: CalculatorState;
  openCalculator: () => void;
  closeCalculator: () => void;
  toggleCalculator: () => void;
  dispatch: (action: CalculatorAction) => void;
};

export const useCalculator = create<CalculatorStore>((set) => ({
  open: false,
  state: createInitialCalculatorState(),
  openCalculator: () => set({ open: true }),
  closeCalculator: () => set({ open: false }),
  toggleCalculator: () => set((current) => ({ open: !current.open })),
  dispatch: (action) => set((current) => ({ state: calculatorReducer(current.state, action) })),
}));
