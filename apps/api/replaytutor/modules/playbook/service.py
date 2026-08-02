from __future__ import annotations

import json
from datetime import UTC, datetime

from replaytutor.config import Settings
from replaytutor.contracts import (
    CreatePlaybookRequest,
    PlaybookListResponse,
    PlaybookRuleDefinition,
    PlaybookVersion,
)
from replaytutor.ids import new_id, stable_id
from replaytutor.modules.market_data.service import utc_text
from replaytutor.modules.training_session.service import parse_utc
from replaytutor.storage.database import connect_database

OFFICIAL = (
    (
        "trend-pullback",
        "趋势回调",
        "顺势等待回调结束, 以结构失效管理风险。",
        ["高周期方向明确", "回调未破坏趋势结构", "触发后下一根执行"],
    ),
    (
        "breakout-retest",
        "突破回踩",
        "等待关键位突破并回踩确认, 不追逐第一根扩张柱。",
        ["突破有收盘确认", "回踩守住关键位", "失效位在结构另一侧"],
    ),
    (
        "range-reversal",
        "区间反转",
        "只在清晰区间边缘寻找拒绝, 不在区间中部交易。",
        ["区间边界至少两次验证", "出现拒绝信号", "目标不越过对侧边界"],
    ),
)
EVALUATOR_VERSION = "1.0"

CORE_RULE_DEFINITIONS = [
    PlaybookRuleDefinition(
        rule_id="plan_locked_before_first_order",
        label="首笔订单前锁定计划",
        evaluator_kind="plan_locked_before_first_order",
    ),
    PlaybookRuleDefinition(
        rule_id="order_activated_on_next_bar",
        label="订单只在下一根 K 线激活",
        evaluator_kind="order_activated_on_next_bar",
    ),
    PlaybookRuleDefinition(
        rule_id="risk_amount_within_limit",
        label="计划风险金额不超过 100 USDT",
        evaluator_kind="risk_amount_within_limit",
        params={"max_risk_amount": "100"},
    ),
    PlaybookRuleDefinition(
        rule_id="protective_stop_present",
        label="入场订单配有保护止损",
        evaluator_kind="protective_stop_present",
    ),
    PlaybookRuleDefinition(
        rule_id="no_order_after_session_complete",
        label="会话完成后没有新增订单",
        evaluator_kind="no_order_after_session_complete",
    ),
    PlaybookRuleDefinition(
        rule_id="entry_side_matches_locked_plan",
        label="入场方向与锁定计划一致",
        evaluator_kind="entry_side_matches_locked_plan",
    ),
]


def free_text_definitions(rules: list[str]) -> list[PlaybookRuleDefinition]:
    return [
        PlaybookRuleDefinition(
            rule_id=f"custom_rule_{index:02d}",
            label=rule,
            evaluator_kind="free_text",
        )
        for index, rule in enumerate(rules, start=1)
    ]


class PlaybookService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def list(self) -> PlaybookListResponse:
        self._seed()
        with connect_database(self.settings.database_path) as connection:
            rows = connection.execute(
                """SELECT * FROM playbook_version
                ORDER BY official DESC, slug, version DESC"""
            ).fetchall()
        return PlaybookListResponse(playbooks=[self._from_row(row) for row in rows])

    def create(self, request: CreatePlaybookRequest) -> PlaybookVersion:
        self._seed()
        now = datetime.now(UTC)
        with connect_database(self.settings.database_path) as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM playbook_version WHERE slug = ?",
                (request.slug,),
            ).fetchone()
            version = int(row[0])
            item = PlaybookVersion(
                playbook_id=new_id("pbk"),
                slug=request.slug,
                name=request.name,
                version=version,
                description=request.description,
                rules=request.rules,
                rule_definitions=free_text_definitions(request.rules),
                evaluator_version=EVALUATOR_VERSION,
                official=False,
                created_at=now,
            )
            self._insert(connection, item)
        return item

    def exists(self, playbook_id: str) -> bool:
        self._seed()
        with connect_database(self.settings.database_path) as connection:
            return (
                connection.execute(
                    "SELECT 1 FROM playbook_version WHERE playbook_id = ?",
                    (playbook_id,),
                ).fetchone()
                is not None
            )

    def _seed(self) -> None:
        now = datetime.now(UTC)
        with connect_database(self.settings.database_path) as connection:
            for slug, name, description, rules in OFFICIAL:
                legacy = PlaybookVersion(
                    playbook_id=stable_id(
                        "pbk",
                        "replaytutor:official-playbook",
                        f"{slug}:1",
                    ),
                    slug=slug,
                    name=name,
                    version=1,
                    description=description,
                    rules=list(rules),
                    rule_definitions=free_text_definitions(list(rules)),
                    evaluator_version="legacy",
                    official=True,
                    created_at=now,
                )
                item = PlaybookVersion(
                    playbook_id=stable_id(
                        "pbk",
                        "replaytutor:official-playbook",
                        f"{slug}:2",
                    ),
                    slug=slug,
                    name=name,
                    version=2,
                    description=description,
                    rules=list(rules),
                    rule_definitions=CORE_RULE_DEFINITIONS,
                    evaluator_version=EVALUATOR_VERSION,
                    official=True,
                    created_at=now,
                )
                for candidate in (legacy, item):
                    connection.execute(
                        """INSERT OR IGNORE INTO playbook_version (
                            playbook_id, slug, name, version, description,
                            rules_json, official, created_at,
                            rule_definitions_json, evaluator_version
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            candidate.playbook_id,
                            candidate.slug,
                            candidate.name,
                            candidate.version,
                            candidate.description,
                            json.dumps(candidate.rules, ensure_ascii=False),
                            candidate.official,
                            utc_text(now),
                            json.dumps(
                                [
                                    definition.model_dump(mode="json")
                                    for definition in candidate.rule_definitions
                                ],
                                ensure_ascii=False,
                            ),
                            candidate.evaluator_version,
                        ),
                    )

    @staticmethod
    def _insert(connection, item: PlaybookVersion) -> None:
        connection.execute(
            """INSERT INTO playbook_version (
                playbook_id, slug, name, version, description,
                rules_json, official, created_at,
                rule_definitions_json, evaluator_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item.playbook_id,
                item.slug,
                item.name,
                item.version,
                item.description,
                json.dumps(item.rules, ensure_ascii=False),
                item.official,
                utc_text(item.created_at),
                json.dumps(
                    [definition.model_dump(mode="json") for definition in item.rule_definitions],
                    ensure_ascii=False,
                ),
                item.evaluator_version,
            ),
        )

    @staticmethod
    def _from_row(row) -> PlaybookVersion:
        rules = json.loads(row["rules_json"])
        definitions = (
            [
                PlaybookRuleDefinition.model_validate(item)
                for item in json.loads(row["rule_definitions_json"])
            ]
            if row["rule_definitions_json"]
            else free_text_definitions(rules)
        )
        return PlaybookVersion(
            playbook_id=str(row["playbook_id"]),
            slug=str(row["slug"]),
            name=str(row["name"]),
            version=int(row["version"]),
            description=str(row["description"]),
            rules=rules,
            rule_definitions=definitions,
            evaluator_version=str(row["evaluator_version"] or "legacy"),
            official=bool(row["official"]),
            created_at=parse_utc(str(row["created_at"])),
        )
