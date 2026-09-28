"use client";

import * as React from "react";
import { Maximize, Minimize } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

function subscribe(onStoreChange: () => void) {
  document.addEventListener("fullscreenchange", onStoreChange);
  return () => document.removeEventListener("fullscreenchange", onStoreChange);
}

function getSnapshot() {
  return Boolean(document.fullscreenElement);
}

function getServerSnapshot() {
  return false;
}

/**
 * Puts the whole POS application into browser full screen. The document root is
 * the target (rather than the shell element) so portalled UI — dialogs,
 * dropdowns, toasts — stays inside the full-screen layer.
 *
 * State is read from the browser through `fullscreenchange`, so it always
 * reflects reality: exiting with Esc, F11, or the OS updates the button too.
 */
function FullscreenToggle() {
  const isFullscreen = React.useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const toggle = React.useCallback(async () => {
    const root = document.documentElement;
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      } else if (typeof root.requestFullscreen === "function") {
        await root.requestFullscreen();
      } else {
        throw new Error("Fullscreen API unavailable");
      }
    } catch {
      // Rejected requests (permissions policy, unsupported, not user-gesture) are
      // non-fatal — surface them and leave the app as-is.
      toast.error("Full screen is not available", {
        description: "Your browser or device blocked the request.",
      });
    }
  }, []);

  const label = isFullscreen ? "Exit full screen" : "Full screen";

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          aria-label={label}
          aria-pressed={isFullscreen}
          onClick={toggle}
        >
          {isFullscreen ? <Minimize className="size-4" /> : <Maximize className="size-4" />}
        </Button>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}

export { FullscreenToggle };
