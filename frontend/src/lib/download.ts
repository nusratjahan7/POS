/**
 * Trigger a browser download of an in-memory Blob.
 *
 * The object URL is revoked on the next tick so the download has already been
 * handed to the browser before the URL disappears.
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}
