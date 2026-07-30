// Generated from Pydantic. Do not edit.

export type AverageEntryPrice = string;
export type Cash = string;
export type FeesPaid = string;
export type PositionQuantity = string;
export type RealizedPnl = string;
export type SchemaVersion = "1.0";

export interface PortfolioState {
  average_entry_price: AverageEntryPrice;
  cash: Cash;
  fees_paid: FeesPaid;
  position_quantity: PositionQuantity;
  realized_pnl: RealizedPnl;
  schema_version?: SchemaVersion;
}
