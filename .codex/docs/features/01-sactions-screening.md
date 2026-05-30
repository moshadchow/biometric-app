# 01 - Sanctions & Compliance Screening

## Overview

This document defines the requirements and implementation specifications for the Customer Due Diligence (CDD) and Compliance Screening module within the customer onboarding platform.

The screening process is a mandatory component of onboarding and must be completed before a customer account can be activated.

All screening activities must be executed asynchronously using Celery workers with Redis as the broker and result backend.

---

# Objectives

Implement a production-grade compliance screening framework that performs:

* Sanctions Screening
* PEP (Politically Exposed Person) Screening
* Adverse Media Screening
* Internal Watchlist Screening
* External Exit List Screening
* IP & Network Risk Screening

The solution must support automated decisioning, manual review workflows, auditability, and future provider extensibility.

---

# Business Requirements

Customer onboarding shall not be considered complete until all required screening checks have been executed and evaluated.

Customer activation must be blocked until:

* Screening has completed successfully.
* A final compliance decision has been generated.
* Any required manual review has been completed.

---

# Screening Components

## 1. Sanctions Screening

The system shall screen customers against:

### Mandatory Lists

* United Nations Security Council Resolution (UNSCR) Lists
* OFAC Sanctions Lists
* European Union Sanctions Lists

### Optional Lists

* UK HMT Sanctions
* Local Regulatory Sanctions Lists
* FATF Related Lists
* Other configured watchlists

### Matching Types

* Exact Match
* Fuzzy Match
* Alias Match
* Transliteration Match

### Outcomes

* Match Found
* Potential Match
* No Match

---

## 2. PEP Screening

The system shall identify:

* Domestic PEPs
* Foreign PEPs
* International Organization PEPs
* Close Associates
* Family Members

### Outcomes

* High Confidence Match
* Medium Confidence Match
* Low Confidence Match
* No Match

---

## 3. Adverse Media Screening

The system shall identify negative media relating to:

* Fraud
* Corruption
* Bribery
* Money Laundering
* Terrorist Financing
* Sanctions Violations
* Organized Crime
* Regulatory Enforcement
* Financial Misconduct

### Execution

* Always Enabled
* Risk-Based
* Configurable Through Rules Engine

---

## 4. Internal Watchlist Screening

The system shall screen against:

* Internal Blacklists
* Rejected Customers
* Fraud Lists
* Suspicious Customer Lists

---

## 5. External Exit List Screening

The system shall support:

* Third-party exclusion lists
* Regulatory denied-customer lists
* Shared fraud consortium lists

---

## 6. IP & Network Risk Screening

The system shall evaluate:

### IP Intelligence

* IP Geolocation
* Country Validation
* ASN Validation
* Hosting Provider Detection

### Network Risk

* VPN Detection
* Proxy Detection
* TOR Detection
* Datacenter Detection

### Risk Indicators

* High-Risk Country
* Suspicious Reputation
* Velocity Patterns
* Known Abuse Sources

---

# Screening Workflow

## High-Level Flow

1. Customer completes onboarding.
2. Customer identity verification is completed.
3. Screening request is created.
4. Celery workflow is triggered.
5. Screening status becomes:

```
SCREENING_PENDING
```

6. Background screening tasks execute.
7. Results are aggregated.
8. Risk score is calculated.
9. Final decision is generated.

### Possible Decisions

```
APPROVED
REVIEW_REQUIRED
REJECTED
```

10. Customer activation proceeds only for approved cases.

---

# Celery Background Processing

## Requirement

All compliance screening operations must run asynchronously using:

* Celery
* Redis

### Redis Usage

* Message Broker
* Result Backend

### Benefits

* Non-blocking onboarding flow
* Scalability
* Retry handling
* Fault tolerance

---

# Celery Task Design

## Orchestration Task

```
start_screening_workflow
```

Responsibilities:

* Validate request
* Prevent duplicate execution
* Trigger child tasks

---

## Screening Tasks

### run_sanctions_screening

Performs:

* UNSCR screening
* OFAC screening
* EU screening
* Other configured sanctions checks

### run_pep_screening

Performs:

* PEP identification
* Associate screening

### run_adverse_media_screening

Performs:

* Negative news search
* Media risk evaluation

### run_internal_watchlist_screening

Performs:

