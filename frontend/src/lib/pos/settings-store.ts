"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

/** Per-terminal POS preferences (sound on/off). Persisted like the cart. */
type PosSettingsState = {
  soundEnabled: boolean;
  setSoundEnabled: (enabled: boolean) => void;
};

export const usePosSettings = create<PosSettingsState>()(
  persist(
    (set) => ({
      soundEnabled: true,
      setSoundEnabled: (soundEnabled) => set({ soundEnabled }),
    }),
    {
      name: "pos-settings",
      // Rehydrated manually on mount (hydration-safe).
      skipHydration: true,
    },
  ),
);
