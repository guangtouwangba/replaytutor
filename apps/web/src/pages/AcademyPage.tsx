import { useQuery } from "@tanstack/react-query";
import { ArrowRight, BookOpenCheck } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { fetchPlaybooks } from "../api/playbooks";

export function AcademyPage() {
  const playbooks = useQuery({ queryKey: ["playbooks"], queryFn: fetchPlaybooks });
  const latestOfficialPlaybooks = playbooks.data?.playbooks.filter(
    (item, _, all) => item.official && !all.some(
      (candidate) => candidate.slug === item.slug && candidate.version > item.version,
    ),
  ) ?? [];
  return <section className="page academy-page"><div className="page-kicker">STRATEGY ACADEMY</div><h1>用规则训练，不用结果倒推</h1><p>三个官方策略都是不可变版本；每次训练会绑定当时版本。</p><div className="academy-grid">{latestOfficialPlaybooks.map((item) => <Link className="academy-card" key={item.playbook_id} to={`/academy/${item.slug}`}><BookOpenCheck size={22} /><span>OFFICIAL · V{item.version}</span><h2>{item.name}</h2><p>{item.description}</p><strong>查看规则 <ArrowRight size={13} /></strong></Link>)}</div></section>;
}

export function StrategyDetailPage() {
  const { strategyId } = useParams();
  const playbooks = useQuery({ queryKey: ["playbooks"], queryFn: fetchPlaybooks });
  const item = playbooks.data?.playbooks.find((entry) => entry.slug === strategyId);
  if (playbooks.isLoading) return <div className="route-loading">正在读取策略版本…</div>;
  if (!item) return <section className="page centered-page"><h1>策略不存在</h1><Link to="/academy">返回学院</Link></section>;
  return <section className="page strategy-page"><div className="page-kicker">PLAYBOOK · V{item.version}</div><h1>{item.name}</h1><p>{item.description}</p><ol>{item.rules.map((rule) => <li key={rule}>{rule}</li>)}</ol><div className="inline-notice">策略提供检查框架，不替代风险控制，也不会读取未来行情。</div><Link className="primary-action" to={`/setup?strategy=${item.slug}`}>用此策略训练 <ArrowRight size={14} /></Link></section>;
}
