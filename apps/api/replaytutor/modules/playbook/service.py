from __future__ import annotations

import json
from datetime import UTC, datetime

from replaytutor.config import Settings
from replaytutor.contracts import (
    CreatePlaybookRequest,
    PlaybookListResponse,
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
                item = PlaybookVersion(
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
                    official=True,
                    created_at=now,
                )
                connection.execute(
                    """INSERT OR IGNORE INTO playbook_version (
                        playbook_id, slug, name, version, description,
                        rules_json, official, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item.playbook_id,
                        item.slug,
                        item.name,
                        item.version,
                        item.description,
                        json.dumps(item.rules, ensure_ascii=False),
                        item.official,
                        utc_text(now),
                    ),
                )

    @staticmethod
    def _insert(connection, item: PlaybookVersion) -> None:
        connection.execute(
            """INSERT INTO playbook_version (
                playbook_id, slug, name, version, description,
                rules_json, official, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item.playbook_id,
                item.slug,
                item.name,
                item.version,
                item.description,
                json.dumps(item.rules, ensure_ascii=False),
                item.official,
                utc_text(item.created_at),
            ),
        )

    @staticmethod
    def _from_row(row) -> PlaybookVersion:
        return PlaybookVersion(
            playbook_id=str(row["playbook_id"]),
            slug=str(row["slug"]),
            name=str(row["name"]),
            version=int(row["version"]),
            description=str(row["description"]),
            rules=json.loads(row["rules_json"]),
            official=bool(row["official"]),
            created_at=parse_utc(str(row["created_at"])),
        )
