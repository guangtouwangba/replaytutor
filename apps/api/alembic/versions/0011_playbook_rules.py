"""Add versioned deterministic Playbook rule definitions."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011_playbook_rules"
down_revision: str | Sequence[str] | None = "0010_annotation_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("playbook_version")
    }
    with op.batch_alter_table("playbook_version") as batch:
        if "rule_definitions_json" not in columns:
            batch.add_column(sa.Column("rule_definitions_json", sa.Text()))
        if "evaluator_version" not in columns:
            batch.add_column(sa.Column("evaluator_version", sa.String(32)))


def downgrade() -> None:
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("playbook_version")
    }
    with op.batch_alter_table("playbook_version") as batch:
        if "evaluator_version" in columns:
            batch.drop_column("evaluator_version")
        if "rule_definitions_json" in columns:
            batch.drop_column("rule_definitions_json")
