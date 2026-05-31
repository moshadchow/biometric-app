import React from "react";
import {
  autosaveIdentityForm,
  getIdentityForm,
  getUploadUrl,
  saveIdentityFormDraft,
  submitIdentityForm,
  type OnboardingSessionSummary,
} from "@/api/OnboardingApi";
import { getRiskAssessmentOptions } from "@/api/ComplianceApi";
import type {
  CustomerAddressPayload,
  CustomerIdentityFormPayload,
  CustomerIdentityFormResponse,
  RiskAssessmentOptions,
  RiskOption,
} from "@/types";

interface CustomerIdentityFormProps {
  sessionId: number | null;
  onSubmitted?: (session: OnboardingSessionSummary) => void;
}

type SaveStatus = "idle" | "loading" | "saving" | "saved" | "error";

const emptyAddress: CustomerAddressPayload = {
  address_line: "",
  city: "",
  district: "",
  postal_code: "",
};

const emptyPayload: CustomerIdentityFormPayload = {
  applicant_name: "",
  account_number: "",
  unique_account_number: "",
  nid_number: "",
  father_name: "",
  mother_name: "",
  spouse_name: "",
  date_of_birth: "",
  gender: "",
  profession: "",
  product_type: "",
  business_category: "",
  residency_status: "",
  onboarding_channel: "",
  mobile_number: "",
  monthly_income: "",
  nationality: "",
  source_of_funds: "",
  tin: "",
  expected_transaction_range: "",
  expected_transaction_pattern: "",
  existing_customer_review: "",
  additional_documents_obtained: "",
  additional_remarks: "",
  beneficial_owner_different: false,
  beneficial_owner_name: "",
  beneficial_owner_nationality: "",
  beneficial_owner_identification_number: "",
  beneficial_owner_relationship: "",
  present_address: { ...emptyAddress },
  permanent_address: { ...emptyAddress },
  nominee: {
    nominee_name: "",
    relationship: "",
  },
  metadata: {},
};

function responseToPayload(response: CustomerIdentityFormResponse): CustomerIdentityFormPayload {
  const profile = response.profile;
  return {
    ...emptyPayload,
    applicant_name: profile.applicant_name ?? "",
    account_number: profile.account_number ?? "",
    unique_account_number: profile.unique_account_number ?? "",
    nid_number: profile.nid_number ?? "",
    father_name: profile.father_name ?? "",
    mother_name: profile.mother_name ?? "",
    spouse_name: profile.spouse_name ?? "",
    date_of_birth: profile.date_of_birth ?? "",
    gender: profile.gender ?? "",
    profession: profile.profession ?? "",
    product_type: profile.product_type ?? "",
    business_category: profile.business_category ?? "",
    residency_status: profile.residency_status ?? "",
    onboarding_channel: profile.onboarding_channel ?? "",
    mobile_number: profile.mobile_number ?? "",
    monthly_income: profile.monthly_income ?? "",
    nationality: profile.nationality ?? "",
    source_of_funds: profile.source_of_funds ?? "",
    tin: profile.tin ?? "",
    expected_transaction_range: profile.expected_transaction_range ?? "",
    expected_transaction_pattern: profile.expected_transaction_pattern ?? "",
    existing_customer_review: profile.existing_customer_review ?? "",
    additional_documents_obtained: profile.additional_documents_obtained ?? "",
    additional_remarks: profile.additional_remarks ?? "",
    beneficial_owner_different: profile.beneficial_owner_different,
    beneficial_owner_name: profile.beneficial_owner_name ?? "",
    beneficial_owner_nationality: profile.beneficial_owner_nationality ?? "",
    beneficial_owner_identification_number: profile.beneficial_owner_identification_number ?? "",
    beneficial_owner_relationship: profile.beneficial_owner_relationship ?? "",
    present_address: {
      ...emptyAddress,
      ...(response.addresses.present ?? {}),
    },
    permanent_address: {
      ...emptyAddress,
      ...(response.addresses.permanent ?? {}),
    },
    nominee: {
      nominee_name: response.nominee?.nominee_name ?? "",
      relationship: response.nominee?.relationship ?? "",
    },
    metadata: {},
  };
}

