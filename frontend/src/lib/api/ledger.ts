/**
 * Account statements (ledgers) are derived server-side from the rows that moved
 * the balance, so the closing figure always equals the account's balance.
 * Money travels as strings, as everywhere else on the wire.
 */
export type LedgerEntryType = "opening" | "sale" | "purchase" | "payment" | "refund";

export type LedgerEntry = {
  occurred_at: string;
  entry_type: LedgerEntryType;
  /** A document number, a payment reference, or "Opening balance". */
  reference: string;
  description: string | null;
  /** Increases what is owed (a charge, or a payment for a payable). */
  debit: string;
  /** Decreases what is owed. */
  credit: string;
  /** The balance immediately after this entry. */
  balance: string;
};

export type LedgerStatement = {
  /** The balance carried into the requested window (0 when unbounded). */
  opening_balance: string;
  entries: LedgerEntry[];
  /** Equals the account balance when no date range narrows the statement. */
  closing_balance: string;
};

export type LedgerParams = {
  /** ISO `YYYY-MM-DD`. */
  date_from?: string;
  /** ISO `YYYY-MM-DD`. */
  date_to?: string;
};
