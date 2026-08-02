// Generated from Pydantic. Do not edit.

export type Continuous = boolean;
export type DefaultTemplateId = string | null;
export type Favorite = boolean;
export type RecentRank = number | null;

export interface UpdateChartToolPreferenceRequest {
  continuous?: Continuous;
  default_template_id?: DefaultTemplateId;
  favorite?: Favorite;
  recent_rank?: RecentRank;
}