* Internal blacklist checks

### run_exit_list_screening

Performs:

* External denied-party screening

### run_ip_risk_assessment

Performs:

* Geolocation validation
* VPN/Proxy/TOR detection
* Reputation checks

---

## Aggregation Task

### calculate_risk_score

Responsibilities:

* Collect all screening results
* Calculate overall risk score
* Determine risk category

---

## Finalization Task

### finalize_screening_decision

Responsibilities:

* Generate final decision
* Update onboarding status
* Trigger review workflow if necessary

---

# Risk Scoring Engine

## Risk Categories

### Low Risk

Decision:

```
APPROVED
```

### Medium Risk

Decision:

```
REVIEW_REQUIRED
```

### High Risk

Decision:

```
REJECTED
```

---

## Example Rules

| Rule                      | Decision      |
| ------------------------- | ------------- |
| Exact Sanctions Match     | Reject        |
| Internal Blacklist Match  | Reject        |
| Confirmed Exit List Match | Reject        |
| High Confidence PEP Match | Review        |
| Adverse Media Match       | Review        |
| High-Risk IP + PEP        | Review/Reject |

---

# Compliance Review Workflow

## Review Queue

Potential matches shall be routed to:

```
COMPLIANCE_REVIEW_QUEUE
```

---

## Analyst Actions

Compliance officers may:

* Review evidence
* Add comments
* Request escalation
* Approve
* Reject
* Override automated decisions

---

## Audit Trail

The system shall record:

* Reviewer
* Timestamp
* Previous Decision
* New Decision
* Reason
* Supporting Notes

---

# Database Design

## screening_requests

Stores:

* Request Metadata
* Status
* Trigger Source

---

## screening_jobs

Stores:

* Celery Job IDs
* Task Status
* Retry Counts

---

## screening_results

Stores:

* Provider Results
* Match Information
* Confidence Scores

---

## risk_assessments

Stores:

* Risk Scores
* Risk Factors
* Risk Categories

---

## compliance_cases

Stores:

* Review Cases
* Analyst Decisions

---

## screening_decisions

Stores:

* Final Decisions
* Approval Status

---

## audit_logs

Stores:

* Screening Events
* User Actions
* Compliance Decisions

---

# API Requirements

## Screening APIs

### Start Screening

```
POST /api/v1/compliance/screenings
```

### Get Screening Status

```
GET /api/v1/compliance/screenings/{id}
```

### Get Screening Results

```
GET /api/v1/compliance/screenings/{id}/results
```

### Re-run Screening

```
POST /api/v1/compliance/screenings/{id}/retry
```

---

## Compliance Case APIs

### List Cases

```
GET /api/v1/compliance/cases
```

### Get Case Details

```
GET /api/v1/compliance/cases/{id}
```

### Approve Case

```
POST /api/v1/compliance/cases/{id}/approve
```

### Reject Case

```
POST /api/v1/compliance/cases/{id}/reject
```

---

# Frontend Requirements

## Customer Portal

Display:

* Screening Pending
* Screening In Progress
* Review Required
* Approved
* Rejected

Do not expose sensitive compliance details.

---

## Compliance Portal

Provide:

* Screening Dashboard
* Review Queue
* Match Details
* Risk Score View
* Audit Logs

---

# Security Requirements

* Encryption at Rest
* Encryption in Transit
* Role-Based Access Control (RBAC)
* Secure Credential Storage
* Full Audit Logging
* Provider Secret Management

---

# Reliability Requirements

* Celery Retry Policies
* Exponential Backoff
* Timeout Management
* Dead Letter Queue Support
* Idempotent Processing
* Duplicate Request Prevention
* Structured Logging
* Monitoring & Alerting

---

# Configuration

The following must be configurable:

* Redis Settings
* Celery Settings
* Provider Credentials
* Risk Thresholds
* Country Risk Ratings
* Matching Thresholds
* Retry Policies
* Feature Flags

Configuration must be environment-driven and aligned with the existing application configuration architecture.

---

# Success Criteria

A customer may only be activated when:

* All required screening checks have completed.
* Risk scoring has completed.
* No rejection conditions are present.
* Required compliance reviews have been resolved.
* Final compliance decision is APPROVED.

The implementation must be scalable, auditable, fault tolerant, and suitable for production deployment.
