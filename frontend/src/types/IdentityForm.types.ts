export type IdentityFormType = "simplified" | "regular";

export type IdentityFormStatus =
  | "IDENTITY_FORM_PENDING"
  | "IDENTITY_FORM_IN_PROGRESS"
  | "IDENTITY_FORM_DRAFT_SAVED"
  | "IDENTITY_FORM_COMPLETED";

export interface CustomerAddressPayload {
  address_line?: string | null;
  city?: string | null;
  district?: string | null;
  postal_code?: string | null;
}

export interface CustomerNomineePayload {
  nominee_name?: string | null;
  relationship?: string | null;
}

export interface CustomerIdentityFormPayload {
  applicant_name?: string | null;
  account_number?: string | null;
  unique_account_number?: string | null;
  nid_number?: string | null;
  father_name?: string | null;
  mother_name?: string | null;
  spouse_name?: string | null;
  date_of_birth?: string | null;
  gender?: string | null;
  profession?: string | null;
  product_type?: string | null;
  business_category?: string | null;
  residency_status?: string | null;
  onboarding_channel?: string | null;
  mobile_number?: string | null;
  monthly_income?: string | null;
  nationality?: string | null;
  source_of_funds?: string | null;
  tin?: string | null;
  expected_transaction_range?: string | null;
  expected_transaction_pattern?: string | null;
  existing_customer_review?: string | null;
  additional_documents_obtained?: string | null;
  additional_remarks?: string | null;
  beneficial_owner_different: boolean;
  beneficial_owner_name?: string | null;
  beneficial_owner_nationality?: string | null;
  beneficial_owner_identification_number?: string | null;
  beneficial_owner_relationship?: string | null;
  present_address: CustomerAddressPayload;
  permanent_address: CustomerAddressPayload;
  nominee: CustomerNomineePayload;
  metadata?: Record<string, unknown>;
}

export interface CustomerIdentityProfile extends CustomerIdentityFormPayload {
  id: number;
  session_id: number;
  form_type: IdentityFormType;
  risk_category: "LOW" | "MEDIUM" | "HIGH";
  status: IdentityFormStatus;
  ocr_snapshot: Record<string, unknown>;
  ocr_corrections: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  submitted_at?: string | null;
}

export interface CustomerAddress extends CustomerAddressPayload {
  id?: number | null;
  address_type: "present" | "permanent";
}

export interface CustomerNominee extends CustomerNomineePayload {
  id?: number | null;
  photograph_file_path?: string | null;
  photograph_file_name?: string | null;
  metadata?: Record<string, unknown>;
}

export interface IdentityDocumentReference {
  path: string;
  file_name?: string | null;
}

export interface CustomerIdentityFormResponse {
  profile: CustomerIdentityProfile;
  addresses: {
    present?: CustomerAddress | null;
    permanent?: CustomerAddress | null;
  };
  nominee?: CustomerNominee | null;
  document_references: Record<string, IdentityDocumentReference | null>;
  session?: unknown;
}

export interface CustomerIdentitySubmitResponse {
  message: string;
  form: CustomerIdentityFormResponse;
  session: unknown;
}
