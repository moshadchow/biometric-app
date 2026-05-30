# models.py
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import Column, Index, JSON, text
from sqlmodel import Field, Relationship, SQLModel


def utc_now() -> datetime:
    return datetime.utcnow()

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password: str
    role: str = "customer"
    re_onboarding_allowed: bool = Field(default=False, index=True)
    re_onboarding_allowed_at: Optional[datetime] = None
    re_onboarding_allowed_by: Optional[int] = Field(default=None, foreign_key="user.id")
    re_onboarding_reason: Optional[str] = None

    # This relationship is named "reviews"
    reviews: List["Review"] = Relationship(back_populates="user")

class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)

    # This relationship is named "products"
    products: List["Product"] = Relationship(back_populates="category")

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str
    price: float
    category_id: int = Field(foreign_key="category.id")
    
    # Corrected: back_populates now points to "products" in the Category model
    category: Category = Relationship(back_populates="products") 
    
    # This relationship is named "reviews"
    reviews: List["Review"] = Relationship(back_populates="products")

class Review(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    text: str
    rating: int

    user_id: int = Field(foreign_key="user.id")
    # Corrected: back_populates now points to "reviews" in the User model
    user: User = Relationship(back_populates="reviews")

    product_id: int = Field(foreign_key="product.id")
    # Corrected: back_populates now points to "reviews" in the Product model
    products: Product = Relationship(back_populates="reviews")


class ProductOrder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_name: str
    item: str
    status: str = Field(default="Order Is Placed")


class OnboardingSession(SQLModel, table=True):
    __tablename__ = "onboarding_session"
    __table_args__ = (
        Index(
            "uq_onboarding_session_active_user_id",
            "user_id",
            unique=True,
            postgresql_where=text("status NOT IN ('completed', 'rejected')"),
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    status: str = Field(default="in_progress", index=True)
    current_step: str = Field(default="face_verification", index=True)
    workflow_state: str = Field(default="ONBOARDING_STARTED", index=True)
    completed_steps: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    activation_status: str = Field(default="blocked", index=True)
    started_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_resumed_at: Optional[datetime] = None
    resume_count: int = Field(default=0)
    completed_at: Optional[datetime] = None


class OnboardingFaceVerification(SQLModel, table=True):
    __tablename__ = "onboarding_face_verification"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="onboarding_session.id", index=True, unique=True)
    result: str
    distance: float
    threshold: float
    error_message: Optional[str] = None
    captured_file_path: str
    reference_file_path: Optional[str] = None
    captured_file_name: Optional[str] = None
    reference_file_name: Optional[str] = None
    payload_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON),
    )
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class OnboardingOCRExtraction(SQLModel, table=True):
    __tablename__ = "onboarding_ocr_extraction"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="onboarding_session.id", index=True, unique=True)
    front_file_path: str
    back_file_path: Optional[str] = None
    front_file_name: Optional[str] = None
    back_file_name: Optional[str] = None
    front_text: str
    back_text: Optional[str] = None
    merged_text: str
    fields: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    front_detection: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    back_detection: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    completed_at: datetime = Field(default_factory=utc_now)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CustomerIdentityProfile(SQLModel, table=True):
    __tablename__ = "customer_identity_profiles"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="onboarding_session.id", index=True, unique=True)
    form_type: str = Field(index=True)
    risk_category: str = Field(index=True)
    status: str = Field(default="IDENTITY_FORM_PENDING", index=True)
    applicant_name: Optional[str] = None
    account_number: Optional[str] = None
    unique_account_number: Optional[str] = None
    nid_number: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    spouse_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    profession: Optional[str] = None
    mobile_number: Optional[str] = None
    monthly_income: Optional[str] = None
    nationality: Optional[str] = None
    source_of_funds: Optional[str] = None
    tin: Optional[str] = None
    expected_transaction_range: Optional[str] = None
    expected_transaction_pattern: Optional[str] = None
    existing_customer_review: Optional[str] = None
    additional_documents_obtained: Optional[str] = None
    additional_remarks: Optional[str] = None
    beneficial_owner_different: bool = Field(default=False)
    beneficial_owner_name: Optional[str] = None
    beneficial_owner_nationality: Optional[str] = None
    beneficial_owner_identification_number: Optional[str] = None
    beneficial_owner_relationship: Optional[str] = None
    ocr_snapshot: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    ocr_corrections: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    payload_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column("metadata", JSON))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    submitted_at: Optional[datetime] = None


