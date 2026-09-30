"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Printer, Search, ShieldAlert, Volume2, VolumeX } from "lucide-react";
import { toast } from "sonner";

import { PosCart } from "@/app/(dashboard)/register/pos-cart";
import { CashMovementDialog } from "@/app/(dashboard)/register/cash-movement-dialog";
import { CloseRegisterDialog } from "@/app/(dashboard)/register/close-register-dialog";
import { PosDiscountDialog, PosHeldListDialog, PosHoldDialog } from "@/app/(dashboard)/register/pos-dialogs";
import { PosCustomerDialog } from "@/app/(dashboard)/register/pos-customer-dialog";
import { OpenRegisterDialog } from "@/app/(dashboard)/register/open-register-dialog";
import { PosPaymentDialog } from "@/app/(dashboard)/register/pos-payment-dialog";
import { PosProductGrid } from "@/app/(dashboard)/register/pos-product-grid";
import { RegisterSessionBar } from "@/app/(dashboard)/register/register-session-bar";
import { InvoicePreviewDialog } from "@/components/invoice/invoice-preview-dialog";
import { useCan } from "@/components/auth/can";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { posApi, type PosProduct } from "@/lib/api/pos";
import { registerSessionsApi } from "@/lib/api/register-sessions";
import { branchesApi } from "@/lib/api/rbac";
import { type Sale } from "@/lib/api/sales";
import { businessApi, registersApi } from "@/lib/api/settings";
import { computeTotals, useCartStore, type SyncResult } from "@/lib/pos/cart-store";
import { usePosSettings } from "@/lib/pos/settings-store";
import {
  configureSound,
  initAudio,
  playRemove,
  playSaleComplete,
  playScanBeep,
  playWarning,
  preloadSounds,
} from "@/lib/pos/sounds";
import { formatMoney, formatQuantity } from "@/lib/format";
import { cn } from "@/lib/utils";

const ALL = "all";
const EMPTY_SYNC: SyncResult = { adjusted: [], removed: [] };