function validate(payload: CustomerIdentityFormPayload, formType: string): string[] {
  const missing: string[] = [];
  const required: Array<[string, string | null | undefined]> = [
    ["Applicant name", payload.applicant_name],
    ["Date of birth", payload.date_of_birth],
    ["Mobile number", payload.mobile_number],
    ["Present address", payload.present_address.address_line],
    ["Permanent address", payload.permanent_address.address_line],
    ["Profession", payload.profession],
    ["Product type", payload.product_type],
    ["Business category", payload.business_category],
    ["Residency status", payload.residency_status],
    ["Source of funds", payload.source_of_funds],
    ["Expected annual transaction volume", payload.expected_transaction_range],
    ["Onboarding channel", payload.onboarding_channel],
  ];
  if (formType === "regular") {
    required.push(["Monthly income", payload.monthly_income]);
  }
  if (payload.beneficial_owner_different) {
    required.push(
      ["Beneficial owner name", payload.beneficial_owner_name],
      ["Beneficial owner identification number", payload.beneficial_owner_identification_number]
    );
  }
  for (const [label, value] of required) {
    if (!String(value ?? "").trim()) {
      missing.push(label);
    }
  }
  return missing;
}

function missingRiskOptionLists(options: RiskAssessmentOptions | null): string[] {
  if (!options) return ["risk configuration"];
  const missing: string[] = [];
  if (options.source_of_funds.length === 0) missing.push("Source of Funds");
  if (options.expected_transaction_ranges.length === 0) missing.push("Expected Annual Transaction Volume");
  if (options.onboarding_channels.length === 0) missing.push("Onboarding Channel");
  return missing;
}

function describeSubmitError(error: unknown): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const message = typeof (detail as { message?: unknown }).message === "string"
      ? String((detail as { message?: unknown }).message)
      : null;
    const missingFields = Array.isArray((detail as { missing_fields?: unknown }).missing_fields)
      ? ((detail as { missing_fields?: string[] }).missing_fields ?? [])
      : [];
    const effectiveFormType = typeof (detail as { effective_form_type?: unknown }).effective_form_type === "string"
      ? String((detail as { effective_form_type?: string }).effective_form_type)
      : null;
    const effectiveRiskCategory = typeof (detail as { effective_risk_category?: unknown }).effective_risk_category === "string"
      ? String((detail as { effective_risk_category?: string }).effective_risk_category)
      : null;

    if (effectiveFormType === "regular" && missingFields.length > 0) {
      return `Risk increased to ${effectiveRiskCategory ?? "MEDIUM"}, so Regular e-KYC is required. Complete: ${missingFields.join(", ")}.`;
    }
    if (message) {
      return message;
    }
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return String(error);
}

