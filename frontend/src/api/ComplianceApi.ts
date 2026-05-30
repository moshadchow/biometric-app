import api from "./ApiService";
import type {
  ComplianceCase,
  ComplianceCaseDetail,
  CustomerRiskAssessment,
  AuditLogEntry,
  RiskBusinessCategory,
  RiskBusinessCategoryListResponse,
  RiskBusinessCategoryPayload,
  RiskProfessionCategory,
  RiskProfessionCategoryListResponse,
  RiskProfessionCategoryPayload,
  RiskFactorRulesResponse,
  RiskFactorRule,
  RiskProductCategory,
  RiskRuleVersion,
  RiskThresholdBand,
  RiskTransactionRange,
  ScreeningDetails,
  ScreeningStatus,
} from "@/types";
export {
  allowCustomerReOnboarding,
  listAdminCustomerOnboarding,
  revokeCustomerReOnboarding,
} from "@/api/OnboardingApi";
export type { AdminCustomerOnboarding } from "@/api/OnboardingApi";

function getAuthToken(): string {
  const token = sessionStorage.getItem("jwt_token");
  if (!token) {
    throw new Error("Missing authentication token.");
  }
  return token;
}

function authHeaders() {
  return {
    Authorization: `Bearer ${getAuthToken()}`,
  };
}

export async function getScreeningStatus(screeningId: number): Promise<ScreeningStatus> {
  const response = await api.get<ScreeningStatus>(`/api/v1/compliance/screenings/${screeningId}`, {
    headers: authHeaders(),
  });
  return response.data;
}

