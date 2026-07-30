// Generated from Pydantic. Do not edit.

export type Count = number;
export type Direction = ("long" | "short") | null;
export type EpisodeId = string | null;
export type ScopeKind = "today" | "recent" | "trade";
export type Symbol = string | null;
export type SyncFirst = boolean;

export interface ReviewRequest {
  count?: Count;
  direction?: Direction;
  episode_id?: EpisodeId;
  scope_kind: ScopeKind;
  symbol?: Symbol;
  sync_first?: SyncFirst;
}
