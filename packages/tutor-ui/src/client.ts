import type {
  AgentCapability,
  CompanionSessionListResult,
  CompanionSessionStateResult,
  CreateTutorThreadRequest,
  EvidenceTarget,
  TutorRequest,
  TutorRun,
  TutorThreadDetail,
  TutorThreadListResponse,
} from "@replaytutor/contracts";

export interface TutorClient {
  discoverCodex(): Promise<AgentCapability>;
  listSessions(): Promise<CompanionSessionListResult>;
  getSession(sessionId: string): Promise<CompanionSessionStateResult>;
  listThreads(sessionId: string): Promise<TutorThreadListResponse>;
  createThread(
    sessionId: string,
    request?: CreateTutorThreadRequest,
  ): Promise<TutorThreadDetail>;
  getThread(threadId: string): Promise<TutorThreadDetail>;
  startRun(sessionId: string, request: TutorRequest): Promise<TutorRun>;
  getRun(runId: string): Promise<TutorRun>;
  cancelRun(runId: string): Promise<TutorRun>;
  resolveEvidence(sessionId: string, evidenceId: string): Promise<EvidenceTarget>;
}
