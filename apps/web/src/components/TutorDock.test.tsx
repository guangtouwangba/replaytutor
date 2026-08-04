import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n";
import { TutorDock } from "./TutorDock";

const sessionId = "ses_00000000-0000-4000-8000-000000000001";
const threadId = "thr_00000000-0000-4000-8000-000000000002";
const runId = "run_00000000-0000-4000-8000-000000000003";
const createdAt = "2026-08-03T00:00:00Z";
let lastTutorRequest: Record<string, unknown> | null = null;
const completedRun = {
  schema_version: "1.0",
  run_id: runId,
  thread_id: threadId,
  sequence: 1,
  session_id: sessionId,
  frame_id: "frm_00000000-0000-4000-8000-000000000004",
  agent_id: "codex-local",
  status: "completed",
  question: "这次入场符合计划吗？",
  stage: "plan",
  context_bundle_id: null,
  response: {
    schema_version: "1.0",
    summary: "入场依据存在，但失效条件仍需收紧。",
    observations: [],
    inferences: [],
    risks_and_unknowns: ["未来行情不可见。"],
    rule_checks: [],
    next_questions: ["你的失效价格是什么？"],
    annotations: [{
      annotation_id: "ann_00000000-0000-4000-8000-000000000005",
      tool: "horizontal_line",
      purpose: "support",
      timeframe: "4h",
      shape: "line",
      label: "4h 关键支撑",
      evidence_ids: ["bar_00000000-0000-4000-8000-000000000006"],
      points: [{ time: createdAt, price: "100" }],
    }],
    disclaimer: "仅用于回放训练。",
  },
  error: null,
  created_at: createdAt,
  completed_at: createdAt,
};
const thread = {
  schema_version: "1.0",
  thread_id: threadId,
  session_id: sessionId,
  title: "入场计划",
  run_count: 1,
  last_question: completedRun.question,
  last_status: "completed",
  created_at: createdAt,
  updated_at: createdAt,
};

function response(payload: unknown) {
  return Promise.resolve(new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  }));
}

beforeEach(async () => {
  await i18n.changeLanguage("zh-CN");
  window.localStorage.clear();
  lastTutorRequest = null;
  Object.defineProperty(HTMLElement.prototype, "scrollTo", { value: vi.fn(), configurable: true });
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/agents/codex")) return response({
      schema_version: "1.0",
      agent_id: "codex-local",
      authentication: "verified",
      available: true,
      diagnostics: [],
      executable: "/usr/bin/codex",
      installed: true,
      version: "1.0.0",
    });
    if (url.endsWith(`/sessions/${sessionId}/tutor/threads`)) {
      return response({ schema_version: "1.0", threads: [thread] });
    }
    if (url.endsWith(`/tutor/threads/${threadId}`)) {
      return response({ ...thread, runs: [completedRun] });
    }
    if (url.endsWith(`/sessions/${sessionId}/tutor`)) {
      lastTutorRequest = JSON.parse(String(init?.body)) as Record<string, unknown>;
      return response({ ...completedRun, sequence: 2, status: "running", response: null });
    }
    throw new Error(`Unexpected URL ${url}`);
  }));
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("TutorDock focused chat", () => {
  it("restores the current conversation without rendering a history sidebar", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={queryClient}><TutorDock sessionId={sessionId} /></QueryClientProvider>);

    await waitFor(() => expect(screen.getByText("入场依据存在，但失效条件仍需收紧。")).toBeInTheDocument());
    expect(screen.getByText("入场计划")).toBeInTheDocument();
    expect(screen.getByText("这次入场符合计划吗？")).toBeInTheDocument();
    expect(screen.getByText("未来行情不可见。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /4h 关键支撑/ })).toBeInTheDocument();
    expect(document.querySelector(".chat-thread-sidebar")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "新建对话" })).toBeInTheDocument();
    expect(window.localStorage.getItem(`replaytutor:tutor-thread:${sessionId}`)).toBe(threadId);

    fireEvent.click(screen.getByRole("button", { name: /图表上下文/ }));
    expect(screen.getByText("本轮明确证据")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "发送给 Codex Tutor" })).toBeInTheDocument();
  });

  it("sends the active chart timeframe with a natural-language drawing request", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={queryClient}><TutorDock analysisTimeframe="4h" sessionId={sessionId} /></QueryClientProvider>);

    const composer = await screen.findByRole("textbox", { name: "发送给 Codex Tutor" });
    fireEvent.change(composer, { target: { value: "帮我画出主要趋势线和支撑压力" } });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));
    await waitFor(() => expect(lastTutorRequest).not.toBeNull());
    expect(lastTutorRequest?.analysis_timeframe).toBe("4h");
  });
});
