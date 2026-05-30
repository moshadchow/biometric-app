# 02 - Customer Identity Form

## Overview

This document defines the requirements for the Customer Identity Form module within the onboarding workflow.

The Customer Identity Form is introduced as a new onboarding step immediately after OCR Extraction and before Signature Capture.

The primary responsibility of this module is customer information collection, review, and validation.

Risk assessment, risk scoring, EDD determination, and compliance decisions are handled separately by the Risk Assessment Engine.

---

# Objectives

The Customer Identity Form shall:

* Capture customer profile information.
* Pre-populate fields using OCR extraction results.
* Support Simplified e-KYC and Regular e-KYC journeys.
* Allow customer review and correction of OCR-extracted data.
* Persist customer profile information.
* Integrate with onboarding workflow orchestration.

---

# Updated Onboarding Flow

1. Face Verification
2. OCR Extraction
3. Customer Identity Form
4. Signature Capture
5. Compliance Screening & Risk Review
6. Onboarding Completion

---

# Form Selection Logic

The form type shall be determined by the Risk Assessment Engine.

| Risk Category | Form Type        |
| ------------- | ---------------- |
| LOW           | Simplified e-KYC |
| MEDIUM        | Regular e-KYC    |
| HIGH          | Regular e-KYC    |

Customers cannot manually switch between forms.

---

# OCR Integration

The form shall automatically populate available OCR data.

## Auto-Populated Fields

* Applicant Name
* Date of Birth
* Gender
* NID Number
* Father's Name
* Mother's Name
* Present Address
* Permanent Address

Users may:

* Edit OCR values
* Correct extraction errors
* Complete missing fields

All changes shall be audited.

---

# Simplified e-KYC Form

Applicable for LOW Risk customers.

## Personal Information

* Applicant Name
* Mother's Name
* Father's Name
* Spouse Name
* Date of Birth
* Gender
* Profession
* Mobile Number

## Address Information

### Present Address

* Address Line
* City
* District
* Postal Code

### Permanent Address

* Address Line
* City
* District
* Postal Code

## Nominee Information

* Nominee Name
* Relationship

## Document References

Display:

* Customer Photo
* Secondary Photo
* NID Front
* NID Back

Documents originate from previous onboarding steps.

No re-upload required.

## Additional Information

* Existing Customer Review Notes
* Expected Transaction Range
* Additional Remarks

---

# Regular e-KYC Form

Applicable for MEDIUM and HIGH Risk customers.

## Personal Information

* Applicant Name
* Account Number
* Unique Account Number
* Mother's Name
* Father's Name
* Spouse Name
* Date of Birth
* Gender

## Financial Information

* Profession
* Monthly Income
* Nationality
* Source of Funds
* TIN (Optional)

## Contact Information

* Mobile Number

## Address Information

* Present Address
* Permanent Address

## Nominee Information

* Nominee Name
* Relationship
* Nominee Photograph

## Beneficial Ownership

* Is Beneficial Owner Different From Customer?
* Beneficial Owner Name
* Beneficial Owner Nationality
* Beneficial Owner Identification Number
* Relationship To Customer

## Additional Information

* Existing Customer Review
* Expected Transaction Pattern
* Additional Documents Obtained
* Additional Remarks

---

# Workflow States

The Customer Identity Form module shall support:

```text
IDENTITY_FORM_PENDING
IDENTITY_FORM_IN_PROGRESS
IDENTITY_FORM_DRAFT_SAVED
IDENTITY_FORM_COMPLETED
```

---

# Auto Save Requirements

The system shall automatically:

* Save draft every 30 seconds.
* Save draft on critical field updates.
* Restore draft after login/session recovery.

---

# API Requirements

## Retrieve Form

GET /api/v1/onboarding/identity-form/{session_id}

## Save Draft

POST /api/v1/onboarding/identity-form/{session_id}/draft

## Auto Save

PATCH /api/v1/onboarding/identity-form/{session_id}/autosave

## Update Form

PUT /api/v1/onboarding/identity-form/{session_id}

## Submit Form

POST /api/v1/onboarding/identity-form/{session_id}/submit

---

# Database Design

## customer_identity_profiles

Stores:

* Personal Information
* Contact Information
* Address Information
* OCR Corrections
* Nominee Information
* Beneficial Ownership Information

## customer_addresses

Stores:

* Present Address
* Permanent Address

## customer_nominees

Stores:

* Nominee Details

---

# Validation Rules

## Common

Required:

* Applicant Name
* Date of Birth
* Mobile Number
* Present Address
* Permanent Address

## Regular e-KYC

Additional Required:

* Source Of Funds
* Nationality
* Monthly Income

---

# Audit Requirements

Audit:

* OCR Data Corrections
* Draft Saves
* Form Updates
* Submission Events

---

# Success Criteria

The module is complete when:

* OCR data is pre-populated.
* Customers can edit OCR values.
* Simplified and Regular e-KYC forms render correctly.
* Form drafts are recoverable.
* Customer data is persisted successfully.
* Signature Capture becomes the next onboarding step.
