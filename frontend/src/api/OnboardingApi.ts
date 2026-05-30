import api from "./ApiService";
import type {
  ComplianceSummary,
  CustomerIdentityFormPayload,
  CustomerIdentityFormResponse,
  CustomerIdentitySubmitResponse,
  FaceMatchCompletionContext,
  MatchResult,
  NIDCompletionContext,
  NIDExtractorResult,
  SignatureCompletionContext,
  StoredSignatureRecord,
} from "@/types";

export interface OnboardingStepResponse<T = unknown> {
  message: string;
  session: T;
}

export interface OnboardingSessionSummary {
  id: number;
  user_id: number;
  status: string;
  current_step: string;
  workflow_state: string;
  completed_steps: string[];
  next_required_step: string;
  draft_availability: Record<string, boolean>;
  document_references?: Record<string, { path: string; file_name?: string | null } | null>;
  risk_category?: string | null;
  activation_status: string;
  started_at: string;
  updated_at: string;
  last_resumed_at?: string | null;
  resume_count: number;
  completed_at?: string | null;
  compliance_summary?: ComplianceSummary | null;
  ocr_extraction?: {
    id: number;
    session_id: number;
    front_text: string;
    back_text?: string | null;
    merged_text: string;
    fields: Record<string, unknown>;
    front_detection: Record<string, unknown>;
    back_detection?: Record<string, unknown> | null;
    completed_at: string;
  } | null;
}

export type OnboardingSessionResponse = OnboardingStepResponse<OnboardingSessionSummary>;

export interface OnboardingSessionListResponse {
  items: OnboardingSessionSummary[];
}

export interface OnboardingEligibility {
  user_id: number;
  username: string;
  latest_session?: OnboardingSessionSummary | null;
  can_start_onboarding: boolean;
  can_resume_onboarding: boolean;
  re_onboarding_allowed: boolean;
  destination: "onboarding" | "customer_dashboard" | "rejected";
  message: string;
}

export interface AdminCustomerOnboarding {
  user_id: number;
  username: string;
  role: string;
  re_onboarding_allowed: boolean;
  re_onboarding_allowed_at?: string | null;
  re_onboarding_allowed_by?: number | null;
  re_onboarding_reason?: string | null;
  latest_session?: OnboardingSessionSummary | null;
}

interface IdentityFormSubmitOptions {
  nomineePhoto?: File | null;
}

let onboardingSessionBootstrapPromise: Promise<OnboardingSessionSummary> | null = null;

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

function appendJsonPayload(formData: FormData, key: string, payload: unknown): void {
  formData.append(key, JSON.stringify(payload));
}

