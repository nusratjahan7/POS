"use client";

import { Calculator as CalculatorIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useCalculator } from "@/lib/pos/calculator-store";

/**
 * Header trigger for the calculator. Any other surface can reuse this button, or
 * call `useCalculator().openCalculator()` directly.
 */
function CalculatorButton() {
  const open = useCalculator((selector) => selector.open);
  const toggleCalculator = useCalculator((selector) => selector.toggleCalculator);

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          data-calculator-trigger
          aria-label="Calculator"
          aria-expanded={open}
          onClick={toggleCalculator}
        >
          <CalculatorIcon className="size-4" />
        </Button>
      </TooltipTrigger>
      <TooltipContent>Calculator</TooltipContent>
    </Tooltip>
  );
}

export { CalculatorButton };
