// Generated from Pydantic. Do not edit.

export type AverageEntryPrice = string;
export type InitialMargin = string;
export type Leverage = number;
export type LiquidationPrice = string | null;
export type MaintenanceMargin = string;
export type MarkPrice = string;
export type Notional = string;
export type PositionSide = "BOTH" | "LONG" | "SHORT";
export type Quantity = string;
export type UnrealizedPnl = string;

export interface PositionState {
  average_entry_price: AverageEntryPrice;
  initial_margin: InitialMargin;
  leverage: Leverage;
  liquidation_price?: LiquidationPrice;
  maintenance_margin: MaintenanceMargin;
  mark_price: MarkPrice;
  notional: Notional;
  position_side: PositionSide;
  quantity: Quantity;
  unrealized_pnl: UnrealizedPnl;
}
