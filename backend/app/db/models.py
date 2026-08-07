from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UserDefinedType
from datetime import datetime
import uuid

from app.db.base import Base


class Vector(UserDefinedType):
    cache_ok = True

    def __init__(self, dimension: int):
        self.dimension = dimension

    def get_col_spec(self, **kw):
        return f"vector({self.dimension})"

    def bind_processor(self, dialect):
        def process(value):
            if value is None:
                return None
            if isinstance(value, str):
                return value
            return "[" + ",".join(str(float(item)) for item in value) + "]"

        return process


def uuid_pk():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Category(Base):
    __tablename__ = "categories"

    category_id: Mapped[uuid.UUID] = uuid_pk()
    parent_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.category_id"),
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[uuid.UUID] = uuid_pk()
    category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.category_id"))
    sku: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str | None] = mapped_column(String, unique=True)
    short_description: Mapped[str | None] = mapped_column(Text)
    long_description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String)
    brand: Mapped[str | None] = mapped_column(String)
    manufacturer: Mapped[str | None] = mapped_column(String)
    model_number: Mapped[str | None] = mapped_column(String)
    tags: Mapped[list[str] | None] = mapped_column(JSON)
    use_cases: Mapped[list[str] | None] = mapped_column(JSON)
    target_audience: Mapped[str | None] = mapped_column(Text)
    warranty_months: Mapped[int | None] = mapped_column(Integer)
    return_window_days: Mapped[int | None] = mapped_column(Integer)
    care_instructions: Mapped[str | None] = mapped_column(Text)
    compatibility_notes: Mapped[str | None] = mapped_column(Text)
    included_accessories: Mapped[list[str] | None] = mapped_column(JSON)
    safety_notes: Mapped[str | None] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    cost: Mapped[float | None] = mapped_column(Numeric(12, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ProductVariant(Base):
    __tablename__ = "product_variants"

    variant_id: Mapped[uuid.UUID] = uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.product_id"), nullable=False)
    sku: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    color: Mapped[str | None] = mapped_column(String)
    size: Mapped[str | None] = mapped_column(String)
    material: Mapped[str | None] = mapped_column(String)
    ram_gb: Mapped[int | None] = mapped_column(Integer)
    storage_gb: Mapped[int | None] = mapped_column(Integer)
    storage_type: Mapped[str | None] = mapped_column(String)
    processor: Mapped[str | None] = mapped_column(String)
    gpu: Mapped[str | None] = mapped_column(String)
    display_size: Mapped[str | None] = mapped_column(String)
    battery_life_hours: Mapped[float | None] = mapped_column(Numeric(5, 2))
    option_values: Mapped[dict | None] = mapped_column(JSON)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    cost: Mapped[float | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    barcode: Mapped[str | None] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ProductImage(Base):
    __tablename__ = "product_images"

    image_id: Mapped[uuid.UUID] = uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.product_id"), nullable=False)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.variant_id"))
    url: Mapped[str] = mapped_column(Text, nullable=False)
    alt_text: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ProductSpec(Base):
    __tablename__ = "product_specs"

    spec_id: Mapped[uuid.UUID] = uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.product_id"), nullable=False)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.variant_id"))
    group_name: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[str | None] = mapped_column(String)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ProductReview(Base):
    __tablename__ = "product_reviews"

    review_id: Mapped[uuid.UUID] = uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.product_id"), nullable=False)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.variant_id"))
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class CompetitorPrice(Base):
    __tablename__ = "competitor_prices"

    competitor_price_id: Mapped[uuid.UUID] = uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.product_id"), nullable=False)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.variant_id"))
    competitor_name: Mapped[str] = mapped_column(String, nullable=False)
    competitor_product_url: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class MarketSignal(Base):
    __tablename__ = "market_signals"

    signal_id: Mapped[uuid.UUID] = uuid_pk()
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("products.product_id"))
    category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.category_id"))
    signal_type: Mapped[str] = mapped_column(String, nullable=False)
    region: Mapped[str | None] = mapped_column(String)
    value: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    observed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Warehouse(Base):
    __tablename__ = "warehouses"

    warehouse_id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    city: Mapped[str | None] = mapped_column(String)
    postal_code: Mapped[str | None] = mapped_column(String)
    street_address: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(String)
    country: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint("variant_id", "warehouse_id", name="uq_inventory_variant_warehouse"),
        CheckConstraint("stock_on_hand >= 0", name="ck_stock_on_hand_nonneg"),
        CheckConstraint("reorder_point >= 0", name="ck_reorder_point_nonneg"),
    )

    inventory_id: Mapped[uuid.UUID] = uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.product_id"), nullable=False)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.variant_id"))
    warehouse_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.warehouse_id"), nullable=False)
    stock_on_hand: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reorder_point: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_sales_qty_pos"),
        CheckConstraint("unit_price >= 0", name="ck_sales_unit_price_nonneg"),
        CheckConstraint("revenue >= 0", name="ck_sales_revenue_nonneg"),
    )

    sale_id: Mapped[uuid.UUID] = uuid_pk()
    sold_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.product_id"), nullable=False)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.variant_id"))
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.warehouse_id"))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    revenue: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    channel: Mapped[str] = mapped_column(String, nullable=False)
    region: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class Return(Base):
    __tablename__ = "returns"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_returns_qty_pos"),
    )

    return_id: Mapped[uuid.UUID] = uuid_pk()
    returned_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    sale_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sales.sale_id"))
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.product_id"), nullable=False)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.variant_id"))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ChatUser(Base):
    __tablename__ = "chat_users"

    user_id: Mapped[uuid.UUID] = uuid_pk()
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user")


