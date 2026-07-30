import { useQuery } from "@tanstack/react-query";
import { ArrowRight, History } from "lucide-react";
import { Link } from "react-router-dom";
import { fetchSessions } from "../api/sessions";

export function SessionsPage() {
  const query = useQuery({ queryKey: ["sessions"], queryFn: fetchSessions });
  return (
    <section className="page sessions-page">
      <div className="page-kicker">SESSION LIBRARY</div>
      <h1>训练会话</h1>
      <p>未完成会话继续训练；已完成会话只读进入确定性证据复盘。</p>
      {query.isLoading && <div className="table-loading">正在恢复会话索引…</div>}
      {query.isError && <div className="inline-error">{query.error.message}</div>}
      <div className="session-cards">
        {query.data?.sessions.map((session) => (
          <Link
            className="session-card"
            key={session.session_id}
            to={session.status === "completed" ? `/sessions/${session.session_id}/review` : `/sessions/${session.session_id}`}
          >
            <History size={18} />
            <span><strong>{session.instrument.canonical_symbol}</strong><small>{session.status} · revision {session.revision}</small></span>
            <code>{session.hidden_real_date && session.status !== "completed" ? `Frame ${session.frame.current_index}` : new Date(session.frame.visible_at).toLocaleString("zh-CN", { hour12: false })}</code>
            <ArrowRight size={15} />
          </Link>
        ))}
      </div>
      {query.data?.sessions.length === 0 && <div className="large-empty"><h2>还没有训练会话</h2><Link className="primary-action" to="/setup">创建第一场训练</Link></div>}
    </section>
  );
}
