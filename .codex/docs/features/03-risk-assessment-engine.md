# 03 - Risk Assessment Engine

## Overview

This document defines the Customer Risk Assessment Engine responsible for:

* Risk Scoring
* Risk Categorization
* EDD Determination
* Compliance Risk Evaluation
* Risk-Based e-KYC Routing

The engine shall operate independently from the Customer Identity Form module.

---

# Objectives

The Risk Assessment Engine shall:

* Calculate customer risk scores.
* Classify customers into LOW, MEDIUM, or HIGH risk categories.
* Trigger Enhanced Due Diligence (EDD).
* Integrate with sanctions, PEP, adverse media, and IP screening.
* Provide auditable risk decisions.

---

# Assessment Lifecycle

## Preliminary Assessment

Executed after:

* OCR Extraction
* Screening Initiation

Purpose:

* Determine initial onboarding path.
* Select Simplified or Regular e-KYC.

## Final Assessment

Executed after:

* Customer Identity Form Completion
* Screening Completion

Purpose:

* Calculate final risk score.
* Determine onboarding approval path.

---

# Risk Categories

| Total Score | Risk Category |
| ----------- | ------------- |
| 0 - 9       | LOW           |
| 10 - 14     | MEDIUM        |
| >= 15       | HIGH          |

Thresholds must be configurable.

---

# Risk Factors

## 1. Type of Onboarding

| Type                        | Score |
| --------------------------- | ----- |
| Branch / RM                 | 2     |
| Direct Sales Agent          | 2     |
| Walk-In                     | 3     |
| Internet / Non Face-To-Face | 2     |

---

## 2. Geographic Risk

| Classification           | Score |
| ------------------------ | ----- |
| Resident Bangladeshi     | 1     |
| Non-Resident Bangladeshi | 3     |

---

## 3. Customer Type Risk

### PEP

| Status | Score |
| ------ | ----- |
| No     | 0     |
| Yes    | 5     |

### PEP Associate

| Status | Score |
| ------ | ----- |
| No     | 0     |
| Yes    | 5     |

### Influential Person (IP)

| Status | Score |
| ------ | ----- |
| No     | 1     |
| Yes    | 5     |

Values must come from compliance screening.

Customers cannot edit these values.

---

## 4. Product Risk

| Product               | Score |
| --------------------- | ----- |
| Individual BO Account | 2     |

---

## 5. Business & Activity Risk

Business and Profession scores shall follow the approved Capital Market Intermediaries Risk Matrix.

The full scoring matrix shall be stored in configuration tables rather than hardcoded.

### Tables

risk_business_categories

risk_profession_categories

---

## 6. Transactional Risk

| Annual Volume | Score |
| ------------- | ----- |
| < BDT 1M      | 1     |
| BDT 1M – 5M   | 2     |
| BDT 5M – 50M  | 3     |
| > BDT 50M     | 5     |

---

## 7. Transparency Risk

### Source Of Funds Verification

| Status       | Score |
| ------------ | ----- |
| Verified     | 1     |
| Not Verified | 5     |

---

# Screening Integration

Risk engine consumes:

* Sanctions Screening
* PEP Screening
* Adverse Media Screening
* Exit List Screening
* IP Risk Screening

Outputs are read-only.

---

# EDD Trigger Rules

EDD shall be triggered when:

* Risk Category = HIGH
* PEP Match Found
* IP Match Found
* Adverse Media Match Found
* Source Of Funds Not Verified
* Beneficial Ownership Concerns Exist
* Compliance Officer Escalation

---

# Risk Assessment Statuses

```text
RISK_PENDING
RISK_IN_PROGRESS
RISK_COMPLETED
EDD_REQUIRED
EDD_IN_REVIEW
EDD_APPROVED
EDD_REJECTED
```

---

# Database Design

## customer_risk_assessments

Stores:

* Overall Score
* Risk Category
* Risk Rule Version
* Assessment Timestamp

## customer_risk_factor_scores

Stores:

* Factor Name
* Factor Score
* Source

## risk_rule_versions

Stores:

* Version
* Effective Date
* Status

---

# APIs

## Calculate Risk

POST /api/v1/risk-assessment/calculate

## Retrieve Assessment

GET /api/v1/risk-assessment/{session_id}

## Recalculate Assessment

POST /api/v1/risk-assessment/{session_id}/recalculate

Compliance role only.

---

# Compliance Review Workflow

When:

* HIGH Risk
* EDD Required
* Compliance Escalation

Create:

```text
COMPLIANCE_REVIEW_CASE
```

Statuses:

```text
PENDING_REVIEW
UNDER_REVIEW
APPROVED
REJECTED
```

---

# Audit Requirements

Log:

* Risk Calculations
* Score Changes
* Rule Version Used
* Manual Overrides
* EDD Decisions

All activities must be immutable and auditable.

---

# Success Criteria

The engine is complete when:

* Risk scoring is fully automated.
* LOW/MEDIUM/HIGH classification works correctly.
* Screening results influence risk scores.
* EDD triggers automatically.
* Compliance review cases are created when required.
* Risk decisions are versioned and auditable.