class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String, default="New chat", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped[ChatUser | None] = relationship(back_populates="conversations")
    messages: Mapped[list["ConversationMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at",
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    message_id: Mapped[uuid.UUID] = uuid_pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.conversation_id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    trace: Mapped[dict | None] = mapped_column(JSON)
    report: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Document(Base):
    __tablename__ = "documents"

    document_id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str] = mapped_column(String, default="manual", nullable=False)
    source_path: Mapped[str | None] = mapped_column(Text)
    department: Mapped[str | None] = mapped_column(String)
    version: Mapped[str | None] = mapped_column(String)
    document_metadata: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index",
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    chunk_id: Mapped[uuid.UUID] = uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    embedding_baai: Mapped[list[float] | None] = mapped_column(Vector(384))
    chunk_metadata: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    document: Mapped[Document] = relationship(back_populates="chunks")


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    __table_args__ = (
        CheckConstraint(
            "selected_case_count >= 0 AND attempted_case_count >= 0 "
            "AND completed_case_count >= 0 AND passed_case_count >= 0 "
            "AND failed_case_count >= 0 AND error_case_count >= 0",
            name="ck_evaluation_runs_counts_nonnegative",
        ),
        CheckConstraint(
            "pass_rate_percent IS NULL OR "
            "(pass_rate_percent >= 0 AND pass_rate_percent <= 100)",
            name="ck_evaluation_runs_pass_rate_range",
        ),
        CheckConstraint(
            "average_score_percent IS NULL OR "
            "(average_score_percent >= 0 AND average_score_percent <= 100)",
            name="ck_evaluation_runs_average_score_range",
        ),
        CheckConstraint(
            "estimated_cost_usd IS NULL OR estimated_cost_usd >= 0",
            name="ck_evaluation_runs_estimated_cost_nonnegative",
        ),
        CheckConstraint(
            "actual_cost_usd IS NULL OR actual_cost_usd >= 0",
            name="ck_evaluation_runs_actual_cost_nonnegative",
        ),
        Index("ix_evaluation_runs_status_created_at", "status", "created_at"),
        Index("ix_evaluation_runs_suite_created_at", "suite_name", "created_at"),
        Index("ix_evaluation_runs_model_created_at", "model", "created_at"),
    )

    run_id: Mapped[uuid.UUID] = uuid_pk()
    baseline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_runs.run_id", ondelete="SET NULL"),
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128),
        unique=True,
    )
    suite_name: Mapped[str] = mapped_column(
        String(120),
        default="productai-agent-evals",
        nullable=False,
    )
    suite_version: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(
        String(32),
        default="queued",
        nullable=False,
    )
    trigger_source: Mapped[str] = mapped_column(
        String(32),
        default="cli",
        nullable=False,
    )
    triggered_by: Mapped[str | None] = mapped_column(String(160))
    environment: Mapped[str | None] = mapped_column(String(64))
    git_commit_sha: Mapped[str | None] = mapped_column(String(64))
    git_branch: Mapped[str | None] = mapped_column(String(255))
    deployment_id: Mapped[str | None] = mapped_column(String(255))
    ci_provider: Mapped[str | None] = mapped_column(String(64))
    ci_run_id: Mapped[str | None] = mapped_column(String(255))
    model_provider: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String(80))
    agent_version: Mapped[str | None] = mapped_column(String(80))
    analysis_depth: Mapped[str | None] = mapped_column(String(32))
    answer_detail: Mapped[str | None] = mapped_column(String(32))
    configuration: Mapped[dict | None] = mapped_column(JSON)
    selection_filters: Mapped[dict | None] = mapped_column(JSON)
    run_metadata: Mapped[dict | None] = mapped_column("metadata", JSON)
    selected_case_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attempted_case_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_case_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed_case_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_case_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_case_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pass_rate_percent: Mapped[float | None] = mapped_column(Numeric(5, 2))
    average_score_percent: Mapped[float | None] = mapped_column(Numeric(5, 2))
    estimated_cost_usd: Mapped[float | None] = mapped_column(Numeric(14, 8))
    actual_cost_usd: Mapped[float | None] = mapped_column(Numeric(14, 8))
    average_latency_ms: Mapped[int | None] = mapped_column(Integer)
    minimum_latency_ms: Mapped[int | None] = mapped_column(Integer)
    maximum_latency_ms: Mapped[int | None] = mapped_column(Integer)
    p95_latency_ms: Mapped[int | None] = mapped_column(Integer)
    total_input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    manifest_uri: Mapped[str | None] = mapped_column(Text)
    report_uri: Mapped[str | None] = mapped_column(Text)
    error_summary: Mapped[str | None] = mapped_column(Text)
    cancellation_requested: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    baseline_run: Mapped["EvaluationRun | None"] = relationship(
        remote_side=[run_id],
        foreign_keys=[baseline_run_id],
    )
    case_results: Mapped[list["EvaluationCaseResult"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )
    artifacts: Mapped[list["EvaluationArtifact"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class EvaluationCaseResult(Base):
    __tablename__ = "evaluation_case_results"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "case_id",
            "attempt_number",
            name="uq_evaluation_case_results_run_case_attempt",
        ),
        CheckConstraint(
            "attempt_number > 0",
            name="ck_evaluation_case_results_attempt_positive",
        ),
        CheckConstraint(
            "score_percent IS NULL OR "
            "(score_percent >= 0 AND score_percent <= 100)",
            name="ck_evaluation_case_results_score_range",
        ),
        CheckConstraint(
            "cost_usd IS NULL OR cost_usd >= 0",
            name="ck_evaluation_case_results_cost_nonnegative",
        ),
        Index(
            "ix_evaluation_case_results_run_status",
            "run_id",
            "status",
        ),
        Index(
            "ix_evaluation_case_results_category_passed",
            "category",
            "passed",
        ),
        Index("ix_evaluation_case_results_case_id", "case_id"),
        Index("ix_evaluation_case_results_trace_id", "trace_id"),
    )

    case_result_id: Mapped[uuid.UUID] = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_runs.run_id", ondelete="CASCADE"),
        nullable=False,
    )
    case_id: Mapped[str] = mapped_column(String(160), nullable=False)
    case_version: Mapped[str | None] = mapped_column(String(80))
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    sequence_number: Mapped[int | None] = mapped_column(Integer)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default="queued",
        nullable=False,
    )
    passed: Mapped[bool | None] = mapped_column(Boolean)
    score_percent: Mapped[float | None] = mapped_column(Numeric(5, 2))
    query: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text)
    final_answer: Mapped[str | None] = mapped_column(Text)
    reference_source: Mapped[str | None] = mapped_column(Text)
    expected_tools: Mapped[list[str] | None] = mapped_column(JSON)
    forbidden_tools: Mapped[list[str] | None] = mapped_column(JSON)
    expected_answer_contains: Mapped[list[str] | None] = mapped_column(JSON)
    expected_answer_terms: Mapped[list[list[str]] | None] = mapped_column(JSON)
    tools_used: Mapped[list[str] | None] = mapped_column(JSON)
    tool_call_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    checks: Mapped[list[dict] | None] = mapped_column(JSON)
    failed_checks: Mapped[list[dict] | None] = mapped_column(JSON)
    trace_id: Mapped[str | None] = mapped_column(String(160))
    guardrail_status: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(120))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(14, 8))
    error_stage: Mapped[str | None] = mapped_column(String(64))
    error_type: Mapped[str | None] = mapped_column(String(160))
    error_message: Mapped[str | None] = mapped_column(Text)
    raw_result_uri: Mapped[str | None] = mapped_column(Text)
    score_result_uri: Mapped[str | None] = mapped_column(Text)
    result_metadata: Mapped[dict | None] = mapped_column("metadata", JSON)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    run: Mapped[EvaluationRun] = relationship(back_populates="case_results")
    artifacts: Mapped[list["EvaluationArtifact"]] = relationship(
        back_populates="case_result",
    )