export function RegisterClient() {
  const canSell = useCan("sales:create");
  const canReadBranches = useCan("branches:read");
  const canOperate = useCan("registers:operate");

  // Cart + settings are persisted; rehydrate after mount so the server and the
  // first client render agree (no hydration mismatch).
  React.useEffect(() => {
    void useCartStore.persist.rehydrate();
    void usePosSettings.persist.rehydrate();
  }, []);

  const soundEnabled = usePosSettings((state) => state.soundEnabled);
  const setSoundEnabled = usePosSettings((state) => state.setSoundEnabled);

  // Keep the audio module in step with the persisted preference.
  React.useEffect(() => {
    configureSound(soundEnabled);
  }, [soundEnabled]);

  // Warm the audio cache so the first scan is instant.
  React.useEffect(() => {
    void preloadSounds();
  }, []);

  // Browsers block autoplay — create the audio context on the first gesture.
  React.useEffect(() => {
    function onFirstGesture() {
      void initAudio();
      window.removeEventListener("pointerdown", onFirstGesture);
      window.removeEventListener("keydown", onFirstGesture);
    }
    window.addEventListener("pointerdown", onFirstGesture);
    window.addEventListener("keydown", onFirstGesture);
    return () => {
      window.removeEventListener("pointerdown", onFirstGesture);
      window.removeEventListener("keydown", onFirstGesture);
    };
  }, []);

  const lines = useCartStore((state) => state.lines);
  const customer = useCartStore((state) => state.customer);
  const orderDiscount = useCartStore((state) => state.orderDiscount);
  const held = useCartStore((state) => state.held);
  const branchId = useCartStore((state) => state.branchId);
  const registerId = useCartStore((state) => state.registerId);

  const addLine = useCartStore((state) => state.addLine);
  const setQuantity = useCartStore((state) => state.setQuantity);
  const setLineDiscount = useCartStore((state) => state.setLineDiscount);
  const removeLine = useCartStore((state) => state.removeLine);
  const setCustomer = useCartStore((state) => state.setCustomer);
  const setOrderDiscount = useCartStore((state) => state.setOrderDiscount);
  const setBranch = useCartStore((state) => state.setBranch);
  const setRegister = useCartStore((state) => state.setRegister);
  const syncLimits = useCartStore((state) => state.syncLimits);
  const clear = useCartStore((state) => state.clear);
  const hold = useCartStore((state) => state.hold);
  const resume = useCartStore((state) => state.resume);
  const dropHeld = useCartStore((state) => state.dropHeld);

  const searchRef = React.useRef<HTMLInputElement>(null);
  const pendingScans = React.useRef<Set<string>>(new Set());
  const [search, setSearch] = React.useState("");
  const [query, setQuery] = React.useState("");
  const [category, setCategory] = React.useState(ALL);

  const [customerOpen, setCustomerOpen] = React.useState(false);
  const [discountOpen, setDiscountOpen] = React.useState(false);
  const [holdOpen, setHoldOpen] = React.useState(false);
  const [heldOpen, setHeldOpen] = React.useState(false);
  const [checkoutOpen, setCheckoutOpen] = React.useState(false);
  const [registerOpen, setRegisterOpen] = React.useState(false);
  const [closeOpen, setCloseOpen] = React.useState(false);
  const [cashDirection, setCashDirection] = React.useState<"in" | "out" | null>(null);
  const [lastSale, setLastSale] = React.useState<Sale | null>(null);
  const [invoiceSale, setInvoiceSale] = React.useState<Sale | null>(null);

  const queryClient = useQueryClient();

  // Fast, cashier-friendly debounce.
  React.useEffect(() => {
    const timer = setTimeout(() => setQuery(search), 150);
    return () => clearTimeout(timer);
  }, [search]);

  const branchesQuery = useQuery({
    queryKey: ["branches", "options"],
    queryFn: () => branchesApi.options(),
    enabled: canSell && canReadBranches,
  });
  const categoriesQuery = useQuery({
    queryKey: ["pos", "categories"],
    queryFn: () => posApi.categories(),
    enabled: canSell,
  });
  const businessQuery = useQuery({
    queryKey: ["business"],
    queryFn: () => businessApi.get(),
    enabled: canSell,
  });

  const branches = branchesQuery.data ?? [];
  const effectiveBranch = branchId ?? branches[0]?.id ?? "";

  // The branch's tills, and the one this cart will be rung on.
  const registersQuery = useQuery({
    queryKey: ["registers", "options", effectiveBranch],
    queryFn: () => registersApi.list({ branch_id: effectiveBranch, page_size: 100 }),
    enabled: canSell && Boolean(effectiveBranch),
  });
  const registers = registersQuery.data?.items ?? [];
  const effectiveRegister =
    registerId && registers.some((register) => register.id === registerId)
      ? registerId
      : (registers[0]?.id ?? "");

  // The open session (if any) for that till — the sell gate and drawer figures.
  const sessionQuery = useQuery({
    queryKey: ["register-session", effectiveRegister],
    queryFn: () => registerSessionsApi.current(effectiveRegister),
    enabled: canSell && Boolean(effectiveRegister),
  });
  const sessionDetail = sessionQuery.data ?? null;

  const catalogQuery = useQuery({
    queryKey: ["pos", "catalog", { query, category, branch: effectiveBranch }],
    queryFn: () =>
      posApi.catalog({
        search: query || undefined,
        category_id: category === ALL ? undefined : category,
        branch_id: effectiveBranch || undefined,
      }),
    enabled: canSell,
  });

  const products = catalogQuery.data?.items ?? [];
  const currency = businessQuery.data?.currency ?? "USD";
  const tax = {
    enabled: businessQuery.data?.tax_enabled ?? false,
    inclusive: businessQuery.data?.tax_inclusive ?? true,
    rate: Number(businessQuery.data?.default_tax_rate ?? "0"),
  };
  const totals = React.useMemo(
    () => computeTotals(lines, orderDiscount, tax),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [lines, orderDiscount, tax.enabled, tax.inclusive, tax.rate],
  );

  const cartQuantities = React.useMemo(() => {
    const map: Record<string, number> = {};
    for (const line of lines) map[line.productId] = line.quantity;
    return map;
  }, [lines]);

  function limitMessage(available: number): string {
    return `Only ${formatQuantity(available)} available in stock.`;
  }

  /** The one guard every add path goes through. */
  function tryAdd(product: PosProduct, quantity = 1): boolean {
    const result = addLine(
      {
        productId: product.id,
        name: product.name,
        sku: product.sku,
        unit: product.unit,
        unitPrice: Number(product.discount_price ?? product.selling_price),
        limit: Number(product.stock_quantity),
      },
      quantity,
    );

    if (result.ok) {
      playScanBeep();
      return true;
    }

    playWarning();
    toast.error(
      result.reason === "out_of_stock"
        ? "Out of stock at this branch."
        : limitMessage(result.available),
    );
    return false;
  }

  function changeQuantity(productId: string, desired: number) {
    const line = lines.find((item) => item.productId === productId);
    if (!line) return;

    if (desired > line.limit) {
      // Clamp to the limit and warn (friendlier than rejecting keystrokes).
      setQuantity(productId, desired);
      playWarning();
      toast.error(limitMessage(line.limit));
      return;
    }

    const result = setQuantity(productId, desired);
    if (!result.ok) {
      playWarning();
      return;
    }
    if (desired >= line.quantity) playScanBeep();
    else playRemove();
  }

  function removeWithSound(productId: string) {
    removeLine(productId);
    playRemove();
  }

  function clearWithSound() {
    clear();
    playRemove();
  }

  async function refreshLimits(branch: string): Promise<SyncResult> {
    const ids = lines.map((line) => line.productId);
    if (ids.length === 0 || !branch) return EMPTY_SYNC;
    try {
      const stocks = await posApi.stock({ branch_id: branch, ids });
      const limits: Record<string, number> = {};
      for (const row of stocks) limits[row.product_id] = Number(row.stock_quantity);
      return syncLimits(limits);
    } catch {
      return EMPTY_SYNC;
    }
  }

  async function switchBranch(value: string) {
    setBranch(value);
    const report = await refreshLimits(value);
    const name = branches.find((branch) => branch.id === value)?.name ?? "this branch";
    for (const item of report.adjusted) {
      if (item.to === 0) {
        toast.warning(`${item.name} removed — no stock at ${name}.`);
      } else {
        toast.warning(`${item.name} reduced to ${formatQuantity(item.to)} — all ${name} has.`);
      }
    }
  }

  async function openCheckout() {
    // A sale is always rung against an open till.
    if (!sessionDetail) {
      toast.error("Open the register before ringing a sale.");
      if (canOperate) setRegisterOpen(true);
      return;
    }
    // Re-validate the cap against live stock before showing the summary.
    const report = await refreshLimits(effectiveBranch);
    for (const item of report.adjusted) {
      if (item.to === 0) toast.warning(`${item.name} is out of stock and was removed.`);
      else toast.warning(`${item.name} was reduced to ${formatQuantity(item.to)}.`);
    }
    setCheckoutOpen(true);
  }

  /** The sale is committed: this is where the kaching belongs. */
  function handleSaleComplete(sale: Sale) {
    playSaleComplete();
    setLastSale(sale);
    clear();
    void queryClient.invalidateQueries({ queryKey: ["pos", "catalog"] });
    void queryClient.invalidateQueries({ queryKey: ["pos", "categories"] });
    void queryClient.invalidateQueries({ queryKey: ["customers"] });
    // The sale added cash to the drawer.
    void queryClient.invalidateQueries({ queryKey: ["register-session", effectiveRegister] });
  }

  function handleSearchKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key !== "Enter") return;
    const term = search.trim();
    if (!term) return;

    const lowered = term.toLowerCase();
    // Barcode scanners type fast then Enter — match barcode/SKU exactly first.
    const exact = products.find(
      (product) =>
        product.sku.toLowerCase() === lowered ||
        (product.barcode !== null && product.barcode.toLowerCase() === lowered),
    );

    if (exact) {
      if (tryAdd(exact)) {
        setSearch("");
        setQuery("");
      }
      return;
    }

    void resolveByCode(term);
  }

  async function resolveByCode(term: string) {
    const key = term.toLowerCase();
    if (pendingScans.current.has(key)) return;
    pendingScans.current.add(key);
    try {
      const result = await posApi.catalog({
        barcode: term,
        branch_id: effectiveBranch || undefined,
      });
      const hit = result.items[0];
      if (hit) {
        if (tryAdd(hit)) {
          setSearch("");
          setQuery("");
        }
      } else {
        playWarning();
        toast.error("No product matches that code.");
      }
    } catch {
      toast.error("Could not look up that code.");
    } finally {
      pendingScans.current.delete(key);
    }
  }

  // Keyboard shortcuts — minimal mouse dependency.
  React.useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const typing = ["INPUT", "TEXTAREA"].includes(
        (document.activeElement?.tagName ?? "").toUpperCase(),
      );

      if (event.key === "/" && !typing) {
        event.preventDefault();
        searchRef.current?.focus();
        return;
      }
      if (event.key === "F2") {
        event.preventDefault();
        if (lines.length > 0) void openCheckout();
        return;
      }
      if (event.key === "F3") {
        event.preventDefault();
        setCustomerOpen(true);
        return;
      }
      if (event.key === "F4") {
        event.preventDefault();
        if (lines.length > 0) setHoldOpen(true);
        return;
      }
      if (event.key === "Escape" && typing) {
        searchRef.current?.blur();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lines.length, effectiveBranch]);

  if (!canSell) {
    return (
      <div className="flex flex-1 p-4 sm:p-6">
        <Card className="w-full">
          <CardContent>
            <ErrorState
              icon={ShieldAlert}
              title="You do not have access to the register"
              description="The till requires the sales:create permission. Ask an administrator to grant it to your role."
            />
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col lg:h-[calc(100svh_-_3.5rem)] lg:min-h-0">
      <RegisterSessionBar
        registers={registers}
        registerId={effectiveRegister}
        onRegisterChange={setRegister}
        detail={sessionDetail}
        isLoading={registersQuery.isPending || sessionQuery.isPending}
        canOperate={canOperate}
        currency={currency}
        onOpen={() => setRegisterOpen(true)}
        onCashIn={() => setCashDirection("in")}
        onCashOut={() => setCashDirection("out")}
        onCloseRegister={() => setCloseOpen(true)}
      />

      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        {/* Left: search, categories, products */}
      <section className="flex min-h-0 flex-1 flex-col">
        <div className="flex flex-col gap-3 border-b px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative min-w-56 flex-1">
              <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2" />
              <Input
                ref={searchRef}
                autoFocus
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                onKeyDown={handleSearchKeyDown}
                placeholder="Scan barcode, or search name / SKU…"
                aria-label="Search products"
                className="h-10 pl-8"
              />
            </div>

            <Select
              value={effectiveBranch}
              onValueChange={(value) => void switchBranch(value)}
              disabled={!canReadBranches || branches.length === 0}
            >
              <SelectTrigger className="h-10 w-44" aria-label="Branch">
                <SelectValue placeholder="Branch" />
              </SelectTrigger>
              <SelectContent>
                {branches.map((branch) => (
                  <SelectItem key={branch.id} value={branch.id}>
                    {branch.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button
              type="button"
              variant="outline"
              size="icon"
              className="size-10"
              aria-label={soundEnabled ? "Mute register sounds" : "Unmute register sounds"}
              title={soundEnabled ? "Sound on" : "Sound off"}
              onClick={() => {
                const next = !soundEnabled;
                setSoundEnabled(next);
                if (next) void initAudio();
              }}
            >
              {soundEnabled ? <Volume2 className="size-4" /> : <VolumeX className="size-4" />}
            </Button>
          </div>

          <div className="flex items-center gap-2 overflow-x-auto pb-0.5">
            <CategoryChip active={category === ALL} onClick={() => setCategory(ALL)}>
              All
            </CategoryChip>
            {(categoriesQuery.data ?? []).map((item) => (
              <CategoryChip
                key={item.id}
                active={category === item.id}
                onClick={() => setCategory(item.id)}
              >
                {item.name}
              </CategoryChip>
            ))}
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          <PosProductGrid
            products={products}
            cartQuantities={cartQuantities}
            currency={currency}
            isLoading={catalogQuery.isPending}
            error={catalogQuery.error}
            onRetry={() => void catalogQuery.refetch()}
            onAdd={tryAdd}
          />
        </div>
      </section>

      {/* Right: cart */}
      <aside className="flex w-full shrink-0 flex-col border-t bg-card lg:w-[380px] lg:border-t-0 lg:border-l">
        {lastSale ? (
          <div className="bg-muted/50 flex items-center justify-between gap-2 border-b px-4 py-2 text-xs">
            <span className="truncate">
              Last sale <span className="font-mono font-semibold">{lastSale.sale_number}</span>
              {Number(lastSale.change_amount) > 0
                ? ` · change ${formatMoney(lastSale.change_amount, currency)}`
                : ""}
              {Number(lastSale.due) > 0 ? ` · due ${formatMoney(lastSale.due, currency)}` : ""}
            </span>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="shrink-0"
              onClick={() => setInvoiceSale(lastSale)}
            >
              <Printer className="size-3.5" />
              Receipt
            </Button>
          </div>
        ) : null}
        <PosCart
          lines={lines}
          customer={customer}
          totals={totals}
          currency={currency}
          heldCount={held.length}
          onQuantity={changeQuantity}
          onLineDiscount={setLineDiscount}
          onRemove={removeWithSound}
          onCustomer={() => setCustomerOpen(true)}
          onDiscount={() => setDiscountOpen(true)}
          onHold={() => setHoldOpen(true)}
          onClear={clearWithSound}
          onCheckout={() => void openCheckout()}
          onHeld={() => setHeldOpen(true)}
        />
      </aside>
      </div>

      {customerOpen ? (
        <PosCustomerDialog
          current={customer}
          currency={currency}
          onSelect={(next) => {
            setCustomer(next);
            setCustomerOpen(false);
          }}
          onClose={() => setCustomerOpen(false)}
        />
      ) : null}

      {discountOpen ? (
        <PosDiscountDialog
          value={orderDiscount}
          subtotal={totals.subtotal}
          currency={currency}
          onApply={setOrderDiscount}
          onClose={() => setDiscountOpen(false)}
        />
      ) : null}

      {holdOpen ? <PosHoldDialog onHold={hold} onClose={() => setHoldOpen(false)} /> : null}

      {heldOpen ? (
        <PosHeldListDialog
          held={held}
          currency={currency}
          onResume={(id) => {
            resume(id);
            setHeldOpen(false);
          }}
          onDrop={dropHeld}
          onClose={() => setHeldOpen(false)}
        />
      ) : null}

      {checkoutOpen ? (
        <PosPaymentDialog
          lines={lines}
          totals={totals}
          orderDiscount={orderDiscount}
          customer={customer}
          branchId={effectiveBranch}
          registerId={effectiveRegister}
          currency={currency}
          onClose={() => setCheckoutOpen(false)}
          onComplete={handleSaleComplete}
        />
      ) : null}

      {invoiceSale ? (
        <InvoicePreviewDialog saleId={invoiceSale.id} onClose={() => setInvoiceSale(null)} />
      ) : null}

      {registerOpen && registers.length > 0 ? (
        <OpenRegisterDialog
          register={registers.find((register) => register.id === effectiveRegister) ?? registers[0]}
          currency={currency}
          onClose={() => setRegisterOpen(false)}
          onOpened={() => void sessionQuery.refetch()}
        />
      ) : null}

      {closeOpen && sessionDetail ? (
        <CloseRegisterDialog
          detail={sessionDetail}
          currency={currency}
          onClose={() => setCloseOpen(false)}
          onClosed={() => void sessionQuery.refetch()}
        />
      ) : null}

      {cashDirection && sessionDetail ? (
        <CashMovementDialog
          sessionId={sessionDetail.session.id}
          direction={cashDirection}
          onClose={() => setCashDirection(null)}
          onDone={() => void sessionQuery.refetch()}
        />
      ) : null}
    </div>
  );
}

function CategoryChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <Button
      type="button"
      variant={active ? "default" : "outline"}
      size="sm"
      onClick={onClick}
      className={cn("shrink-0", !active && "text-muted-foreground")}
    >
      {children}
    </Button>
  );
}