class CustomerAddress(SQLModel, table=True):
    __tablename__ = "customer_addresses"
    __table_args__ = (
        Index("uq_customer_address_profile_type", "profile_id", "address_type", unique=True),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="customer_identity_profiles.id", index=True)
    address_type: str = Field(index=True)
    address_line: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    postal_code: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CustomerNominee(SQLModel, table=True):
    __tablename__ = "customer_nominees"

    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="customer_identity_profiles.id", index=True, unique=True)
    nominee_name: Optional[str] = None
    relationship: Optional[str] = None
    photograph_file_path: Optional[str] = None
    photograph_file_name: Optional[str] = None
    payload_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column("metadata", JSON))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class OnboardingSignatureCapture(SQLModel, table=True):
    __tablename__ = "onboarding_signature_capture"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="onboarding_session.id", index=True, unique=True)
    signature_method: str
    verification_method: str
    account_risk: str
    signer_name: Optional[str] = None
    signature_file_path: Optional[str] = None
    signature_file_name: Optional[str] = None
    signature_record: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    audit_log: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    payload_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON),
    )
    integrity_hash: str
    submitted_at: datetime = Field(default_factory=utc_now)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ScreeningRequest(SQLModel, table=True):
    __tablename__ = "screening_request"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="onboarding_session.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    status: str = Field(default="SCREENING_PENDING", index=True)
    trigger_source: str = Field(default="ocr_completion")
    workflow_id: Optional[str] = Field(default=None, index=True)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_error: Optional[str] = None
    retry_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ScreeningJob(SQLModel, table=True):
    __tablename__ = "screening_job"

    id: Optional[int] = Field(default=None, primary_key=True)
    screening_request_id: int = Field(foreign_key="screening_request.id", index=True)
    job_name: str = Field(index=True)
    celery_task_id: Optional[str] = Field(default=None, index=True)
    status: str = Field(default="PENDING", index=True)
    retry_count: int = Field(default=0)
    last_error: Optional[str] = None
    payload_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column("metadata", JSON))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ScreeningResult(SQLModel, table=True):
    __tablename__ = "screening_result"

    id: Optional[int] = Field(default=None, primary_key=True)
    screening_request_id: int = Field(foreign_key="screening_request.id", index=True)
    screening_type: str = Field(index=True)
    provider_name: str
    list_name: Optional[str] = None
    outcome: str = Field(index=True)
    confidence_score: float = Field(default=0.0)
    matched_fields: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    risk_factors: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    evidence_summary: Optional[str] = None
    raw_payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class RiskAssessment(SQLModel, table=True):
    __tablename__ = "risk_assessment"

    id: Optional[int] = Field(default=None, primary_key=True)
    screening_request_id: int = Field(foreign_key="screening_request.id", index=True, unique=True)
    risk_score: int
    risk_category: str = Field(index=True)
    factors: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    rules_snapshot: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class RiskRuleVersion(SQLModel, table=True):
    __tablename__ = "risk_rule_versions"

    id: Optional[int] = Field(default=None, primary_key=True)
    version: str = Field(index=True, unique=True)
    effective_date: datetime = Field(default_factory=utc_now)
    status: str = Field(default="ACTIVE", index=True)
    thresholds: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    rules_snapshot: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_by: Optional[int] = Field(default=None, foreign_key="user.id")
    change_notes: Optional[str] = None
    activated_at: Optional[datetime] = None
    retired_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class RiskFactorDefinition(SQLModel, table=True):
    __tablename__ = "risk_factor_definitions"

    id: Optional[int] = Field(default=None, primary_key=True)
    factor_code: str = Field(index=True, unique=True)
    factor_name: str = Field(index=True)
    factor_group: str = Field(index=True)
    source_key: str = Field(index=True)
    aggregation_mode: str = Field(default="max")
    description: Optional[str] = None
    is_active: bool = Field(default=True, index=True)
    display_order: int = Field(default=0, index=True)
    created_by: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class RiskFactorRule(SQLModel, table=True):
    __tablename__ = "risk_factor_rules"

    id: Optional[int] = Field(default=None, primary_key=True)
    rule_version_id: int = Field(foreign_key="risk_rule_versions.id", index=True)
    factor_definition_id: int = Field(foreign_key="risk_factor_definitions.id", index=True)
    rule_code: str = Field(index=True)
    rule_type: str = Field(index=True)
    match_value: Optional[str] = Field(default=None, index=True)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    boolean_value: Optional[bool] = None
    risk_score: int
    description: Optional[str] = None
    is_active: bool = Field(default=True, index=True)
    effective_date: datetime = Field(default_factory=utc_now)
    created_by: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class RiskThresholdBand(SQLModel, table=True):
    __tablename__ = "risk_threshold_bands"

    id: Optional[int] = Field(default=None, primary_key=True)
    rule_version_id: int = Field(foreign_key="risk_rule_versions.id", index=True)
    category_code: str = Field(index=True)
    category_name: str = Field(index=True)
    min_score: int
    max_score: Optional[int] = None
    is_active: bool = Field(default=True, index=True)
    created_by: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class RiskTransactionRange(SQLModel, table=True):
    __tablename__ = "risk_transaction_ranges"

    id: Optional[int] = Field(default=None, primary_key=True)
    rule_version_id: int = Field(foreign_key="risk_rule_versions.id", index=True)
    range_code: str = Field(index=True)
    range_name: str = Field(index=True)
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    risk_score: int
    is_active: bool = Field(default=True, index=True)
    created_by: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class RiskProductCategory(SQLModel, table=True):
    __tablename__ = "risk_product_categories"

    id: Optional[int] = Field(default=None, primary_key=True)
    rule_version_id: int = Field(foreign_key="risk_rule_versions.id", index=True)
    product_code: str = Field(index=True)
    product_name: str = Field(index=True)
    product_category: str = Field(index=True)
    risk_score: int
    is_active: bool = Field(default=True, index=True)
    created_by: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class RiskBusinessCategory(SQLModel, table=True):
    __tablename__ = "risk_business_categories"

    id: Optional[int] = Field(default=None, primary_key=True)
    category_code: str = Field(index=True, unique=True)
    category_name: str = Field(index=True, unique=True)
    risk_score: int
    description: Optional[str] = None
    is_active: bool = Field(default=True, index=True)
    created_by: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class RiskProfessionCategory(SQLModel, table=True):
    __tablename__ = "risk_profession_categories"

    id: Optional[int] = Field(default=None, primary_key=True)
    profession_code: str = Field(index=True, unique=True)
    profession_name: str = Field(index=True, unique=True)
    risk_score: int
    description: Optional[str] = None
    is_active: bool = Field(default=True, index=True)
    created_by: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CustomerRiskAssessment(SQLModel, table=True):
    __tablename__ = "customer_risk_assessments"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="onboarding_session.id", index=True)
    screening_request_id: Optional[int] = Field(default=None, foreign_key="screening_request.id", index=True)
    assessment_type: str = Field(index=True)
    status: str = Field(default="RISK_PENDING", index=True)
    total_score: int = Field(default=0)
    risk_category: str = Field(default="LOW", index=True)
    rule_version: str = Field(index=True)
    edd_required: bool = Field(default=False, index=True)
    edd_status: Optional[str] = Field(default=None, index=True)
    edd_reasons: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    rules_snapshot: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    calculated_at: datetime = Field(default_factory=utc_now)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CustomerRiskFactorScore(SQLModel, table=True):
    __tablename__ = "customer_risk_factor_scores"

    id: Optional[int] = Field(default=None, primary_key=True)
    assessment_id: int = Field(foreign_key="customer_risk_assessments.id", index=True)
    factor_name: str = Field(index=True)
    factor_score: int
    source: str = Field(index=True)
    source_value: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    rule_version: str = Field(index=True)
    created_at: datetime = Field(default_factory=utc_now)


