import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

class FakeSource {
  onended: (() => void) | null = null;
  started = 0;
  connect() {}
  start() {
    this.started += 1;
  }
  stop() {
    this.onended?.();
  }
}

class FakeParam {
  setValueAtTime() {}
  exponentialRampToValueAtTime() {}
}

class FakeOscillator extends FakeSource {
  type = "sine";
  frequency = new FakeParam();
}

class FakeGain {
  gain = {
    value: 0,
    setValueAtTime: () => {},
    exponentialRampToValueAtTime: () => {},
  };
  connect() {}
}

class FakeAudioContext {
  static created: FakeAudioContext[] = [];
  state = "running";
  currentTime = 0;
  destination = { name: "destination" };
  sources: FakeSource[] = [];

  constructor() {
    FakeAudioContext.created.push(this);
  }

  async resume() {}

  createBufferSource() {
    const source = new FakeSource();
    this.sources.push(source);
    return source;
  }

  createOscillator() {
    const oscillator = new FakeOscillator();
    this.sources.push(oscillator);
    return oscillator;
  }

  createGain() {
    return new FakeGain();
  }

  async decodeAudioData() {
    return { duration: 0.1 } as unknown as AudioBuffer;
  }
}

async function load(options: { fetchFails?: boolean } = {}) {
  vi.resetModules();
  FakeAudioContext.created = [];

  Object.assign(globalThis, { AudioContext: FakeAudioContext });
  Object.assign(globalThis, {
    fetch: vi.fn(async () =>
      options.fetchFails
        ? { ok: false, status: 404, arrayBuffer: async () => new ArrayBuffer(0) }
        : { ok: true, status: 200, arrayBuffer: async () => new ArrayBuffer(8) },
    ),
  });

  return import("./sounds");
}

function sourcesStarted(): number {
  return FakeAudioContext.created
    .flatMap((context) => context.sources)
    .filter((source) => source.started > 0).length;
}

beforeEach(() => {
  vi.spyOn(console, "warn").mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("pos sounds", () => {
  it("plays a single scanner beep for rapid additions", async () => {
    const sounds = await load();
    await sounds.initAudio();

    sounds.playScanBeep();
    sounds.playScanBeep();
    sounds.playScanBeep();

    expect(sourcesStarted()).toBe(1);
  });

  it("keeps the sale kaching separate from the scanner beep", async () => {
    const sounds = await load();
    await sounds.initAudio();

    sounds.playScanBeep();
    sounds.playSaleComplete();

    expect(sourcesStarted()).toBe(2);
  });

  it("stays silent when the terminal has sound turned off", async () => {
    const sounds = await load();
    await sounds.initAudio();
    sounds.configureSound(false);

    sounds.playScanBeep();
    sounds.playSaleComplete();
    sounds.playWarning();

    expect(sourcesStarted()).toBe(0);
  });

  it("does not substitute a sound when an asset is missing", async () => {
    const sounds = await load({ fetchFails: true });
    await sounds.initAudio();

    expect(() => sounds.playScanBeep()).not.toThrow();
    expect(() => sounds.playSaleComplete()).not.toThrow();
    expect(sourcesStarted()).toBe(0);
  });

  it("still gives error feedback when an asset is missing", async () => {
    const sounds = await load({ fetchFails: true });
    await sounds.initAudio();

    sounds.playWarning();

    expect(sourcesStarted()).toBe(1);
  });
});
