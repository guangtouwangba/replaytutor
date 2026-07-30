import { Construction, type LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";

interface UnavailablePageProps {
  readonly kicker: string;
  readonly title: string;
  readonly description: string;
  readonly milestone: string;
  readonly actionTo?: string;
  readonly actionLabel?: string;
  readonly icon?: LucideIcon;
}

export function UnavailablePage({
  kicker,
  title,
  description,
  milestone,
  actionTo = "/",
  actionLabel = "返回今日训练",
  icon: Icon = Construction,
}: UnavailablePageProps) {
  return (
    <section className="page centered-page unavailable-page" data-milestone={milestone}>
      <Icon size={36} />
      <div className="page-kicker">{kicker}</div>
      <h1>{title}</h1>
      <p>{description}</p>
      <span className="delivery-badge">{milestone} · 尚未交付</span>
      <Link className="secondary-action" to={actionTo}>{actionLabel}</Link>
    </section>
  );
}

export function AcademyPage() {
  return <UnavailablePage kicker="STRATEGY ACADEMY" title="策略学院" description="官方策略会在确定性训练闭环完成后开放；当前不会使用静态课程数据冒充可用功能。" milestone="W5" />;
}

export function StrategyDetailPage() {
  return <UnavailablePage kicker="OFFICIAL PLAYBOOK" title="策略详情" description="趋势回调、突破回踩和区间反转将绑定真实 Playbook 版本与训练规则。" milestone="W5" actionTo="/academy" actionLabel="返回策略学院" />;
}

export function SessionSetupPage() {
  return <UnavailablePage kicker="NEW SESSION" title="训练配置" description="Session/Replay 契约接入后，这里将创建受 visible_at 约束的 BTCUSDT 训练。" milestone="W1" actionTo="/data" actionLabel="检查行情数据" />;
}

export function SessionsPage() {
  return <UnavailablePage kicker="SESSION LIBRARY" title="会话库" description="会话恢复、结束和证据复盘将在 Session 事件流完成后开放。" milestone="W3" />;
}

export function SessionCompletePage() {
  return <UnavailablePage kicker="SESSION COMPLETE" title="会话完成" description="结束会话后才会揭示完整行情、MFE/MAE 与事后证据。" milestone="W3" />;
}

export function SessionReviewPage() {
  return <UnavailablePage kicker="EVIDENCE REVIEW" title="训练复盘" description="这里将展示确定性指标、计划偏差和可回跳的图表证据。" milestone="W3" />;
}

export function PlaybooksPage() {
  return <UnavailablePage kicker="PLAYBOOKS" title="个人 Playbook" description="策略版本化会在训练、撮合和确定性复盘稳定后实现。" milestone="W5" />;
}

export function SettingsPage() {
  return <UnavailablePage kicker="PREFERENCES & SAFETY" title="设置" description="这里只会展示已生效的偏好、目录、隐私和 Codex 状态，不提供无效开关。" milestone="W5" />;
}
