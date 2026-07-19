import { useCallback, useEffect, useState } from "react";
import { fetchHealth } from "./api/health";
import { AppShell, type StartupState } from "./components/AppShell";
import "./styles.css";

const SUPPORTED_SCHEMA_VERSION = "1.0";

export function App() {
  const [startup, setStartup] = useState<StartupState>({ kind: "loading" });
  const [attempt, setAttempt] = useState(0);

  const retry = useCallback(() => {
    setStartup({ kind: "loading" });
    setAttempt((value) => value + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetchHealth(controller.signal)
      .then((health) => {
        if (health.schema_version !== SUPPORTED_SCHEMA_VERSION) {
          setStartup({ kind: "incompatible", receivedVersion: health.schema_version });
          return;
        }
        setStartup({ kind: "available", health });
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        const message = error instanceof Error ? error.message : "Unknown API error";
        setStartup({ kind: "unavailable", message });
      });
    return () => controller.abort();
  }, [attempt]);

  return <AppShell startup={startup} onRetry={retry} />;
}
