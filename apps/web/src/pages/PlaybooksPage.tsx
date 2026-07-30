import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { createPlaybook, fetchPlaybooks } from "../api/playbooks";

export function PlaybooksPage() {
  const queryClient = useQueryClient();
  const playbooks = useQuery({ queryKey: ["playbooks"], queryFn: fetchPlaybooks });
  const [name, setName] = useState("我的趋势回调");
  const [rules, setRules] = useState("高周期方向明确\n回调不破坏结构\n定义失效后再下单");
  const create = useMutation({
    mutationFn: () => createPlaybook({
      slug: name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "my-playbook",
      name,
      description: "个人训练规则",
      rules: (() => {
        const parsed = rules.split("\n").map((rule) => rule.trim()).filter(Boolean);
        return parsed.length ? [parsed[0]!, ...parsed.slice(1)] : ["定义一条可验证规则"];
      })(),
    }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["playbooks"] }),
  });
  return <section className="page playbooks-page"><div className="page-kicker">VERSIONED PLAYBOOKS</div><h1>策略版本</h1><p>修改不会覆盖历史版本；训练会话固定引用创建时的版本 ID。</p><div className="playbook-layout"><div>{playbooks.data?.playbooks.map((item) => <article className="playbook-row" key={item.playbook_id}><span>{item.official ? "官方" : "个人"} · v{item.version}</span><h2>{item.name}</h2><p>{item.description}</p><code>{item.playbook_id.slice(0, 16)}</code></article>)}</div><form className="playbook-editor" onSubmit={(event) => { event.preventDefault(); create.mutate(); }}><h2>创建新版本</h2><label>名称<input onChange={(event) => setName(event.target.value)} value={name} /></label><label>规则（每行一条）<textarea onChange={(event) => setRules(event.target.value)} value={rules} /></label><button className="primary-action" disabled={create.isPending} type="submit">保存不可变版本</button>{create.isError && <div className="inline-error">{create.error.message}</div>}</form></div></section>;
}
