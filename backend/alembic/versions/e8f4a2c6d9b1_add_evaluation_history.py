"""add evaluation history

Revision ID: e8f4a2c6d9b1
Revises: d1e2f3a4b5c6
Create Date: 2026-07-27 22:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8f4a2c6d9b1"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evaluation_runs",
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("baseline_run_id", sa.UUID(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column(
            "suite_name",
            sa.String(length=120),
            server_default="productai-agent-evals",
            nullable=False,
        ),
        sa.Column("suite_version", sa.String(length=80), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="queued",
            nullable=False,
        ),
        sa.Column(
            "trigger_source",
            sa.String(length=32),
            server_default="cli",
            nullable=False,
        ),
        sa.Column("triggered_by", sa.String(length=160), nullable=True),
        sa.Column("environment", sa.String(length=64), nullable=True),
        sa.Column("git_commit_sha", sa.String(length=64), nullable=True),
        sa.Column("git_branch", sa.String(length=255), nullable=True),
        sa.Column("deployment_id", sa.String(length=255), nullable=True),
        sa.Column("ci_provider", sa.String(length=64), nullable=True),
        sa.Column("ci_run_id", sa.String(length=255), nullable=True),
        sa.Column("model_provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("prompt_version", sa.String(length=80), nullable=True),
        sa.Column("agent_version", sa.String(length=80), nullable=True),
        sa.Column("analysis_depth", sa.String(length=32), nullable=True),
        sa.Column("answer_detail", sa.String(length=32), nullable=True),
        sa.Column("configuration", sa.JSON(), nullable=True),
        sa.Column("selection_filters", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "selected_case_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "attempted_case_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "completed_case_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "passed_case_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "failed_case_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "error_case_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("pass_rate_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("average_score_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("estimated_cost_usd", sa.Numeric(14, 8), nullable=True),
        sa.Column("actual_cost_usd", sa.Numeric(14, 8), nullable=True),
        sa.Column("average_latency_ms", sa.Integer(), nullable=True),
        sa.Column("minimum_latency_ms", sa.Integer(), nullable=True),
        sa.Column("maximum_latency_ms", sa.Integer(), nullable=True),
        sa.Column("p95_latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "total_input_tokens",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "total_output_tokens",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "total_tokens",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("manifest_uri", sa.Text(), nullable=True),
        sa.Column("report_uri", sa.Text(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column(
            "cancellation_requested",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "selected_case_count >= 0 AND attempted_case_count >= 0 "
            "AND completed_case_count >= 0 AND passed_case_count >= 0 "
            "AND failed_case_count >= 0 AND error_case_count >= 0",
            name="ck_evaluation_runs_counts_nonnegative",
        ),
        sa.CheckConstraint(
            "pass_rate_percent IS NULL OR "
            "(pass_rate_percent >= 0 AND pass_rate_percent <= 100)",
            name="ck_evaluation_runs_pass_rate_range",
        ),
        sa.CheckConstraint(
            "average_score_percent IS NULL OR "
            "(average_score_percent >= 0 AND average_score_percent <= 100)",
            name="ck_evaluation_runs_average_score_range",
        ),
        sa.CheckConstraint(
            "estimated_cost_usd IS NULL OR estimated_cost_usd >= 0",
            name="ck_evaluation_runs_estimated_cost_nonnegative",
        ),
        sa.CheckConstraint(
            "actual_cost_usd IS NULL OR actual_cost_usd >= 0",
            name="ck_evaluation_runs_actual_cost_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["baseline_run_id"],
            ["evaluation_runs.run_id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("run_id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        "ix_evaluation_runs_status_created_at",
        "evaluation_runs",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_evaluation_runs_suite_created_at",
        "evaluation_runs",
        ["suite_name", "created_at"],
    )
    op.create_index(
        "ix_evaluation_runs_model_created_at",
        "evaluation_runs",
        ["model", "created_at"],
    )

    op.create_table(
        "evaluation_case_results",
        sa.Column("case_result_id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.String(length=160), nullable=False),
        sa.Column("case_version", sa.String(length=80), nullable=True),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=True),
        sa.Column(
            "attempt_number",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="queued",
            nullable=False,
        ),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("score_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("final_answer", sa.Text(), nullable=True),
        sa.Column("reference_source", sa.Text(), nullable=True),
        sa.Column("expected_tools", sa.JSON(), nullable=True),
        sa.Column("forbidden_tools", sa.JSON(), nullable=True),
        sa.Column("expected_answer_contains", sa.JSON(), nullable=True),
        sa.Column("expected_answer_terms", sa.JSON(), nullable=True),
        sa.Column("tools_used", sa.JSON(), nullable=True),
        sa.Column(
            "tool_call_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("checks", sa.JSON(), nullable=True),
        sa.Column("failed_checks", sa.JSON(), nullable=True),
        sa.Column("trace_id", sa.String(length=160), nullable=True),
        sa.Column("guardrail_status", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "input_tokens",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "output_tokens",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "total_tokens",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("cost_usd", sa.Numeric(14, 8), nullable=True),
        sa.Column("error_stage", sa.String(length=64), nullable=True),
        sa.Column("error_type", sa.String(length=160), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("raw_result_uri", sa.Text(), nullable=True),
        sa.Column("score_result_uri", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "attempt_number > 0",
            name="ck_evaluation_case_results_attempt_positive",
        ),
        sa.CheckConstraint(
            "score_percent IS NULL OR "
            "(score_percent >= 0 AND score_percent <= 100)",
            name="ck_evaluation_case_results_score_range",
        ),
        sa.CheckConstraint(
            "cost_usd IS NULL OR cost_usd >= 0",
            name="ck_evaluation_case_results_cost_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["evaluation_runs.run_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("case_result_id"),
        sa.UniqueConstraint(
            "run_id",
            "case_id",
            "attempt_number",
            name="uq_evaluation_case_results_run_case_attempt",
        ),
    )
    op.create_index(
        "ix_evaluation_case_results_run_status",
        "evaluation_case_results",
        ["run_id", "status"],
    )
    op.create_index(
        "ix_evaluation_case_results_category_passed",
        "evaluation_case_results",
        ["category", "passed"],
    )
    op.create_index(
        "ix_evaluation_case_results_case_id",
        "evaluation_case_results",
        ["case_id"],
    )
    op.create_index(
        "ix_evaluation_case_results_trace_id",
        "evaluation_case_results",
        ["trace_id"],
    )

    op.create_table(
        "evaluation_artifacts",
        sa.Column("artifact_id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("case_result_id", sa.UUID(), nullable=True),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "storage_provider",
            sa.String(length=32),
            server_default="local",
            nullable=False,
        ),
        sa.Column("uri", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=160), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column(
            "is_sensitive",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column("retention_expires_at", sa.DateTime(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "size_bytes IS NULL OR size_bytes >= 0",
            name="ck_evaluation_artifacts_size_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["case_result_id"],
            ["evaluation_case_results.case_result_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["evaluation_runs.run_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("artifact_id"),
    )
    op.create_index(
        "ix_evaluation_artifacts_run_type",
        "evaluation_artifacts",
        ["run_id", "artifact_type"],
    )
    op.create_index(
        "ix_evaluation_artifacts_case_result_id",
        "evaluation_artifacts",
        ["case_result_id"],
    )


def downgrade() -> None:
    op.drop_table("evaluation_artifacts")
    op.drop_table("evaluation_case_results")
    op.drop_table("evaluation_runs")
