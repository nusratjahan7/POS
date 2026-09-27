"use client";

/**
 * POS audio cues.
 *
 * The two supplied assets — the store scanner beep and the cash-register kaching —
 * are preloaded and decoded into memory, so playback on the scan path costs nothing.
 * The error and removal cues are synthesized: no assets were supplied for those, and
 * they deliberately do not imitate the scanner beep.
 *
 * The kaching is for a completed sale only (Module 11's payment success). It is never
 * played for a cart addition.
 */

export type SoundCue = "scan" | "sale" | "warning" | "remove";

const ASSETS: { cue: SoundCue; url: string }[] = [
  { cue: "scan", url: "/sounds/store-scanner-beep.mp3" },
  { cue: "sale", url: "/sounds/cash-register-kaching.mp3" },
];

/** Retail-appropriate levels — one constant each, easy to tune on the shop floor. */
const GAIN: Record<SoundCue, number> = { scan: 0.6, sale: 0.7, warning: 0.05, remove: 0.06 };

/** Rapid scanning must not stack cues: a minimum interval plus voice stealing. */
const MIN_INTERVAL_MS: Record<SoundCue, number> = {
  scan: 120,
  sale: 300,
  warning: 160,
  remove: 90,
};

const SYNTH: Record<"warning" | "remove", { from: number; to: number; seconds: number }> = {
  warning: { from: 320, to: 200, seconds: 0.17 },
  remove: { from: 520, to: 330, seconds: 0.11 },
};

let context: AudioContext | null = null;
let enabled = true;
let preloading: Promise<void> | null = null;

const raw = new Map<SoundCue, ArrayBuffer>();
const buffers = new Map<SoundCue, AudioBuffer>();
const playing = new Map<SoundCue, AudioScheduledSourceNode>();
const lastPlayed: Record<SoundCue, number> = { scan: 0, sale: 0, warning: 0, remove: 0 };
const warned = new Set<SoundCue>();

/** Kept in sync with the persisted POS setting by the register screen. */
export function configureSound(next: boolean): void {
  enabled = next;
}

function warnOnce(cue: SoundCue, message: string): void {
  if (warned.has(cue)) return;
  warned.add(cue);
  if (process.env.NODE_ENV !== "production") {
    console.warn(`[pos-sounds] ${message}`);
  }
}

/** Warm the asset cache ahead of the first scan. Safe to call repeatedly. */
export function preloadSounds(): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();

  preloading ??= Promise.all(
    ASSETS.map(async ({ cue, url }) => {
      try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(String(response.status));
        raw.set(cue, await response.arrayBuffer());
      } catch {
        // Stay silent rather than substituting a generated scanner sound.
        warnOnce(cue, `could not load ${url}; that cue stays silent`);
      }
    }),
  ).then(() => undefined);

  return preloading;
}

async function decode(cue: SoundCue): Promise<AudioBuffer | null> {
  if (!context) return null;
  const cached = buffers.get(cue);
  if (cached) return cached;

  const data = raw.get(cue);
  if (!data) return null;

  try {
    // decodeAudioData detaches its input, so hand it a copy and keep the original.
    const decoded = await context.decodeAudioData(data.slice(0));
    buffers.set(cue, decoded);
    return decoded;
  } catch {
    warnOnce(cue, `could not decode the ${cue} cue`);
    return null;
  }
}

/**
 * Create/resume the audio context and decode the assets. Call from a user gesture —
 * browsers block autoplay otherwise. Returns false and stays silent when unavailable.
 */
export async function initAudio(): Promise<boolean> {
  if (typeof window === "undefined") return false;

  try {
    const ctor =
      window.AudioContext ??
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!ctor) return false;

    context ??= new ctor();
    if (context.state === "suspended") await context.resume();
    if (context.state !== "running") return false;

    // Everything the first scan needs, in memory before it happens.
    await preloadSounds();
    for (const { cue } of ASSETS) {
      await decode(cue);
    }
    return true;
  } catch {
    return false;
  }
}

function canPlay(cue: SoundCue): boolean {
  if (!enabled || !context || context.state !== "running") return false;

  const now = performance.now();
  if (now - lastPlayed[cue] < MIN_INTERVAL_MS[cue]) return false;
  lastPlayed[cue] = now;
  return true;
}

/** Stop this cue's previous voice so rapid scans never overlap. */
function steal(cue: SoundCue): void {
  const previous = playing.get(cue);
  if (!previous) return;
  try {
    previous.stop();
  } catch {
    // Already finished.
  }
  playing.delete(cue);
}

function track(cue: SoundCue, source: AudioScheduledSourceNode): void {
  playing.set(cue, source);
  source.onended = () => {
    if (playing.get(cue) === source) playing.delete(cue);
  };
}

function playBuffer(cue: SoundCue): boolean {
  const buffer = buffers.get(cue);
  if (!context || !buffer) return false;

  steal(cue);
  const source = context.createBufferSource();
  source.buffer = buffer;
  const gain = context.createGain();
  gain.gain.value = GAIN[cue];
  source.connect(gain);
  gain.connect(context.destination);
  track(cue, source);
  source.start();
  return true;
}

function playSynth(cue: "warning" | "remove"): boolean {
  if (!context) return false;

  const shape = SYNTH[cue];
  const now = context.currentTime;

  steal(cue);
  const oscillator = context.createOscillator();
  const gain = context.createGain();
  oscillator.type = cue === "warning" ? "square" : "sine";
  oscillator.frequency.setValueAtTime(shape.from, now);
  oscillator.frequency.exponentialRampToValueAtTime(shape.to, now + shape.seconds);
  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(GAIN[cue], now + 0.008);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + shape.seconds);
  oscillator.connect(gain);
  gain.connect(context.destination);

  track(cue, oscillator);
  oscillator.start(now);
  oscillator.stop(now + shape.seconds + 0.02);
  return true;
}

function play(cue: SoundCue): boolean {
  if (!canPlay(cue)) return false;
  if (cue === "warning" || cue === "remove") return playSynth(cue);
  // A missing asset means silence, never a stand-in scanner sound.
  return playBuffer(cue);
}

/** Product added, barcode scan matched, or quantity increased. */
export function playScanBeep(): void {
  play("scan");
}

/** Sale paid and completed — the kaching. Module 11's payment success only. */
export function playSaleComplete(): void {
  play("sale");
}

/** Blocked action: stock limit, out of stock, or no product for the code. */
export function playWarning(): void {
  play("warning");
}

/** Line removed or quantity decreased. */
export function playRemove(): void {
  play("remove");
}
