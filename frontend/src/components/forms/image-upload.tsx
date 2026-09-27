"use client";

import * as React from "react";
import { ImageIcon, ImageUp, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { describeError, mediaUrl } from "@/lib/api/client";
import { uploadsApi } from "@/lib/api/uploads";
import { cn } from "@/lib/utils";

type ImageUploadProps = {
  value: string | null | undefined;
  /**
   * Persist the chosen URL (or `null` to clear it). May be async — while it runs
   * the control stays busy, and any thrown error is surfaced as a toast. The
   * caller owns the value, so the preview follows `value` on the next render.
   */
  onChange: (url: string | null) => void | Promise<void>;
  disabled?: boolean;
  label?: string;
  hint?: string;
  shape?: "square" | "rounded" | "circle";
  accept?: string;
  className?: string;
};

const SHAPE: Record<NonNullable<ImageUploadProps["shape"]>, string> = {
  square: "rounded-md",
  rounded: "rounded-lg",
  circle: "rounded-full",
};

/**
 * Controlled image picker: uploads to the media endpoint and delegates
 * persistence to the caller, so the same control serves create forms (keep the
 * URL in form state) and settings (save immediately).
 */
function ImageUpload({
  value,
  onChange,
  disabled = false,
  label,
  hint,
  shape = "rounded",
  accept = "image/png,image/jpeg,image/webp,image/gif",
  className,
}: ImageUploadProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [busy, setBusy] = React.useState(false);

  async function handleFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setBusy(true);
    try {
      const uploaded = await uploadsApi.uploadImage(file);
      await onChange(uploaded.url);
    } catch (cause) {
      toast.error(describeError(cause));
    } finally {
      setBusy(false);
    }
  }

  async function handleRemove() {
    setBusy(true);
    try {
      await onChange(null);
    } catch (cause) {
      toast.error(describeError(cause));
    } finally {
      setBusy(false);
    }
  }

  const resolved = mediaUrl(value);

  return (
    <div className={cn("flex flex-wrap items-center gap-4", className)}>
      <div
        className={cn(
          "bg-muted flex size-20 shrink-0 items-center justify-center overflow-hidden border",
          SHAPE[shape],
        )}
      >
        {resolved ? (
          // Uploaded media is served from the API origin, so next/image would
          // need remote-pattern configuration for no benefit here.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={resolved} alt="" className="size-full object-contain" />
        ) : (
          <ImageIcon className="text-muted-foreground size-6" aria-hidden />
        )}
      </div>

      <div className="flex flex-col gap-2">
        {label ? <p className="text-sm font-medium">{label}</p> : null}
        {hint ? <p className="text-muted-foreground text-xs">{hint}</p> : null}

        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="file"
            accept={accept}
            className="hidden"
            onChange={handleFile}
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={disabled || busy}
            onClick={() => inputRef.current?.click()}
          >
            {busy ? <Spinner /> : <ImageUp className="size-4" />}
            {resolved ? "Replace" : "Upload"}
          </Button>
          {resolved ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={disabled || busy}
              onClick={() => void handleRemove()}
            >
              <Trash2 className="size-4" />
              Remove
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export { ImageUpload };
