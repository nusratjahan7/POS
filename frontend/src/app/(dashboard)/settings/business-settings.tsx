"use client";

import * as React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ImageUp, ShieldAlert, Store, Trash2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { SettingsCard } from "@/app/(dashboard)/settings/settings-card";
import { SettingsSkeleton } from "@/app/(dashboard)/settings/settings-skeleton";
import { Can, useCan } from "@/components/auth/can";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ErrorState } from "@/components/ui/error-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, describeError, mediaUrl } from "@/lib/api/client";
import { businessApi, uploadsApi, type Business } from "@/lib/api/settings";
import { cn } from "@/lib/utils";

const CURRENCIES = [
  "BDT",
  "USD",
  "EUR",
  "GBP",
  "INR",
  "AED",
  "SAR",
  "MYR",
  "SGD",
  "PKR",
  "NPR",
  "LKR",
  "JPY",
  "CNY",
  "AUD",
  "CAD",
];

const FALLBACK_TIMEZONES = [
  "UTC",
  "Asia/Dhaka",
  "Asia/Kolkata",
  "Asia/Dubai",
  "Asia/Singapore",
  "Europe/London",
  "Europe/Berlin",
  "America/New_York",
  "America/Los_Angeles",
  "Australia/Sydney",
];

/** The full IANA list when the runtime exposes it, always including the current value. */
function timezoneOptions(current: string): string[] {
  const supported = (Intl as { supportedValuesOf?: (key: string) => string[] }).supportedValuesOf;
  let zones: string[] = [];
  if (typeof supported === "function") {
    try {
      zones = supported("timeZone");
    } catch {
      zones = [];
    }
  }
  if (zones.length === 0) zones = FALLBACK_TIMEZONES;
  return zones.includes(current) ? zones : [current, ...zones];
}

const schema = z.object({
  name: z.string().min(1, "A business name is required.").max(160, "Use at most 160 characters."),
  phone: z.string().max(32, "Use at most 32 characters."),
  email: z.union([z.literal(""), z.string().email("Enter a valid email address.")]),
  address: z.string().max(255, "Use at most 255 characters."),
  tax_label: z.string().min(1, "Give the tax a label.").max(32, "Use at most 32 characters."),
  default_tax_rate: z.coerce
    .number()
    .min(0, "Cannot be negative.")
    .max(100, "Cannot exceed 100."),
});

type FormValues = z.infer<typeof schema>;

export function BusinessSettings() {
  const canRead = useCan("business:read");
  const query = useQuery({
    queryKey: ["business"],
    queryFn: () => businessApi.get(),
    enabled: canRead,
  });

  if (!canRead) {
    return (
      <SettingsCard title="Business profile" description="The trading entity and its tax settings.">
        <ErrorState
          icon={ShieldAlert}
          title="You cannot view the business profile"
          description="This section requires the business:read permission."
        />
      </SettingsCard>
    );
  }

  if (query.isPending) {
    return (
      <SettingsSkeleton
        title="Business profile"
        description="The trading entity and its tax settings."
        rows={4}
      />
    );
  }

  if (query.error) {
    return (
      <SettingsCard title="Business profile" description="The trading entity and its tax settings.">
        <ErrorState
          title="Could not load the business profile"
          description={describeError(query.error)}
          action={
            <Button variant="outline" onClick={() => void query.refetch()}>
              Try again
            </Button>
          }
        />
      </SettingsCard>
    );
  }

  return <BusinessForm business={query.data} />;
}

