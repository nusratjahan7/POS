"use client";

import * as React from "react";
import { Calculator as CalculatorIcon, X } from "lucide-react";

import { Calculator } from "@/components/calculator/calculator";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useCalculator } from "@/lib/pos/calculator-store";
import { cn } from "@/lib/utils";
import type { CalculatorAction } from "@/lib/calculator";

/** Maps a physical key to a calculator action; null means "not ours". */
function keyToAction(key: string): CalculatorAction | null {
  if (key.length === 1 && key >= "0" && key <= "9") {
    return { type: "digit", digit: key };
  }
  switch (key) {
    case ".":
    case ",":
      return { type: "decimal" };
    case "+":
      return { type: "operator", operator: "add" };
    case "-":
      return { type: "operator", operator: "subtract" };
    case "*":
    case "x":
    case "X":
      return { type: "operator", operator: "multiply" };
    case "/":
      return { type: "operator", operator: "divide" };
    case "%":
      return { type: "percent" };
    case "Enter":
    case "=":
      return { type: "equals" };
    case "Backspace":
      return { type: "backspace" };
    case "Delete":
    case "c":
    case "C":
      return { type: "clear" };
    default:
      return null;
  }
}

/**
 * The calculator popup — a small centered card with a transparent backdrop so
 * the POS stays visible behind it. Mounted once in the app shell so the value
 * survives navigation, and fully independent of app full screen. Keyboard events
 * are handled on the panel only, so the barcode scanner and register shortcuts
 * are never intercepted.
 *
 * Rendered as a sibling of the header (never inside it) so the header's
 * backdrop-filter does not become the containing block for this fixed layer.
 */
function CalculatorPopup() {
  const open = useCalculator((selector) => selector.open);
  const state = useCalculator((selector) => selector.state);
  const dispatch = useCalculator((selector) => selector.dispatch);
  const closeCalculator = useCalculator((selector) => selector.closeCalculator);

  const panelRef = React.useRef<HTMLDivElement>(null);
  const hasOpened = React.useRef(false);

  // Focus the panel on open; hand focus back to the trigger on close.
  React.useEffect(() => {
    if (open) {
      hasOpened.current = true;
      const frame = window.requestAnimationFrame(() => panelRef.current?.focus());
      return () => window.cancelAnimationFrame(frame);
    }
    if (hasOpened.current) {
      document.querySelector<HTMLElement>("[data-calculator-trigger]")?.focus();
    }
  }, [open]);

  function handleBackdropPointerDown(event: React.PointerEvent<HTMLDivElement>) {
    if (event.target === event.currentTarget) closeCalculator();
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    const key = event.key;

    if (key === "Escape") {
      event.preventDefault();
      closeCalculator();
      return;
    }

    // Let a focused keypad button activate natively on Enter/Space.
    const isButton = (event.target as HTMLElement).tagName === "BUTTON";
    if (isButton && (key === "Enter" || key === " ")) return;

    const action = keyToAction(key);
    if (!action) return;

    // Keep register shortcuts (e.g. "/") from firing while the calculator owns focus.
    event.preventDefault();
    event.stopPropagation();
    dispatch(action);
  }

  return (
    <div
      data-state={open ? "open" : "closed"}
      inert={!open}
      className={cn(
        "bg-foreground/25 fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-[2px] transition-[opacity,visibility] duration-150 ease-out",
        open ? "visible opacity-100" : "pointer-events-none invisible opacity-0",
      )}
      onPointerDown={handleBackdropPointerDown}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-label="Calculator"
        tabIndex={-1}
        data-state={open ? "open" : "closed"}
        onKeyDown={handleKeyDown}
        className={cn(
          "bg-popover text-popover-foreground flex w-full max-w-xs flex-col overflow-hidden rounded-xl border shadow-lg outline-none",
          "transition-[opacity,transform] duration-150 ease-out",
          open ? "scale-100 opacity-100" : "scale-95 opacity-0",
        )}
      >
        <div className="flex items-center justify-between border-b px-3 py-2">
          <div className="flex items-center gap-2">
            <CalculatorIcon className="text-muted-foreground size-4" aria-hidden />
            <span className="text-sm font-medium">Calculator</span>
          </div>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label="Close calculator"
                onClick={closeCalculator}
              >
                <X className="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Close</TooltipContent>
          </Tooltip>
        </div>

        <div className="p-3">
          <Calculator state={state} onAction={dispatch} />
        </div>
      </div>
    </div>
  );
}

export { CalculatorPopup };
