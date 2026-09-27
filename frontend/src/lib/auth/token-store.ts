/**
 * The access token is held in memory only, never in localStorage or
 * sessionStorage — those are readable by any script on the page, so an XSS bug
 * would turn into a stolen session.
 *
 * The refresh token is an httpOnly cookie the browser never exposes to
 * JavaScript. A page reload therefore restores the session by calling
 * `/auth/refresh` (see `refreshSession` in `lib/api/client.ts`).
 */

type Listener = () => void;

let accessToken: string | null = null;
const listeners = new Set<Listener>();

function emit(): void {
  for (const listener of listeners) listener();
}

export const tokenStore = {
  get(): string | null {
    return accessToken;
  },

  set(token: string | null): void {
    if (token === accessToken) return;
    accessToken = token;
    emit();
  },

  clear(): void {
    tokenStore.set(null);
  },

  /** Lets React components observe token changes via `useSyncExternalStore`. */
  subscribe(listener: Listener): () => void {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  },
};
