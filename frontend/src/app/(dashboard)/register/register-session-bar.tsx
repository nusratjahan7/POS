"use client";

import { ArrowDownCircle, ArrowUpCircle, Lock, Unlock } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { RegisterSessionDetail } from "@/lib/api/register-sessions";
import type { Register } from "@/lib/api/settings";
import { formatDateTime, formatMoney } from "@/lib/format";

type RegisterSessionBarProps = {
  registers: Register[];
  registerId: string;
  onRegisterChange: (registerId: string) => void;
  detail: RegisterSessionDetail | null;
  isLoading: boolean;
  canOperate: boolean;
  currency: string;
  onOpen: () => void;
  onCashIn: () => void;
  onCashOut: () => void;
  onCloseRegister: () => void;
};

/**
 * The till's status strip — always visible at the top of the register so a
 * cashier can see, at a glance, whether the drawer is open and what it should
 * hold, and act on it (open, cash in/out, close).
 */
export function RegisterSessionBar({
  registers,
  registerId,
  onRegisterChange,
  detail,
  isLoading,
  canOperate,
  currency,
  onOpen,
  onCashIn,
  onCashOut,
  onCloseRegister,
}: RegisterSessionBarProps) {
  const session = detail?.session ?? null;
  const expected = detail?.summary.expected_cash ?? session?.expected_cash ?? "0";

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b bg-muted/40 px-4 py-2">
      <Select
        value={registerId}
        onValueChange={onRegisterChange}
        disabled={registers.length === 0}
      >
        <SelectTrigger className="h-9 w-48" aria-label="Register">
          <SelectValue placeholder="Register" />
        </SelectTrigger>
        <SelectContent>
          {registers.map((register) => (
            <SelectItem key={register.id} value={register.id}>
              {register.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {registers.length === 0 ? (
        <span className="text-muted-foreground text-sm">
          No register is set up for this branch — add one in Settings.
        </span>
      ) : isLoading ? (
        <span className="text-muted-foreground text-sm">Checking the register…</span>
      ) : session ? (
        <>
          <Badge variant="success" className="gap-1">
            <Unlock className="size-3" aria-hidden />
            Open
          </Badge>
          <span className="text-muted-foreground text-sm">
            since {formatDateTime(session.opened_at)}
            {session.opened_by ? ` · ${session.opened_by.full_name}` : ""}
          </span>
          <span className="text-sm">
            Expected cash{" "}
            <strong className="tabular-nums">{formatMoney(expected, currency)}</strong>
          </span>
          <div className="ms-auto flex flex-wrap items-center gap-2">
            <Button size="sm" variant="outline" onClick={onCashIn} disabled={!canOperate}>
              <ArrowDownCircle className="size-4" />
              Cash in
            </Button>
            <Button size="sm" variant="outline" onClick={onCashOut} disabled={!canOperate}>
              <ArrowUpCircle className="size-4" />
              Cash out
            </Button>
            <Button size="sm" onClick={onCloseRegister} disabled={!canOperate}>
              <Lock className="size-4" />
              Close register
            </Button>
          </div>
        </>
      ) : (
        <>
          <Badge variant="warning">Closed</Badge>
          <span className="text-sm font-medium">Open the register to start selling.</span>
          <div className="ms-auto">
            <Button size="sm" onClick={onOpen} disabled={!canOperate}>
              <Unlock className="size-4" />
              Open register
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
