# schemas.py
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict
from sqlmodel import Field, SQLModel


# These models are used for API input/output validation and are distinct from the database models.
# This allows us to control what data is exposed via the API.

# Shared properties for a user
class UserBase(SQLModel):
    username: str
    role: str = "customer"

# Properties for creating a new user (input)
class UserCreate(UserBase):
    password: str

# Properties to return from the API (output), excluding the password
class UserPublic(UserBase):
    id: int
    re_onboarding_allowed: bool = False
    re_onboarding_allowed_at: Optional[datetime] = None
    re_onboarding_allowed_by: Optional[int] = None
    re_onboarding_reason: Optional[str] = None

# Shared properties for a category
class CategoryBase(SQLModel):
    name: str

# Properties for creating a new category (input)
class CategoryCreate(CategoryBase):
    pass

# Properties to return from the API (output)
class CategoryPublic(CategoryBase):
    id: int

# Shared properties for a review
class ReviewBase(SQLModel):
    text: str
    rating: int

# Properties for creating a new review (input)
class ReviewCreate(ReviewBase):
    product_id: int
    # user_id will be taken from the current authenticated user in a later part

# Public model for a review, including the user who wrote it
class ReviewPublic(ReviewBase):
    id: int
    user: UserPublic # Nested model to show user details

# Shared properties for a product
class ProductBase(SQLModel):
    name: str
    description: str
    price: float

# Properties for creating a new product (input)
class ProductCreate(ProductBase):
    category_id: int

# Public model for a product, including nested category and review info
class ProductPublic(ProductBase):
    id: int
    category: CategoryPublic
    reviews: List[ReviewPublic] = []

# To avoid circular imports, we can create specific models for nested data
# that don't have their own nested relationships.

class CategoryPublicWithProducts(CategoryPublic):
    products: List[ProductPublic] = []

class UserPublicWithReviews(UserPublic):
    reviews: List[ReviewPublic] = []

class OrderCreate(SQLModel):
    customer_name: str
    item: str

class OrderResponse(SQLModel):
    id: int
    customer_name: str
    item: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class OnboardingSessionBase(SQLModel):
    status: str
    current_step: str


class OnboardingSessionCreate(SQLModel):
    pass


class OnboardingFaceVerificationPayload(BaseModel):
    result: str
    distance: float
    threshold: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}

class OnboardingFaceVerificationPublic(BaseModel):
    id: int
    session_id: int
    result: str
    distance: float
    threshold: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}
    captured_file_path: str
    reference_file_path: Optional[str] = None
    captured_file_name: Optional[str] = None
    reference_file_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class OnboardingOCRPayload(SQLModel):
    front: Dict[str, Any]
    back: Optional[Dict[str, Any]] = None
    mergedText: str
    completedAt: str
    fields: Dict[str, Any]
    frontDetection: Dict[str, Any]
    backDetection: Optional[Dict[str, Any]] = None

class OnboardingOCRExtractionPublic(SQLModel):
    id: int
    session_id: int
    front_file_path: str
    back_file_path: Optional[str] = None
    front_file_name: Optional[str] = None
    back_file_name: Optional[str] = None
    front_text: str
    back_text: Optional[str] = None
    merged_text: str
    fields: Dict[str, Any]
    front_detection: Dict[str, Any]
    back_detection: Optional[Dict[str, Any]] = None
    completed_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerAddressPayload(BaseModel):
    address_line: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    postal_code: Optional[str] = None


class CustomerNomineePayload(BaseModel):
    nominee_name: Optional[str] = None
    relationship: Optional[str] = None


class CustomerIdentityFormPayload(BaseModel):
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
    beneficial_owner_different: bool = False
    beneficial_owner_name: Optional[str] = None
    beneficial_owner_nationality: Optional[str] = None
    beneficial_owner_identification_number: Optional[str] = None
    beneficial_owner_relationship: Optional[str] = None
    present_address: CustomerAddressPayload = CustomerAddressPayload()
    permanent_address: CustomerAddressPayload = CustomerAddressPayload()
    nominee: CustomerNomineePayload = CustomerNomineePayload()
    metadata: Dict[str, Any] = {}


