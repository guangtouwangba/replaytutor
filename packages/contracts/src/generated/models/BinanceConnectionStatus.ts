// Generated from Pydantic. Do not edit.

export type Diagnostics = string[];
export type FuturesTradeEnabled = boolean;
export type IpRestricted = boolean;
export type Mainnet = boolean;
export type ReadEnabled = boolean;
export type Readable = boolean;
export type SchemaVersion = "1.0";
export type WithdrawalsEnabled = boolean;

export interface BinanceConnectionStatus {
  diagnostics?: Diagnostics;
  futures_trade_enabled: FuturesTradeEnabled;
  ip_restricted: IpRestricted;
  mainnet: Mainnet;
  read_enabled: ReadEnabled;
  readable: Readable;
  schema_version?: SchemaVersion;
  withdrawals_enabled: WithdrawalsEnabled;
}