class ComplianceCase(SQLModel, table=True):
    __tablename__ = "compliance_case"

    id: Optional[int] = Field(default=None, primary_key=True)
    screening_request_id: int = Field(foreign_key="screening_request.id", index=True, unique=True)
    status: str = Field(default="OPEN", index=True)
    queue_name: str = Field(default="COMPLIANCE_REVIEW_QUEUE")
    reviewer_id: Optional[int] = Field(default=None, foreign_key="user.id")
    opened_at: datetime = Field(default_factory=utc_now)
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ScreeningDecision(SQLModel, table=True):
    __tablename__ = "screening_decision"

    id: Optional[int] = Field(default=None, primary_key=True)
    screening_request_id: int = Field(foreign_key="screening_request.id", index=True, unique=True)
    decision: str = Field(index=True)
    decision_source: str = Field(default="system", index=True)
    reviewer_id: Optional[int] = Field(default=None, foreign_key="user.id")
    previous_decision: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None
    decided_at: datetime = Field(default_factory=utc_now)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    screening_request_id: Optional[int] = Field(default=None, foreign_key="screening_request.id", index=True)
    session_id: Optional[int] = Field(default=None, foreign_key="onboarding_session.id", index=True)
    actor_user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    event_type: str = Field(index=True)
    event_status: str = Field(default="info", index=True)
    message: str
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)