export async function getScreeningResults(screeningId: number): Promise<ScreeningDetails> {
  const response = await api.get<ScreeningDetails>(
    `/api/v1/compliance/screenings/${screeningId}/results`,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function retryScreening(screeningId: number): Promise<ScreeningStatus> {
  const response = await api.post<ScreeningStatus>(
    `/api/v1/compliance/screenings/${screeningId}/retry`,
    {},
    { headers: authHeaders() }
  );
  return response.data;
}

export async function listComplianceCases(): Promise<ComplianceCase[]> {
  const response = await api.get<{ items: ComplianceCase[] }>("/api/v1/compliance/cases", {
    headers: authHeaders(),
  });
  return response.data.items;
}

export async function getComplianceCase(caseId: number): Promise<ComplianceCaseDetail> {
  const response = await api.get<ComplianceCaseDetail>(`/api/v1/compliance/cases/${caseId}`, {
    headers: authHeaders(),
  });
  return response.data;
}

export async function approveComplianceCase(
  caseId: number,
  payload: { reason: string; notes?: string }
): Promise<ComplianceCaseDetail> {
  const response = await api.post<ComplianceCaseDetail>(
    `/api/v1/compliance/cases/${caseId}/approve`,
    payload,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function rejectComplianceCase(
  caseId: number,
  payload: { reason: string; notes?: string }
): Promise<ComplianceCaseDetail> {
  const response = await api.post<ComplianceCaseDetail>(
    `/api/v1/compliance/cases/${caseId}/reject`,
    payload,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function recalculateRiskAssessment(sessionId: number): Promise<CustomerRiskAssessment> {
  const response = await api.post<CustomerRiskAssessment>(
    `/api/v1/risk-assessment/${sessionId}/recalculate`,
    {},
    { headers: authHeaders() }
  );
  return response.data;
}

function categoryQuery(params?: { q?: string; is_active?: boolean }) {
  const query = new URLSearchParams();
  if (params?.q) {
    query.set("q", params.q);
  }
  if (typeof params?.is_active === "boolean") {
    query.set("is_active", String(params.is_active));
  }
  const queryString = query.toString();
  return queryString ? `?${queryString}` : "";
}

export async function listRiskBusinessCategories(params?: {
  q?: string;
  is_active?: boolean;
}): Promise<RiskBusinessCategoryListResponse> {
  const response = await api.get<RiskBusinessCategoryListResponse>(
    `/api/v1/risk-assessment/admin/business-categories${categoryQuery(params)}`,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function createRiskBusinessCategory(
  payload: RiskBusinessCategoryPayload
): Promise<RiskBusinessCategory> {
  const response = await api.post<RiskBusinessCategory>(
    "/api/v1/risk-assessment/admin/business-categories",
    payload,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function updateRiskBusinessCategory(
  categoryId: number,
  payload: Partial<RiskBusinessCategoryPayload> & { reason: string }
): Promise<RiskBusinessCategory> {
  const response = await api.put<RiskBusinessCategory>(
    `/api/v1/risk-assessment/admin/business-categories/${categoryId}`,
    payload,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function setRiskBusinessCategoryActive(
  categoryId: number,
  active: boolean,
  reason: string
): Promise<RiskBusinessCategory> {
  const response = await api.post<RiskBusinessCategory>(
    `/api/v1/risk-assessment/admin/business-categories/${categoryId}/${active ? "activate" : "deactivate"}`,
    { reason },
    { headers: authHeaders() }
  );
  return response.data;
}

export async function getRiskBusinessCategoryAudit(categoryId: number): Promise<AuditLogEntry[]> {
  const response = await api.get<AuditLogEntry[]>(
    `/api/v1/risk-assessment/admin/business-categories/${categoryId}/audit`,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function listRiskProfessionCategories(params?: {
  q?: string;
  is_active?: boolean;
}): Promise<RiskProfessionCategoryListResponse> {
  const response = await api.get<RiskProfessionCategoryListResponse>(
    `/api/v1/risk-assessment/admin/profession-categories${categoryQuery(params)}`,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function createRiskProfessionCategory(
  payload: RiskProfessionCategoryPayload
): Promise<RiskProfessionCategory> {
  const response = await api.post<RiskProfessionCategory>(
    "/api/v1/risk-assessment/admin/profession-categories",
    payload,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function updateRiskProfessionCategory(
  categoryId: number,
  payload: Partial<RiskProfessionCategoryPayload> & { reason: string }
): Promise<RiskProfessionCategory> {
  const response = await api.put<RiskProfessionCategory>(
    `/api/v1/risk-assessment/admin/profession-categories/${categoryId}`,
    payload,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function setRiskProfessionCategoryActive(
  categoryId: number,
  active: boolean,
  reason: string
): Promise<RiskProfessionCategory> {
  const response = await api.post<RiskProfessionCategory>(
    `/api/v1/risk-assessment/admin/profession-categories/${categoryId}/${active ? "activate" : "deactivate"}`,
    { reason },
    { headers: authHeaders() }
  );
  return response.data;
}

export async function getRiskProfessionCategoryAudit(categoryId: number): Promise<AuditLogEntry[]> {
  const response = await api.get<AuditLogEntry[]>(
    `/api/v1/risk-assessment/admin/profession-categories/${categoryId}/audit`,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function listRiskRuleVersions(): Promise<RiskRuleVersion[]> {
  const response = await api.get<{ items: RiskRuleVersion[] }>("/api/v1/risk-assessment/admin/rule-versions", {
    headers: authHeaders(),
  });
  return response.data.items;
}

export async function cloneRiskRuleVersion(payload: {
  version: string;
  change_notes: string;
}): Promise<RiskRuleVersion> {
  const response = await api.post<RiskRuleVersion>(
    "/api/v1/risk-assessment/admin/rule-versions/clone",
    payload,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function activateRiskRuleVersion(versionId: number, reason: string): Promise<RiskRuleVersion> {
  const response = await api.post<RiskRuleVersion>(
    `/api/v1/risk-assessment/admin/rule-versions/${versionId}/activate`,
    { reason },
    { headers: authHeaders() }
  );
  return response.data;
}

export async function listRiskFactorRules(versionId?: number): Promise<RiskFactorRulesResponse> {
  const query = versionId ? `?version_id=${versionId}` : "";
  const response = await api.get<RiskFactorRulesResponse>(
    `/api/v1/risk-assessment/admin/factor-rules${query}`,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function updateRiskFactorRule(
  ruleId: number,
  payload: Partial<RiskFactorRule> & { reason: string }
): Promise<RiskFactorRule> {
  const response = await api.put<RiskFactorRule>(
    `/api/v1/risk-assessment/admin/factor-rules/${ruleId}`,
    payload,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function listRiskThresholds(versionId?: number): Promise<RiskThresholdBand[]> {
  const query = versionId ? `?version_id=${versionId}` : "";
  const response = await api.get<RiskThresholdBand[]>(
    `/api/v1/risk-assessment/admin/thresholds${query}`,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function updateRiskThreshold(
  bandId: number,
  payload: Partial<RiskThresholdBand> & { reason: string }
): Promise<RiskThresholdBand> {
  const response = await api.put<RiskThresholdBand>(
    `/api/v1/risk-assessment/admin/thresholds/${bandId}`,
    payload,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function listRiskTransactionRanges(versionId?: number): Promise<RiskTransactionRange[]> {
  const query = versionId ? `?version_id=${versionId}` : "";
  const response = await api.get<RiskTransactionRange[]>(
    `/api/v1/risk-assessment/admin/transaction-ranges${query}`,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function updateRiskTransactionRange(
  rangeId: number,
  payload: Partial<RiskTransactionRange> & { reason: string }
): Promise<RiskTransactionRange> {
  const response = await api.put<RiskTransactionRange>(
    `/api/v1/risk-assessment/admin/transaction-ranges/${rangeId}`,
    payload,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function listRiskProductRisks(versionId?: number): Promise<RiskProductCategory[]> {
  const query = versionId ? `?version_id=${versionId}` : "";
  const response = await api.get<RiskProductCategory[]>(
    `/api/v1/risk-assessment/admin/product-risks${query}`,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function updateRiskProductRisk(
  productId: number,
  payload: Partial<RiskProductCategory> & { reason: string }
): Promise<RiskProductCategory> {
  const response = await api.put<RiskProductCategory>(
    `/api/v1/risk-assessment/admin/product-risks/${productId}`,
    payload,
    { headers: authHeaders() }
  );
  return response.data;
}