export function getUploadUrl(path: string): string {
  const uploadPath = path.replace(/^storage\/uploads\//, "");
  const baseURL = String(api.defaults.baseURL ?? "").replace(/\/$/, "");
  return `${baseURL}/uploads/${uploadPath}`;
}

async function fetchAsFile(url: string, fileName: string): Promise<File> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch ${url}.`);
  }
  const blob = await response.blob();
  return new File([blob], fileName, { type: blob.type || "application/octet-stream" });
}

async function dataUrlToFile(dataUrl: string, fileName: string): Promise<File> {
  const response = await fetch(dataUrl);
  if (!response.ok) {
    throw new Error("Failed to read the generated image.");
  }
  const blob = await response.blob();
  return new File([blob], fileName, { type: blob.type || "image/png" });
}

export async function ensureOnboardingSession(): Promise<OnboardingSessionSummary> {
  const response = await api.post<OnboardingSessionResponse>(
    "/api/v1/onboarding/sessions/ensure",
    {},
    { headers: authHeaders() }
  );
  return response.data.session;
}

export async function getCurrentOnboardingSession(): Promise<OnboardingSessionSummary> {
  const response = await api.get<OnboardingSessionResponse>(
    "/api/v1/onboarding/session/current",
    { headers: authHeaders() }
  );
  return response.data.session;
}

export async function getOnboardingEligibility(): Promise<OnboardingEligibility> {
  const response = await api.get<OnboardingEligibility>(
    "/api/v1/onboarding/session/eligibility",
    { headers: authHeaders() }
  );
  return response.data;
}

export async function getOnboardingSessionStatus(sessionId: number): Promise<OnboardingSessionSummary> {
  const response = await api.get<OnboardingSessionResponse>(
    `/api/v1/onboarding/session/${sessionId}/status`,
    { headers: authHeaders() }
  );
  return response.data.session;
}

export async function resumeOnboardingSession(sessionId: number): Promise<OnboardingSessionSummary> {
  const response = await api.post<OnboardingSessionResponse>(
    `/api/v1/onboarding/session/${sessionId}/resume`,
    {},
    { headers: authHeaders() }
  );
  return response.data.session;
}

export async function loadOnboardingSession(): Promise<OnboardingSessionSummary> {
  if (onboardingSessionBootstrapPromise) {
    return onboardingSessionBootstrapPromise;
  }

  onboardingSessionBootstrapPromise = (async () => {
    try {
      const session = await ensureOnboardingSession();
      return await resumeOnboardingSession(session.id);
    } finally {
      onboardingSessionBootstrapPromise = null;
    }
  })();

  return onboardingSessionBootstrapPromise;
}

export async function listOnboardingSessions(): Promise<OnboardingSessionSummary[]> {
  const response = await api.get<OnboardingSessionListResponse>(
    "/api/v1/onboarding/sessions",
    { headers: authHeaders() }
  );
  return response.data.items;
}

export async function listAdminCustomerOnboarding(): Promise<AdminCustomerOnboarding[]> {
  const response = await api.get<{ items: AdminCustomerOnboarding[] }>(
    "/api/v1/onboarding/admin/customers",
    { headers: authHeaders() }
  );
  return response.data.items;
}

export async function allowCustomerReOnboarding(
  userId: number,
  payload: { reason: string; notes?: string }
): Promise<AdminCustomerOnboarding> {
  const response = await api.post<AdminCustomerOnboarding>(
    `/api/v1/onboarding/admin/customers/${userId}/re-onboarding/allow`,
    payload,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function revokeCustomerReOnboarding(
  userId: number,
  payload: { reason: string; notes?: string }
): Promise<AdminCustomerOnboarding> {
  const response = await api.post<AdminCustomerOnboarding>(
    `/api/v1/onboarding/admin/customers/${userId}/re-onboarding/revoke`,
    payload,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function submitFaceVerification(
  payload: {
    result: MatchResult;
    distance: number;
    threshold: number;
    error?: string;
    context: FaceMatchCompletionContext;
  },
  sessionId: number
): Promise<OnboardingSessionSummary> {
  const formData = new FormData();
  appendJsonPayload(formData, "payload", {
    result: payload.result,
    distance: payload.distance,
    threshold: payload.threshold,
    error_message: payload.error ?? null,
    metadata: {
      source: "frontend",
      quality: payload.context.quality ?? null,
      matchThreshold: payload.context.matchThreshold,
    },
  });

  const capturedFile = await dataUrlToFile(
    payload.context.capturedBase64,
    `captured-face-${Date.now()}.png`
  );
  formData.append("captured_image", capturedFile);

  try {
    const referenceFile = await fetchAsFile(
      payload.context.referenceImageSrc,
      `reference-face-${Date.now()}.png`
    );
    formData.append("reference_image", referenceFile);
  } catch {
    // Reference asset is optional on the backend and may be served from the frontend origin.
  }

  const response = await api.post<OnboardingSessionResponse>(
    `/api/v1/onboarding/sessions/${sessionId}/face-verification`,
    formData,
    { headers: authHeaders() }
  );
  return response.data.session;
}

export async function submitNIDExtraction(
  payload: {
    result: NIDExtractorResult;
    context: NIDCompletionContext;
  },
  sessionId: number
): Promise<OnboardingSessionSummary> {
  const formData = new FormData();
  appendJsonPayload(formData, "payload", payload.result);

  if (payload.context.frontFile) {
    formData.append("front_file", payload.context.frontFile);
  } else {
    throw new Error("Front NID file is required for backend persistence.");
  }

  if (payload.context.backFile) {
    formData.append("back_file", payload.context.backFile);
  }

  const response = await api.post<OnboardingSessionResponse>(
    `/api/v1/onboarding/sessions/${sessionId}/ocr-extraction`,
    formData,
    { headers: authHeaders() }
  );
  return response.data.session;
}

export async function getIdentityForm(sessionId: number): Promise<CustomerIdentityFormResponse> {
  const response = await api.get<CustomerIdentityFormResponse>(
    `/api/v1/onboarding/identity-form/${sessionId}`,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function saveIdentityFormDraft(
  sessionId: number,
  payload: CustomerIdentityFormPayload
): Promise<CustomerIdentityFormResponse> {
  const response = await api.post<CustomerIdentityFormResponse>(
    `/api/v1/onboarding/identity-form/${sessionId}/draft`,
    payload,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function autosaveIdentityForm(
  sessionId: number,
  payload: CustomerIdentityFormPayload
): Promise<CustomerIdentityFormResponse> {
  const response = await api.patch<CustomerIdentityFormResponse>(
    `/api/v1/onboarding/identity-form/${sessionId}/autosave`,
    payload,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function updateIdentityForm(
  sessionId: number,
  payload: CustomerIdentityFormPayload
): Promise<CustomerIdentityFormResponse> {
  const response = await api.put<CustomerIdentityFormResponse>(
    `/api/v1/onboarding/identity-form/${sessionId}`,
    payload,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function submitIdentityForm(
  sessionId: number,
  payload: CustomerIdentityFormPayload,
  options: IdentityFormSubmitOptions = {}
): Promise<CustomerIdentitySubmitResponse> {
  const formData = new FormData();
  appendJsonPayload(formData, "payload", payload);
  if (options.nomineePhoto) {
    formData.append("nominee_photo", options.nomineePhoto);
  }

  const response = await api.post<CustomerIdentitySubmitResponse>(
    `/api/v1/onboarding/identity-form/${sessionId}/submit`,
    formData,
    { headers: authHeaders() }
  );
  return response.data;
}

export async function submitSignatureCapture(
  payload: {
    record: StoredSignatureRecord;
    context: SignatureCompletionContext;
  },
  sessionId: number
): Promise<OnboardingSessionSummary> {
  const formData = new FormData();
  appendJsonPayload(formData, "payload", {
    ...payload.record,
    signerName: payload.context.signerName,
  });

  if (payload.context.signatureImage?.dataUrl) {
    const fileName = payload.context.signatureImage.fileName ?? `signature-${Date.now()}.png`;
    const signatureFile = await dataUrlToFile(payload.context.signatureImage.dataUrl, fileName);
    formData.append("signature_file", signatureFile);
  }

  const response = await api.post<OnboardingSessionResponse>(
    `/api/v1/onboarding/sessions/${sessionId}/signature`,
    formData,
    { headers: authHeaders() }
  );
  return response.data.session;
}