class EvaluationArtifact(Base):
    __tablename__ = "evaluation_artifacts"
    __table_args__ = (
        CheckConstraint(
            "size_bytes IS NULL OR size_bytes >= 0",
            name="ck_evaluation_artifacts_size_nonnegative",
        ),
        Index(
            "ix_evaluation_artifacts_run_type",
            "run_id",
            "artifact_type",
        ),
        Index(
            "ix_evaluation_artifacts_case_result_id",
            "case_result_id",
        ),
    )

    artifact_id: Mapped[uuid.UUID] = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_runs.run_id", ondelete="CASCADE"),
        nullable=False,
    )
    case_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "evaluation_case_results.case_result_id",
            ondelete="CASCADE",
        ),
    )
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_provider: Mapped[str] = mapped_column(
        String(32),
        default="local",
        nullable=False,
    )
    uri: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(160))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    is_sensitive: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    retention_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    artifact_metadata: Mapped[dict | None] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    run: Mapped[EvaluationRun] = relationship(back_populates="artifacts")
    case_result: Mapped[EvaluationCaseResult | None] = relationship(
        back_populates="artifacts",
    )


class PageView(Base):
    """One visit to a public page.

    The raw client IP is never stored. It is salted and hashed so distinct
    visitors can still be counted, while the stored row stays non-identifying.
    """

    __tablename__ = "page_views"

    view_id: Mapped[uuid.UUID] = uuid_pk()
    path: Mapped[str] = mapped_column(String(300), nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(64))
    visitor_hash: Mapped[str | None] = mapped_column(String(64))
    country: Mapped[str | None] = mapped_column(String(80))
    country_code: Mapped[str | None] = mapped_column(String(2))
    city: Mapped[str | None] = mapped_column(String(120))
    referrer: Mapped[str | None] = mapped_column(String(500))
    user_agent: Mapped[str | None] = mapped_column(String(400))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        Index("ix_page_views_created_at", "created_at"),
        Index("ix_page_views_path_created_at", "path", "created_at"),
    )
