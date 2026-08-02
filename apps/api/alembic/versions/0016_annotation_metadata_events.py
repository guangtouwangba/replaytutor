"""Store effective metadata in append-only annotation revision events."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016_annotation_metadata_events"
down_revision: str | Sequence[str] | None = "0015_dataset_download_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {
        column["name"]
        for column in inspector.get_columns("session_annotation_event")
    }
    if "replacement_metadata_json" not in columns:
        op.add_column(
            "session_annotation_event",
            sa.Column("replacement_metadata_json", sa.Text()),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {
        column["name"]
        for column in inspector.get_columns("session_annotation_event")
    }
    if "replacement_metadata_json" in columns:
        op.drop_column("session_annotation_event", "replacement_metadata_json")
