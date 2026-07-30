// Generated from Pydantic. Do not edit.

export type Dimension = "background" | "location" | "setup" | "trigger" | "execution" | "management" | "outcome";
export type Evidence = string[];
export type Title = string;
export type Verdict = "correct" | "improve" | "unknown";

export interface ReviewDimension {
  dimension: Dimension;
  evidence: Evidence;
  title: Title;
  verdict: Verdict;
}