function BusinessForm({ business }: { business: Business }) {
  const canWrite = useCan("business:write");
  const queryClient = useQueryClient();

  const [currency, setCurrency] = React.useState(business.currency);
  const [timezone, setTimezone] = React.useState(business.timezone);
  const [taxEnabled, setTaxEnabled] = React.useState(business.tax_enabled);
  const [taxInclusive, setTaxInclusive] = React.useState(business.tax_inclusive);
  const [baseline, setBaseline] = React.useState({
    currency: business.currency,
    timezone: business.timezone,
    taxEnabled: business.tax_enabled,
    taxInclusive: business.tax_inclusive,
  });
  const [formError, setFormError] = React.useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: business.name,
      phone: business.phone ?? "",
      email: business.email ?? "",
      address: business.address ?? "",
      tax_label: business.tax_label,
      default_tax_rate: Number(business.default_tax_rate),
    },
  });

  const zones = React.useMemo(() => timezoneOptions(business.timezone), [business.timezone]);
  const currencies = React.useMemo(
    () => (CURRENCIES.includes(business.currency) ? CURRENCIES : [business.currency, ...CURRENCIES]),
    [business.currency],
  );

  const localDirty =
    currency !== baseline.currency ||
    timezone !== baseline.timezone ||
    taxEnabled !== baseline.taxEnabled ||
    taxInclusive !== baseline.taxInclusive;
  const dirty = isDirty || localDirty;

  async function onSubmit(values: FormValues) {
    setFormError(null);
    try {
      await businessApi.update({
        name: values.name.trim(),
        phone: values.phone.trim() || null,
        email: values.email.trim() || null,
        address: values.address.trim() || null,
        currency,
        timezone,
        tax_enabled: taxEnabled,
        tax_inclusive: taxInclusive,
        tax_label: values.tax_label.trim(),
        default_tax_rate: values.default_tax_rate.toFixed(3),
      });
      toast.success("Business settings saved");
      setBaseline({ currency, timezone, taxEnabled, taxInclusive });
      reset(values);
      void queryClient.invalidateQueries({ queryKey: ["business"] });
    } catch (cause) {
      setFormError(describeError(cause));
      if (cause instanceof ApiError) {
        for (const [field, message] of Object.entries(cause.fieldErrors)) {
          if (field === "name" || field === "email" || field === "phone" || field === "address") {
            setError(field, { message });
          }
        }
      }
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-6">
      <SettingsCard
        title="Business profile"
        description="Shown on receipts and reports. The logo is uploaded to your own storage."
      >
        <div className="flex flex-col gap-6">
          {formError ? (
            <Alert variant="destructive">
              <AlertTitle>Could not save the business settings</AlertTitle>
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          ) : null}

          <LogoField business={business} canWrite={canWrite} />

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Business name" htmlFor="business-name" error={errors.name?.message}>
              <Input
                id="business-name"
                autoComplete="organization"
                placeholder="Acme Retail Ltd."
                disabled={!canWrite}
                {...register("name")}
              />
            </Field>

            <Field label="Phone" htmlFor="business-phone" error={errors.phone?.message}>
              <Input
                id="business-phone"
                autoComplete="tel"
                placeholder="Optional"
                disabled={!canWrite}
                {...register("phone")}
              />
            </Field>

            <Field label="Email" htmlFor="business-email" error={errors.email?.message}>
              <Input
                id="business-email"
                type="email"
                autoComplete="email"
                placeholder="hello@example.com"
                disabled={!canWrite}
                {...register("email")}
              />
            </Field>

            <Field
              label="Address"
              htmlFor="business-address"
              error={errors.address?.message}
              className="sm:col-span-2"
            >
              <Textarea
                id="business-address"
                rows={2}
                placeholder="Street, city, postcode"
                disabled={!canWrite}
                {...register("address")}
              />
            </Field>
          </div>
        </div>
      </SettingsCard>

      <SettingsCard
        title="Regional & tax"
        description="Currency, time zone and how tax is named and applied to prices."
      >
        <div className="flex flex-col gap-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              label="Currency"
              htmlFor="business-currency"
              hint="ISO 4217 code used for all amounts."
            >
              <Select value={currency} onValueChange={setCurrency} disabled={!canWrite}>
                <SelectTrigger id="business-currency" className="w-full">
                  <SelectValue placeholder="Select currency" />
                </SelectTrigger>
                <SelectContent>
                  {currencies.map((code) => (
                    <SelectItem key={code} value={code}>
                      {code}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            <Field
              label="Time zone"
              htmlFor="business-timezone"
              hint="Used to group sales by business day."
            >
              <Select value={timezone} onValueChange={setTimezone} disabled={!canWrite}>
                <SelectTrigger id="business-timezone" className="w-full">
                  <SelectValue placeholder="Select time zone" />
                </SelectTrigger>
                <SelectContent className="max-h-72">
                  {zones.map((zone) => (
                    <SelectItem key={zone} value={zone}>
                      {zone}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            <Field label="Tax label" htmlFor="business-tax-label" error={errors.tax_label?.message}>
              <Input
                id="business-tax-label"
                placeholder="VAT, GST, Tax"
                disabled={!canWrite}
                {...register("tax_label")}
              />
            </Field>

            <Field
              label="Default tax rate (%)"
              htmlFor="business-tax-rate"
              error={errors.default_tax_rate?.message}
              hint="A percentage, e.g. 15 for 15%."
            >
              <Input
                id="business-tax-rate"
                type="number"
                min="0"
                max="100"
                step="0.001"
                inputMode="decimal"
                disabled={!canWrite}
                {...register("default_tax_rate")}
              />
            </Field>
          </div>

          <div className="flex flex-col gap-3 rounded-md border p-3">
            <label
              className={cn(
                "flex cursor-pointer items-center gap-2.5",
                (!canWrite || isSubmitting) && "cursor-not-allowed opacity-60",
              )}
            >
              <Checkbox
                checked={taxEnabled}
                disabled={!canWrite || isSubmitting}
                onCheckedChange={(state) => setTaxEnabled(state === true)}
              />
              <span className="flex flex-col">
                <span className="text-sm font-medium">Charge tax on sales</span>
                <span className="text-muted-foreground text-xs">
                  Turn off if this business is not tax-registered.
                </span>
              </span>
            </label>

            <label
              className={cn(
                "flex cursor-pointer items-center gap-2.5",
                (!canWrite || !taxEnabled || isSubmitting) && "cursor-not-allowed opacity-60",
              )}
            >
              <Checkbox
                checked={taxInclusive}
                disabled={!canWrite || !taxEnabled || isSubmitting}
                onCheckedChange={(state) => setTaxInclusive(state === true)}
              />
              <span className="flex flex-col">
                <span className="text-sm font-medium">Prices include tax</span>
                <span className="text-muted-foreground text-xs">
                  When off, tax is added to the price at checkout.
                </span>
              </span>
            </label>
          </div>
        </div>
      </SettingsCard>

      <div className="flex items-center justify-end gap-3">
        {!canWrite ? (
          <p className="text-muted-foreground mr-auto text-xs">
            Your role can view these settings but not change them.
          </p>
        ) : null}
        <Can permission="business:write">
          <Button type="submit" disabled={!dirty || isSubmitting}>
            {isSubmitting ? <Spinner /> : null}
            Save changes
          </Button>
        </Can>
      </div>
    </form>
  );
}

function LogoField({ business, canWrite }: { business: Business; canWrite: boolean }) {
  const queryClient = useQueryClient();
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [logoUrl, setLogoUrl] = React.useState(business.logo_url);
  const [busy, setBusy] = React.useState(false);

  async function handleFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setBusy(true);
    try {
      const uploaded = await uploadsApi.uploadImage(file);
      const updated = await businessApi.update({ logo_url: uploaded.url });
      setLogoUrl(updated.logo_url);
      toast.success("Logo updated");
      void queryClient.invalidateQueries({ queryKey: ["business"] });
    } catch (cause) {
      toast.error(describeError(cause));
    } finally {
      setBusy(false);
    }
  }

  async function removeLogo() {
    setBusy(true);
    try {
      const updated = await businessApi.update({ logo_url: null });
      setLogoUrl(updated.logo_url);
      toast.success("Logo removed");
      void queryClient.invalidateQueries({ queryKey: ["business"] });
    } catch (cause) {
      toast.error(describeError(cause));
    } finally {
      setBusy(false);
    }
  }

  const resolved = mediaUrl(logoUrl);

  return (
    <div className="flex flex-wrap items-center gap-4">
      <div className="bg-muted flex size-20 shrink-0 items-center justify-center overflow-hidden rounded-lg border">
        {resolved ? (
          // Uploaded media is served from the API origin, so a plain <img> avoids
          // configuring remote patterns for next/image.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={resolved} alt="Business logo" className="size-full object-contain" />
        ) : (
          <Store className="text-muted-foreground size-7" aria-hidden />
        )}
      </div>

      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium">Logo</p>
        <p className="text-muted-foreground text-xs">
          PNG, JPEG, WebP or GIF, up to 5&nbsp;MB. Shown on receipts.
        </p>
        <Can permission="business:write">
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif"
              className="hidden"
              onChange={handleFile}
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={busy || !canWrite}
              onClick={() => inputRef.current?.click()}
            >
              {busy ? <Spinner /> : <ImageUp className="size-4" />}
              {logoUrl ? "Replace" : "Upload"}
            </Button>
            {logoUrl ? (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled={busy || !canWrite}
                onClick={removeLogo}
              >
                <Trash2 className="size-4" />
                Remove
              </Button>
            ) : null}
          </div>
        </Can>
      </div>
    </div>
  );
}
