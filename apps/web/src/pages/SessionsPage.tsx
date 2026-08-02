import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, History, RotateCcw, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import {
  deleteSession,
  fetchSessions,
  fetchSessionTrash,
  restoreSession,
} from "../api/sessions";

export function SessionsPage() {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["sessions"], queryFn: fetchSessions });
  const trash = useQuery({ queryKey: ["session-trash"], queryFn: fetchSessionTrash });
  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["sessions"] }),
      queryClient.invalidateQueries({ queryKey: ["session-trash"] }),
      queryClient.invalidateQueries({ queryKey: ["training-reviews"] }),
    ]);
  };
  const remove = useMutation({
    mutationFn: deleteSession,
    onSuccess: refresh,
  });
  const restore = useMutation({
    mutationFn: restoreSession,
    onSuccess: refresh,
  });
  return (
    <section className="page sessions-page">
      <div className="page-kicker">SESSION LIBRARY</div>
      <h1>训练会话</h1>
      <p>未完成会话继续训练；已完成会话只读进入确定性证据复盘。</p>
      {query.isLoading && <div className="table-loading">正在恢复会话索引…</div>}
      {query.isError && <div className="inline-error">{query.error.message}</div>}
      <div className="session-cards">
        {query.data?.sessions.map((session) => (
          <article className="session-card-shell" key={session.session_id}>
            <Link
              className="session-card"
              to={session.status === "completed" ? `/sessions/${session.session_id}/review` : `/sessions/${session.session_id}`}
            >
              <History size={18} />
              <span><strong>{session.instrument.canonical_symbol}</strong><small>{session.status} · revision {session.revision}</small></span>
              <code>{session.hidden_real_date && session.status !== "completed" ? `Frame ${session.frame.current_index}` : new Date(session.frame.visible_at).toLocaleString("zh-CN", { hour12: false })}</code>
              <ArrowRight size={15} />
            </Link>
            <button aria-label={`移入回收站 ${session.session_id}`} disabled={remove.isPending} onClick={() => remove.mutate(session.session_id)} title="移入回收站" type="button"><Trash2 size={14} /></button>
          </article>
        ))}
      </div>
      {query.data?.sessions.length === 0 && <div className="large-empty"><h2>还没有训练会话</h2><Link className="primary-action" to="/setup">创建第一场训练</Link></div>}
      {(trash.data?.sessions.length ?? 0) > 0 && (
        <section className="session-trash">
          <div className="section-title"><h2>回收站</h2><span>可恢复，不会删除证据</span></div>
          {trash.data?.sessions.map((session) => (
            <div key={session.session_id}>
              <span>{session.instrument.canonical_symbol} · {session.session_id.slice(0, 16)}</span>
              <time>{session.deleted_at ? new Date(session.deleted_at).toLocaleString("zh-CN") : "—"}</time>
              <button disabled={restore.isPending} onClick={() => restore.mutate(session.session_id)} type="button"><RotateCcw size={13} />恢复</button>
            </div>
          ))}
        </section>
      )}
    </section>
  );
}