class CustomerAddressPublic(BaseModel):
    id: Optional[int] = None
    address_type: str
    address_line: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    postal_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CustomerNomineePublic(BaseModel):
    id: Optional[int] = None
    nominee_name: Optional[str] = None
    relationship: Optional[str] = None
    photograph_file_path: Optional[str] = None
    photograph_file_name: Optional[str] = None
    metadata: Dict[str, Any] = {}

    model_config = ConfigDict(from_attributes=True)


class CustomerIdentityProfilePublic(BaseModel):
    id: int
    session_id: int
    form_type: str
    risk_category: str
    status: str
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
    beneficial_owner_different: bool = False
    beneficial_owner_name: Optional[str] = None
    beneficial_owner_nationality: Optional[str] = None
    beneficial_owner_identification_number: Optional[str] = None
    beneficial_owner_relationship: Optional[str] = None
    ocr_snapshot: Dict[str, Any]
    ocr_corrections: Dict[str, Any]
    metadata: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CustomerIdentityFormResponse(BaseModel):
    profile: CustomerIdentityProfilePublic
    addresses: Dict[str, Optional[CustomerAddressPublic]]
    nominee: Optional[CustomerNomineePublic] = None
    document_references: Dict[str, Optional[Dict[str, Any]]]
    session: Optional[Any] = None


class CustomerIdentitySubmitResponse(BaseModel):
    message: str
    form: CustomerIdentityFormResponse
    session: Any

class OnboardingSignaturePayload(BaseModel):
    signatureMethod: str
    verificationMethod: str
    accountRisk: str
    signatureImage: Optional[Dict[str, Any]] = None
    digitalSignature: Optional[Dict[str, Any]] = None
    pinAuthorization: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}
    auditLog: List[Dict[str, Any]] = []
    integrityHash: str
    signerName: Optional[str] = None


class OnboardingSignatureCapturePublic(BaseModel):
    id: int
    session_id: int
    signature_method: str
    verification_method: str
    account_risk: str
    signer_name: Optional[str] = None
    signature_file_path: Optional[str] = None
    signature_file_name: Optional[str] = None
    signature_record: Dict[str, Any]
    audit_log: List[Dict[str, Any]]
    metadata: Dict[str, Any] = {}
    integrity_hash: str
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplianceSummaryPublic(BaseModel):
    screening_request_id: Optional[int] = None
    screening_status: str = "NOT_STARTED"
    final_decision: Optional[str] = None
    risk_category: Optional[str] = None
    risk_score: Optional[int] = None
    review_required: bool = False
    activation_eligible: bool = False
    last_updated_at: Optional[datetime] = None


class OnboardingSessionPublic(SQLModel):
    id: int
    user_id: int
    status: str
    current_step: str
    workflow_state: str
    completed_steps: List[str] = []
    next_required_step: str
    draft_availability: Dict[str, bool] = {}
    document_references: Dict[str, Optional[Dict[str, Any]]] = {}
    risk_category: Optional[str] = None
    activation_status: str
    started_at: datetime
    updated_at: datetime
    last_resumed_at: Optional[datetime] = None
    resume_count: int = 0
    completed_at: Optional[datetime] = None
    face_verification: Optional[OnboardingFaceVerificationPublic] = None
    ocr_extraction: Optional[OnboardingOCRExtractionPublic] = None
    signature_capture: Optional[OnboardingSignatureCapturePublic] = None
    compliance_summary: ComplianceSummaryPublic | None = None

    model_config = ConfigDict(from_attributes=True)


class OnboardingStepResponse(SQLModel):
    message: str
    session: OnboardingSessionPublic

    model_config = ConfigDict(from_attributes=True)


class OnboardingSessionSummary(SQLModel):
    id: int
    user_id: int
    status: str
    current_step: str
    workflow_state: str
    completed_steps: List[str] = []
    next_required_step: str
    draft_availability: Dict[str, bool] = {}
    risk_category: Optional[str] = None
    activation_status: str
    started_at: datetime
    updated_at: datetime
    last_resumed_at: Optional[datetime] = None
    resume_count: int = 0
    completed_at: Optional[datetime] = None
    compliance_summary: ComplianceSummaryPublic | None = None

    model_config = ConfigDict(from_attributes=True)


