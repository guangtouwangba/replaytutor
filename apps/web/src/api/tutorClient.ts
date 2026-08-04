import type {
  CompanionSessionListResult,
  CompanionSessionStateResult,
  CompanionSessionSummary,
  ReplaySession,
} from "@replaytutor/contracts";
import type { TutorClient } from "@replaytutor/tutor-ui";
import { fetchEvidenceTarget, fetchSession, fetchSessions } from "./sessions";
import {
  cancelTutorRun,
  createTutorThread,
  discoverCodex,
  fetchTutorRun,
  fetchTutorThread,
  fetchTutorThreads,
  startTutor,
} from "./tutor";

function sessionSummary(session: ReplaySession): CompanionSessionSummary {
  return {
    schema_version: "1.0",
    session_id: session.session_id,
    snapshot_id: session.snapshot_id,
    instrument: session.instrument,
    status: session.status,
    frame_id: session.frame.frame_id,
    revision: session.revision,
    visible_at: session.frame.visible_at,
    updated_at: session.updated_at,
  };
}

async function listSessions(): Promise<CompanionSessionListResult> {
  const result = await fetchSessions();
  const sessions = [...result.sessions]
    .sort((left, right) => {
      const leftFinished = ["completed", "stopped"].includes(left.status);
      const rightFinished = ["completed", "stopped"].includes(right.status);
      if (leftFinished !== rightFinished) return leftFinished ? 1 : -1;
      return Date.parse(right.updated_at) - Date.parse(left.updated_at);
    })
    .slice(0, 50)
    .map(sessionSummary);
  return { schema_version: "1.0", sessions };
}

async function getSession(sessionId: string): Promise<CompanionSessionStateResult> {
  const result = await fetchSession(sessionId);
  return { schema_version: "1.0", session: sessionSummary(result.session) };
}

export const webTutorClient: TutorClient = {
  discoverCodex,
  listSessions,
  getSession,
  listThreads: fetchTutorThreads,
  createThread: createTutorThread,
  getThread: fetchTutorThread,
  startRun: startTutor,
  getRun: fetchTutorRun,
  cancelRun: cancelTutorRun,
  resolveEvidence: fetchEvidenceTarget,
};
