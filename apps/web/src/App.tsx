import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense, type ReactNode, useCallback, useEffect, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { fetchHealth } from "./api/health";
import { AppShell, type StartupState } from "./components/AppShell";
import "./styles.css";

const SUPPORTED_SCHEMA_VERSION = "1.0";
const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 10_000 } } });
const HomePage = lazy(() => import("./pages/HomePage").then((module) => ({ default: module.HomePage })));
const DataCenterPage = lazy(() => import("./pages/DataCenterPage").then((module) => ({ default: module.DataCenterPage })));
const TradeReviewPage = lazy(() => import("./pages/TradeReviewPage").then((module) => ({ default: module.TradeReviewPage })));
const WorkbenchPage = lazy(() => import("./pages/WorkbenchPage").then((module) => ({ default: module.WorkbenchPage })));
const AcademyPage = lazy(() => import("./pages/AcademyPage").then((module) => ({ default: module.AcademyPage })));
const StrategyDetailPage = lazy(() => import("./pages/AcademyPage").then((module) => ({ default: module.StrategyDetailPage })));
const SessionSetupPage = lazy(() => import("./pages/SessionSetupPage").then((module) => ({ default: module.SessionSetupPage })));
const SessionsPage = lazy(() => import("./pages/SessionsPage").then((module) => ({ default: module.SessionsPage })));
const SessionCompletePage = lazy(() => import("./pages/SessionReviewPage").then((module) => ({ default: module.SessionCompletePage })));
const SessionReviewPage = lazy(() => import("./pages/SessionReviewPage").then((module) => ({ default: module.SessionReviewPage })));
const PlaybooksPage = lazy(() => import("./pages/PlaybooksPage").then((module) => ({ default: module.PlaybooksPage })));
const SettingsPage = lazy(() => import("./pages/SettingsPage").then((module) => ({ default: module.SettingsPage })));
const TrainingReviewsPage = lazy(() => import("./pages/TrainingReviewsPage").then((module) => ({ default: module.TrainingReviewsPage })));

function RouteFallback() {
  const { t } = useTranslation();
  return <div className="route-loading" role="status">{t("app.loading")}</div>;
}

function RoutePage({ children }: { readonly children: ReactNode }) {
  return <Suspense fallback={<RouteFallback />}>{children}</Suspense>;
}

export function App() {
  const [startup, setStartup] = useState<StartupState>({ kind: "loading" });
  const [attempt, setAttempt] = useState(0);
  const retry = useCallback(() => { setStartup({ kind: "loading" }); setAttempt((value) => value + 1); }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetchHealth(controller.signal).then((health) => {
      if (health.schema_version !== SUPPORTED_SCHEMA_VERSION) {
        setStartup({ kind: "incompatible", receivedVersion: health.schema_version ?? "missing" });
        return;
      }
      setStartup({ kind: "available", health });
    }).catch((error: unknown) => {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setStartup({ kind: "unavailable", message: error instanceof Error ? error.message : "Unknown API error" });
    });
    return () => controller.abort();
  }, [attempt]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell startup={startup} onRetry={retry} />}>
            <Route index element={<RoutePage><HomePage /></RoutePage>} />
            <Route path="academy" element={<RoutePage><AcademyPage /></RoutePage>} />
            <Route path="academy/:strategyId" element={<RoutePage><StrategyDetailPage /></RoutePage>} />
            <Route path="setup" element={<RoutePage><SessionSetupPage /></RoutePage>} />
            <Route path="workbench" element={<RoutePage><WorkbenchPage /></RoutePage>} />
            <Route path="sessions" element={<RoutePage><SessionsPage /></RoutePage>} />
            <Route path="sessions/:sessionId" element={<RoutePage><WorkbenchPage /></RoutePage>} />
            <Route path="sessions/:sessionId/complete" element={<RoutePage><SessionCompletePage /></RoutePage>} />
            <Route path="sessions/:sessionId/review" element={<RoutePage><SessionReviewPage /></RoutePage>} />
            <Route path="reviews" element={<RoutePage><TrainingReviewsPage /></RoutePage>} />
            <Route path="reviews/binance" element={<RoutePage><TradeReviewPage /></RoutePage>} />
            <Route path="playbooks" element={<RoutePage><PlaybooksPage /></RoutePage>} />
            <Route path="data" element={<RoutePage><DataCenterPage /></RoutePage>} />
            <Route path="settings" element={<RoutePage><SettingsPage /></RoutePage>} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