class OnboardingSessionListResponse(SQLModel):
    items: List[OnboardingSessionSummary]

    model_config = ConfigDict(from_attributes=True)


class OnboardingEligibilityResponse(BaseModel):
    user_id: int
    username: str
    latest_session: Optional[OnboardingSessionSummary] = None
    can_start_onboarding: bool
    can_resume_onboarding: bool
    re_onboarding_allowed: bool
    destination: str
    message: str


class ReOnboardingApprovalPayload(BaseModel):
    reason: str
    notes: Optional[str] = None


class AdminCustomerOnboardingPublic(BaseModel):
    user_id: int
    username: str
    role: str
    re_onboarding_allowed: bool
    re_onboarding_allowed_at: Optional[datetime] = None
    re_onboarding_allowed_by: Optional[int] = None
    re_onboarding_reason: Optional[str] = None
    latest_session: Optional[OnboardingSessionSummary] = None


class AdminCustomerOnboardingListResponse(BaseModel):
    items: List[AdminCustomerOnboardingPublic]


class ScreeningStartRequest(SQLModel):
    session_id: int
    trigger_source: str = "manual"


class ScreeningStatusPublic(BaseModel):
    id: int
    session_id: int
    user_id: int
    status: str
    trigger_source: str
    workflow_id: Optional[str] = None
    retry_count: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    decision: Optional[str] = None
    risk_category: Optional[str] = None
    risk_score: Optional[int] = None
    review_required: bool = False
    activation_eligible: bool = False

    model_config = ConfigDict(from_attributes=True)


class ScreeningResultPublic(BaseModel):
    id: int
    screening_type: str
    provider_name: str
    list_name: Optional[str] = None
    outcome: str
    confidence_score: float
    matched_fields: Dict[str, Any]
    risk_factors: List[str]
    evidence_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskAssessmentPublic(BaseModel):
    risk_score: int
    risk_category: str
    factors: List[Dict[str, Any]]
    rules_snapshot: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class CustomerRiskFactorScorePublic(BaseModel):
    id: int
    factor_name: str
    factor_score: int
    source: str
    source_value: Dict[str, Any]
    rule_version: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerRiskAssessmentPublic(BaseModel):
    id: int
    session_id: int
    screening_request_id: Optional[int] = None
    assessment_type: str
    status: str
    total_score: int
    risk_category: str
    rule_version: str
    edd_required: bool
    edd_status: Optional[str] = None
    edd_reasons: List[str]
    rules_snapshot: Dict[str, Any]
    calculated_at: datetime
    created_at: datetime
    updated_at: datetime
    factors: List[CustomerRiskFactorScorePublic] = []

    model_config = ConfigDict(from_attributes=True)


class RiskAssessmentCalculateRequest(BaseModel):
    session_id: int
    assessment_type: str = "final"
    trigger_source: str = "manual"


class RiskCategoryChangePayload(BaseModel):
    reason: str


class RiskBusinessCategoryCreate(BaseModel):
    category_code: str
    category_name: str
    risk_score: int
    description: Optional[str] = None
    is_active: bool = True
    reason: str = "Category created."


class RiskBusinessCategoryUpdate(BaseModel):
    category_code: Optional[str] = None
    category_name: Optional[str] = None
    risk_score: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    reason: str


class RiskBusinessCategoryPublic(BaseModel):
    id: int
    category_code: str
    category_name: str
    risk_score: int
    description: Optional[str] = None
    is_active: bool
    created_by: Optional[int] = None
    usage_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskBusinessCategoryListResponse(BaseModel):
    items: List[RiskBusinessCategoryPublic] = []
    total: int


class RiskProfessionCategoryCreate(BaseModel):
    profession_code: str
    profession_name: str
    risk_score: int
    description: Optional[str] = None
    is_active: bool = True
    reason: str = "Profession category created."


class RiskProfessionCategoryUpdate(BaseModel):
    profession_code: Optional[str] = None
    profession_name: Optional[str] = None
    risk_score: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    reason: str