const CustomerIdentityForm: React.FC<CustomerIdentityFormProps> = ({ sessionId, onSubmitted }) => {
  const [payload, setPayload] = React.useState<CustomerIdentityFormPayload>(emptyPayload);
  const [formResponse, setFormResponse] = React.useState<CustomerIdentityFormResponse | null>(null);
  const [status, setStatus] = React.useState<SaveStatus>("idle");
  const [message, setMessage] = React.useState("");
  const [error, setError] = React.useState("");
  const [dirty, setDirty] = React.useState(false);
  const [nomineePhoto, setNomineePhoto] = React.useState<File | null>(null);
  const [riskOptions, setRiskOptions] = React.useState<RiskAssessmentOptions | null>(null);

  React.useEffect(() => {
    if (!sessionId) return undefined;
    let cancelled = false;
    setStatus("loading");
    void (async () => {
      try {
        const [response, options] = await Promise.all([
          getIdentityForm(sessionId),
          getRiskAssessmentOptions(),
        ]);
        if (cancelled) return;
        setFormResponse(response);
        setRiskOptions(options);
        setPayload(responseToPayload(response));
        setDirty(false);
        setError("");
        setMessage("Identity form restored from backend.");
        setStatus("idle");
      } catch (loadError) {
        if (cancelled) return;
        setError(loadError instanceof Error ? loadError.message : String(loadError));
        setStatus("error");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  React.useEffect(() => {
    if (!sessionId || !dirty || status === "loading") return undefined;
    const timer = window.setInterval(() => {
      void (async () => {
        try {
          await autosaveIdentityForm(sessionId, payload);
          setMessage("Draft autosaved.");
          setError("");
          setDirty(false);
        } catch {
          setError("Autosave failed. Use Save Draft before leaving this step.");
        }
      })();
    }, 30000);
    return () => window.clearInterval(timer);
  }, [dirty, payload, sessionId, status]);

  const formType = formResponse?.profile.form_type ?? "simplified";
  const riskCategory = formResponse?.profile.risk_category ?? "LOW";
  const options = riskOptions ?? {
    professions: [],
    business_categories: [],
    product_types: [],
    nationalities: [],
    residency_statuses: [],
    source_of_funds: [],
    expected_transaction_ranges: [],
    beneficial_ownership: [],
    onboarding_channels: [],
  };

  const setField = (key: keyof CustomerIdentityFormPayload, value: string | boolean) => {
    setPayload((current) => ({ ...current, [key]: value }));
    setDirty(true);
  };

  const setAddressField = (
    addressKey: "present_address" | "permanent_address",
    field: keyof CustomerAddressPayload,
    value: string
  ) => {
    setPayload((current) => ({
      ...current,
      [addressKey]: {
        ...current[addressKey],
        [field]: value,
      },
    }));
    setDirty(true);
  };

  const setNomineeField = (field: "nominee_name" | "relationship", value: string) => {
    setPayload((current) => ({
      ...current,
      nominee: {
        ...current.nominee,
        [field]: value,
      },
    }));
    setDirty(true);
  };

  const handleSaveDraft = async () => {
    if (!sessionId) return;
    setStatus("saving");
    try {
      const response = await saveIdentityFormDraft(sessionId, payload);
      setFormResponse(response);
      setDirty(false);
      setMessage("Draft saved.");
      setError("");
      setStatus("saved");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : String(saveError));
      setStatus("error");
    }
  };

  const handleSubmit = async () => {
    if (!sessionId) return;
    const missingOptions = missingRiskOptionLists(riskOptions);
    if (missingOptions.length > 0) {
      setError(`Risk configuration is missing options for: ${missingOptions.join(", ")}.`);
      return;
    }
    const missing = validate(payload, formType);
    if (missing.length > 0) {
      setError(`Complete required fields: ${missing.join(", ")}.`);
      return;
    }
    setStatus("saving");
    try {
      const response = await submitIdentityForm(sessionId, payload, { nomineePhoto });
      setFormResponse(response.form);
      setDirty(false);
      setMessage("Identity form submitted.");
      setError("");
      setStatus("saved");
      onSubmitted?.(response.session as OnboardingSessionSummary);
    } catch (submitError) {
      setError(describeSubmitError(submitError));
      setStatus("error");
    }
  };

  if (!sessionId) {
    return <div style={s.root}>Loading onboarding session...</div>;
  }

  return (
    <div style={s.root}>
      <div style={s.header}>
        <div>
          <div style={s.kicker}>{formType === "regular" ? "Regular e-KYC" : "Simplified e-KYC"}</div>
          <h1 style={s.title}>Customer Identity Form</h1>
          <div style={s.subtitle}>
            Risk category {riskCategory}. OCR values are editable and corrections are audited.
          </div>
        </div>
        <div style={s.statusBadge}>{formResponse?.profile.status ?? status}</div>
      </div>

      <section style={s.panel}>
        <div style={s.sectionTitle}>Personal Information</div>
        <div style={s.grid}>
          <Input label="Applicant Name" value={payload.applicant_name} onChange={(value) => setField("applicant_name", value)} required />
          {formType === "regular" && (
            <>
              <Input label="Account Number" value={payload.account_number} onChange={(value) => setField("account_number", value)} />
              <Input label="Unique Account Number" value={payload.unique_account_number} onChange={(value) => setField("unique_account_number", value)} />
            </>
          )}
          <Input label="NID Number" value={payload.nid_number} onChange={(value) => setField("nid_number", value)} />
          <Input label="Date of Birth" value={payload.date_of_birth} onChange={(value) => setField("date_of_birth", value)} required />
          <Input label="Gender" value={payload.gender} onChange={(value) => setField("gender", value)} />
          <Input label="Father's Name" value={payload.father_name} onChange={(value) => setField("father_name", value)} />
          <Input label="Mother's Name" value={payload.mother_name} onChange={(value) => setField("mother_name", value)} />
          <Input label="Spouse Name" value={payload.spouse_name} onChange={(value) => setField("spouse_name", value)} />
          <Input label="Mobile Number" value={payload.mobile_number} onChange={(value) => setField("mobile_number", value)} required />
        </div>
      </section>

      <section style={s.panel}>
        <div style={s.sectionTitle}>{formType === "regular" ? "Financial and Contact Information" : "Additional Information"}</div>
        <div style={s.grid}>
          <SelectInput label="Profession" value={payload.profession} options={options.professions} onChange={(value) => setField("profession", value)} required />
          <SelectInput label="Product Type" value={payload.product_type} options={options.product_types} onChange={(value) => setField("product_type", value)} required />
          <SelectInput label="Business Category" value={payload.business_category} options={options.business_categories} onChange={(value) => setField("business_category", value)} required />
          <SelectInput label="Residency Status" value={payload.residency_status} options={options.residency_statuses} onChange={(value) => setField("residency_status", value)} required />
          <SelectInput label="Source of Funds" value={payload.source_of_funds} options={options.source_of_funds} onChange={(value) => setField("source_of_funds", value)} required />
          <SelectInput label="Expected Annual Transaction Volume" value={payload.expected_transaction_range} options={options.expected_transaction_ranges} onChange={(value) => setField("expected_transaction_range", value)} required />
          <SelectInput label="Onboarding Channel" value={payload.onboarding_channel} options={options.onboarding_channels} onChange={(value) => setField("onboarding_channel", value)} required />
          {formType === "regular" ? (
            <>
              <Input label="Monthly Income" value={payload.monthly_income} onChange={(value) => setField("monthly_income", value)} required />
              <Input label="TIN" value={payload.tin} onChange={(value) => setField("tin", value)} />
              <Input label="Additional Documents Obtained" value={payload.additional_documents_obtained} onChange={(value) => setField("additional_documents_obtained", value)} />
            </>
          ) : null}
        </div>
      </section>

      <section style={s.twoColumn}>
        <AddressPanel
          title="Present Address"
          value={payload.present_address}
          required
          onChange={(field, value) => setAddressField("present_address", field, value)}
        />
        <AddressPanel
          title="Permanent Address"
          value={payload.permanent_address}
          required
          onChange={(field, value) => setAddressField("permanent_address", field, value)}
        />
      </section>

      <section style={s.panel}>
        <div style={s.sectionTitle}>Nominee Information</div>
        <div style={s.grid}>
          <Input label="Nominee Name" value={payload.nominee.nominee_name} onChange={(value) => setNomineeField("nominee_name", value)} />
          <Input label="Relationship" value={payload.nominee.relationship} onChange={(value) => setNomineeField("relationship", value)} />
          {formType === "regular" && (
            <label style={s.fileBox}>
              <input
                type="file"
                accept=".png,.jpg,.jpeg,image/png,image/jpeg"
                onChange={(event) => setNomineePhoto(event.target.files?.[0] ?? null)}
                style={s.hiddenInput}
              />
              <span style={s.fileTitle}>Nominee photograph</span>
              <span style={s.fileHint}>{nomineePhoto?.name ?? formResponse?.nominee?.photograph_file_name ?? "PNG or JPG"}</span>
            </label>
          )}
        </div>
      </section>

      {formType === "regular" && (
        <section style={s.panel}>
          <div style={s.sectionTitle}>Beneficial Ownership</div>
          <label style={s.checkboxRow}>
            <input
              type="checkbox"
              checked={payload.beneficial_owner_different}
              onChange={(event) => setField("beneficial_owner_different", event.target.checked)}
            />
            <span>Beneficial owner is different from customer</span>
          </label>
          {payload.beneficial_owner_different && (
            <div style={s.grid}>
              <Input label="Beneficial Owner Name" value={payload.beneficial_owner_name} onChange={(value) => setField("beneficial_owner_name", value)} />
              <Input label="Nationality" value={payload.beneficial_owner_nationality} onChange={(value) => setField("beneficial_owner_nationality", value)} />
              <Input label="Identification Number" value={payload.beneficial_owner_identification_number} onChange={(value) => setField("beneficial_owner_identification_number", value)} />
              <Input label="Relationship To Customer" value={payload.beneficial_owner_relationship} onChange={(value) => setField("beneficial_owner_relationship", value)} />
            </div>
          )}
        </section>
      )}

      <section style={s.panel}>
        <div style={s.sectionTitle}>Document References</div>
        <div style={s.documentGrid}>
          {Object.entries(formResponse?.document_references ?? {}).map(([key, reference]) => (
            <div key={key} style={s.documentItem}>
              {reference?.path && (
                <img
                  src={getUploadUrl(reference.path)}
                  alt={key.replace(/_/g, " ")}
                  style={s.documentImage}
                />
              )}
              <span style={s.documentLabel}>{key.replace(/_/g, " ")}</span>
              <span style={s.documentValue}>{reference?.file_name ?? "Not available"}</span>
            </div>
          ))}
        </div>
      </section>

      <section style={s.panel}>
        <div style={s.sectionTitle}>Remarks</div>
        <textarea
          value={payload.additional_remarks ?? ""}
          onChange={(event) => setField("additional_remarks", event.target.value)}
          style={s.textarea}
          rows={4}
        />
      </section>

      {error && <div style={s.errorBanner}>{error}</div>}
      {message && !error && <div style={s.successBanner}>{message}</div>}

      <div style={s.actions}>
        <button type="button" style={s.secondaryButton} onClick={handleSaveDraft} disabled={status === "saving"}>
          Save Draft
        </button>
        <button type="button" style={s.primaryButton} onClick={handleSubmit} disabled={status === "saving"}>
          {status === "saving" ? "Saving..." : "Submit Identity Form"}
        </button>
      </div>
    </div>
  );
};

const Input: React.FC<{
  label: string;
  value?: string | null;
  required?: boolean;
  onChange: (value: string) => void;
}> = ({ label, value, required, onChange }) => (
  <label style={s.field}>
    <span style={s.label}>{label}{required ? " *" : ""}</span>
    <input value={value ?? ""} onChange={(event) => onChange(event.target.value)} style={s.input} />
  </label>
);

const SelectInput: React.FC<{
  label: string;
  value?: string | null;
  options: RiskOption[];
  required?: boolean;
  onChange: (value: string) => void;
}> = ({ label, value, options, required, onChange }) => {
  const currentValue = value ?? "";
  const hasCurrent = !currentValue || options.some((option) => option.value === currentValue);
  return (
    <label style={s.field}>
      <span style={s.label}>{label}{required ? " *" : ""}</span>
      <select value={currentValue} onChange={(event) => onChange(event.target.value)} style={s.input}>
        <option value="">Select</option>
        {!hasCurrent && <option value={currentValue}>{currentValue}</option>}
        {options.map((option) => (
          <option key={`${option.source}:${option.value}`} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
};

const AddressPanel: React.FC<{
  title: string;
  value: CustomerAddressPayload;
  required?: boolean;
  onChange: (field: keyof CustomerAddressPayload, value: string) => void;
}> = ({ title, value, required, onChange }) => (
  <section style={s.panel}>
    <div style={s.sectionTitle}>{title}</div>
    <div style={s.grid}>
      <Input label="Address Line" value={value.address_line} required={required} onChange={(next) => onChange("address_line", next)} />
      <Input label="City" value={value.city} onChange={(next) => onChange("city", next)} />
      <Input label="District" value={value.district} onChange={(next) => onChange("district", next)} />
      <Input label="Postal Code" value={value.postal_code} onChange={(next) => onChange("postal_code", next)} />
    </div>
  </section>
);

const s: Record<string, React.CSSProperties> = {
  root: {
    fontFamily: "'DM Mono','Fira Code','Cascadia Code',monospace",
    background: "#0a0a0a",
    color: "#ececec",
    border: "1px solid #212121",
    borderRadius: 18,
    padding: "2rem 1.5rem",
    display: "grid",
    gap: 16,
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    gap: 16,
    alignItems: "flex-start",
    flexWrap: "wrap",
  },
  kicker: {
    color: "#00e5a0",
    fontSize: 12,
    fontWeight: 800,
    textTransform: "uppercase",
  },
  title: {
    margin: "0.25rem 0",
    fontSize: 22,
    color: "#fff",
  },
  subtitle: {
    color: "#9a9a9a",
    fontSize: 12,
    lineHeight: 1.6,
  },
  statusBadge: {
    borderRadius: 999,
    border: "1px solid #2b2b2b",
    background: "#111",
    color: "#38b6ff",
    padding: "6px 12px",
    fontSize: 11,
    fontWeight: 800,
  },
  panel: {
    borderRadius: 14,
    border: "1px solid #1f1f1f",
    background: "#0d0d0d",
    padding: 16,
  },
  sectionTitle: {
    color: "#7d7d7d",
    fontSize: 11,
    fontWeight: 800,
    letterSpacing: "0.7px",
    textTransform: "uppercase",
    marginBottom: 12,
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
    gap: 12,
  },
  twoColumn: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
    gap: 16,
  },
  field: {
    display: "grid",
    gap: 7,
  },
  label: {
    color: "#8d8d8d",
    fontSize: 11,
  },
  input: {
    borderRadius: 10,
    border: "1px solid #2a2a2a",
    background: "#111",
    color: "#f0f0f0",
    padding: "11px 12px",
    fontFamily: "inherit",
    fontSize: 13,
    minWidth: 0,
  },
  textarea: {
    width: "100%",
    boxSizing: "border-box",
    borderRadius: 10,
    border: "1px solid #2a2a2a",
    background: "#111",
    color: "#f0f0f0",
    padding: 12,
    fontFamily: "inherit",
    fontSize: 13,
    resize: "vertical",
  },
  checkboxRow: {
    display: "flex",
    gap: 10,
    alignItems: "center",
    color: "#d8d8d8",
    fontSize: 13,
    marginBottom: 14,
  },
  fileBox: {
    borderRadius: 12,
    border: "1px dashed #2c2c2c",
    background: "#101010",
    padding: 14,
    display: "grid",
    gap: 6,
    cursor: "pointer",
  },
  hiddenInput: {
    display: "none",
  },
  fileTitle: {
    color: "#fff",
    fontSize: 13,
    fontWeight: 800,
  },
  fileHint: {
    color: "#8d8d8d",
    fontSize: 12,
  },
  documentGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
    gap: 10,
  },
  documentItem: {
    borderRadius: 10,
    border: "1px solid #202020",
    background: "#101010",
    padding: 12,
    display: "grid",
    gap: 6,
  },
  documentImage: {
    width: "100%",
    aspectRatio: "16 / 10",
    objectFit: "cover",
    borderRadius: 8,
    border: "1px solid #242424",
    background: "#080808",
  },
  documentLabel: {
    color: "#777",
    fontSize: 10,
    textTransform: "uppercase",
  },
  documentValue: {
    color: "#ededed",
    fontSize: 12,
    wordBreak: "break-word",
  },
  successBanner: {
    borderRadius: 12,
    border: "1px solid #146c47",
    background: "#0f2e22",
    color: "#00e5a0",
    padding: "12px 14px",
    fontSize: 12,
  },
  errorBanner: {
    borderRadius: 12,
    border: "1px solid #7f1d1d",
    background: "#351010",
    color: "#ffb3b3",
    padding: "12px 14px",
    fontSize: 12,
  },
  actions: {
    display: "flex",
    gap: 12,
    justifyContent: "flex-end",
    flexWrap: "wrap",
  },
  primaryButton: {
    background: "#00e5a0",
    color: "#06120d",
    border: "none",
    borderRadius: 8,
    padding: "11px 16px",
    fontFamily: "inherit",
    fontSize: 12,
    fontWeight: 800,
    cursor: "pointer",
  },
  secondaryButton: {
    background: "transparent",
    color: "#d6d6d6",
    border: "1px solid #2a2a2a",
    borderRadius: 8,
    padding: "11px 16px",
    fontFamily: "inherit",
    fontSize: 12,
    fontWeight: 800,
    cursor: "pointer",
  },
};

export default CustomerIdentityForm;
