export interface ComplianceSummary {
  screening_request_id?: number | null;
  screening_status: string;
  final_decision?: string | null;
  risk_category?: string | null;
  risk_score?: number | null;
  review_required: boolean;
  activation_eligible: boolean;
  last_updated_at?: string | null;
}

export interface ScreeningStatus {
  id: number;
  session_id: number;
  user_id: number;
  status: string;
  trigger_source: string;
  workflow_id?: string | null;
  retry_count: number;
  started_at?: string | null;
  completed_at?: string | null;
  last_error?: string | null;
  created_at: string;
  updated_at: string;
  decision?: string | null;
  risk_category?: string | null;
  risk_score?: number | null;
  review_required: boolean;
  activation_eligible: boolean;
}

export interface ScreeningResult {
  id: number;
  screening_type: string;
  provider_name: string;
  list_name?: string | null;
  outcome: string;
  confidence_score: number;
  matched_fields: Record<string, unknown>;
  risk_factors: string[];
  evidence_summary?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RiskAssessment {
  risk_score: number;
  risk_category: string;
  factors: Array<Record<string, unknown>>;
  rules_snapshot: Record<string, unknown>;
}

export interface CustomerRiskFactorScore {
  id: number;
  factor_name: string;
  factor_code?: string | null;
  factor_score: number;
  source: string;
  source_table?: string | null;
  selected_value?: string | null;
  rule_id?: number | null;
  match_status: string;
  source_value: Record<string, unknown>;
  rule_version: string;
  created_at: string;
}

export interface CustomerRiskAssessment {
  id: number;
  session_id: number;
  screening_request_id?: number | null;
  assessment_type: string;
  status: string;
  total_score: number;
  risk_category: string;
  rule_version: string;
  edd_required: boolean;
  edd_status?: string | null;
  edd_reasons: string[];
  rules_snapshot: Record<string, unknown>;
  calculated_at: string;
  created_at: string;
  updated_at: string;
  factors: CustomerRiskFactorScore[];
}

export interface AuditLogEntry {
  id: number;
  actor_user_id?: number | null;
  event_type: string;
  event_status: string;
  message: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface RiskBusinessCategory {
  id: number;
  category_code: string;
  category_name: string;
  risk_score: number;
  description?: string | null;
  is_active: boolean;
  created_by?: number | null;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

export interface RiskProfessionCategory {
  id: number;
  profession_code: string;
  profession_name: string;
  risk_score: number;
  description?: string | null;
  is_active: boolean;
  created_by?: number | null;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

export interface RiskBusinessCategoryListResponse {
  items: RiskBusinessCategory[];
  total: number;
}

export interface RiskProfessionCategoryListResponse {
  items: RiskProfessionCategory[];
  total: number;
}

export interface RiskBusinessCategoryPayload {
  category_code: string;
  category_name: string;
  risk_score: number;
  description?: string | null;
  is_active?: boolean;
  reason: string;
}

export interface RiskProfessionCategoryPayload {
  profession_code: string;
  profession_name: string;
  risk_score: number;
  description?: string | null;
  is_active?: boolean;
  reason: string;
}

export interface RiskRuleVersion {
  id: number;
  version: string;
  effective_date: string;
  status: string;
  thresholds: Record<string, unknown>;
  rules_snapshot: Record<string, unknown>;
  created_by?: number | null;
  change_notes?: string | null;
  activated_at?: string | null;
  retired_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RiskFactorDefinition {
  id: number;
  factor_code: string;
  factor_name: string;
  factor_group: string;
  source_key: string;
  aggregation_mode: string;
  description?: string | null;
  is_active: boolean;
  display_order: number;
  created_at: string;
  updated_at: string;
}

export interface RiskFactorRule {
  id: number;
  rule_version_id: number;
  factor_definition_id: number;
  rule_code: string;
  rule_type: string;
  match_value?: string | null;
  min_value?: number | null;
  max_value?: number | null;
  boolean_value?: boolean | null;
  risk_score: number;
  description?: string | null;
  is_active: boolean;
  effective_date: string;
  created_at: string;
  updated_at: string;
}

export interface RiskFactorRulesResponse {
  definitions: RiskFactorDefinition[];
  rules: RiskFactorRule[];
}

export interface RiskOption {
  value: string;
  label: string;
  source: string;
  score?: number | null;
}

export interface RiskAssessmentOptions {
  professions: RiskOption[];
  business_categories: RiskOption[];
  product_types: RiskOption[];
  nationalities: RiskOption[];
  residency_statuses: RiskOption[];
  source_of_funds: RiskOption[];
  expected_transaction_ranges: RiskOption[];
  beneficial_ownership: RiskOption[];
  onboarding_channels: RiskOption[];
}

export interface RiskThresholdBand {
  id: number;
  rule_version_id: number;
  category_code: string;
  category_name: string;
  min_score: number;
  max_score?: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RiskTransactionRange {
  id: number;
  rule_version_id: number;
  range_code: string;
  range_name: string;
  min_amount?: number | null;
  max_amount?: number | null;
  risk_score: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RiskProductCategory {
  id: number;
  rule_version_id: number;
  product_code: string;
  product_name: string;
  product_category: string;
  risk_score: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ScreeningDetails {
  screening: ScreeningStatus;
  risk_assessment?: RiskAssessment | null;
  customer_risk_assessment?: CustomerRiskAssessment | null;
  results: ScreeningResult[];
  audit_logs: AuditLogEntry[];
}

export interface ComplianceCase {
  id: number;
  screening_request_id: number;
  status: string;
  queue_name: string;
  reviewer_id?: number | null;
  opened_at: string;
  resolved_at?: string | null;
  resolution_note?: string | null;
  created_at: string;
  updated_at: string;
  screening_status: string;
  decision?: string | null;
  risk_category?: string | null;
  risk_score?: number | null;
  username?: string | null;
}

export interface ComplianceCaseDetail {
  case: ComplianceCase;
  screening: ScreeningStatus;
  risk_assessment?: RiskAssessment | null;
  customer_risk_assessment?: CustomerRiskAssessment | null;
  results: ScreeningResult[];
  audit_logs: AuditLogEntry[];
}