class RiskProfessionCategoryPublic(BaseModel):
    id: int
    profession_code: str
    profession_name: str
    risk_score: int
    description: Optional[str] = None
    is_active: bool
    created_by: Optional[int] = None
    usage_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskProfessionCategoryListResponse(BaseModel):
    items: List[RiskProfessionCategoryPublic] = []
    total: int


class RiskRuleVersionPublic(BaseModel):
    id: int
    version: str
    effective_date: datetime
    status: str
    thresholds: Dict[str, Any]
    rules_snapshot: Dict[str, Any]
    created_by: Optional[int] = None
    change_notes: Optional[str] = None
    activated_at: Optional[datetime] = None
    retired_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskRuleVersionListResponse(BaseModel):
    items: List[RiskRuleVersionPublic] = []


class RiskRuleVersionClonePayload(BaseModel):
    version: str
    change_notes: str


class RiskFactorDefinitionPublic(BaseModel):
    id: int
    factor_code: str
    factor_name: str
    factor_group: str
    source_key: str
    aggregation_mode: str
    description: Optional[str] = None
    is_active: bool
    display_order: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskFactorRulePublic(BaseModel):
    id: int
    rule_version_id: int
    factor_definition_id: int
    rule_code: str
    rule_type: str
    match_value: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    boolean_value: Optional[bool] = None
    risk_score: int
    description: Optional[str] = None
    is_active: bool
    effective_date: datetime
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskFactorRulePayload(BaseModel):
    factor_definition_id: int
    rule_code: str
    rule_type: str
    match_value: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    boolean_value: Optional[bool] = None
    risk_score: int
    description: Optional[str] = None
    is_active: bool = True
    reason: str


class RiskFactorRulesResponse(BaseModel):
    definitions: List[RiskFactorDefinitionPublic] = []
    rules: List[RiskFactorRulePublic] = []


class RiskThresholdBandPublic(BaseModel):
    id: int
    rule_version_id: int
    category_code: str
    category_name: str
    min_score: int
    max_score: Optional[int] = None
    is_active: bool
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskThresholdBandPayload(BaseModel):
    category_code: str
    category_name: str
    min_score: int
    max_score: Optional[int] = None
    is_active: bool = True
    reason: str


class RiskTransactionRangePublic(BaseModel):
    id: int
    rule_version_id: int
    range_code: str
    range_name: str
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    risk_score: int
    is_active: bool
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskTransactionRangePayload(BaseModel):
    range_code: str
    range_name: str
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    risk_score: int
    is_active: bool = True
    reason: str


class RiskProductCategoryPublic(BaseModel):
    id: int
    rule_version_id: int
    product_code: str
    product_name: str
    product_category: str
    risk_score: int
    is_active: bool
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskProductCategoryPayload(BaseModel):
    product_code: str
    product_name: str
    product_category: str
    risk_score: int
    is_active: bool = True
    reason: str


class AuditLogPublic(BaseModel):
    id: int
    actor_user_id: Optional[int] = None
    event_type: str
    event_status: str
    message: str
    payload: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScreeningDetailsResponse(BaseModel):
    screening: ScreeningStatusPublic
    risk_assessment: Optional[RiskAssessmentPublic] = None
    customer_risk_assessment: Optional[CustomerRiskAssessmentPublic] = None
    results: List[ScreeningResultPublic] = []
    audit_logs: List[AuditLogPublic] = []


class CaseDecisionPayload(SQLModel):
    reason: str
    notes: Optional[str] = None


class ComplianceCasePublic(BaseModel):
    id: int
    screening_request_id: int
    status: str
    queue_name: str
    reviewer_id: Optional[int] = None
    opened_at: datetime
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    screening_status: str
    decision: Optional[str] = None
    risk_category: Optional[str] = None
    risk_score: Optional[int] = None
    username: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ComplianceCaseListResponse(BaseModel):
    items: List[ComplianceCasePublic]


class ComplianceCaseDetailResponse(BaseModel):
    case: ComplianceCasePublic
    screening: ScreeningStatusPublic
    risk_assessment: Optional[RiskAssessmentPublic] = None
    customer_risk_assessment: Optional[CustomerRiskAssessmentPublic] = None
    results: List[ScreeningResultPublic] = []
    audit_logs: List[AuditLogPublic] = []
