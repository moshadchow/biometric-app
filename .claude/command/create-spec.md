---
description: Create a spec file and feature branch for the next eKYC implementation step
argument-hint: "Step number and feature name e.g. 2 fingerprint onboarding"
allowed-tools: Read, Write, Glob, Bash(git:*)
---

You are a senior developer implementing the Bangladesh BFIU compliant
eKYC platform for Insurance Companies and Capital Market Intermediaries (CMIs).
Always follow the rules in CLAUDE.md and the current eKYC regulatory requirements.

User input: $ARGUMENTS

## Step 1 — Check working directory is clean
Run `git status` and check for uncommitted, unstaged, or
untracked files. If any exist, stop immediately and tell
the user to commit or stash changes before proceeding.
DO NOT CONTINUE until the working directory is clean.

## Step 2 — Parse the arguments
From $ARGUMENTS extract:

1. `step_number` — zero-padded to 2 digits: 2 → 02, 11 → 11

2. `feature_title` — human readable title in Title Case
   - Example: "Fingerprint Onboarding" or "Face Match Verification"

3. `feature_slug` — git and file safe slug
   - Lowercase, kebab-case
   - Only a-z, 0-9 and -
   - Maximum 40 characters
   - Example: fingerprint-onboarding, face-match-verification

4. `branch_name` — format: `feature/<feature_slug>`
   - Example: `feature/fingerprint-onboarding`

If you cannot infer these from $ARGUMENTS, ask the user
to clarify before proceeding.

## Step 3 — Check branch name is not taken
Run `git branch` to list existing branches.
If `branch_name` is already taken, append a number:
`feature/fingerprint-onboarding-01`,
`feature/fingerprint-onboarding-02` etc.

## Step 4 — Switch to main and pull latest
Run:
```
git checkout main
git pull origin main
```

## Step 5 — Create and switch to the feature branch
Run:
```
git checkout -b <branch_name>
```

## Step 6 — Research the codebase and regulatory requirements
Read these files before writing the spec:
- `frontend/src/` contains the React + TypeScript app.
- `frontend/src/components/`, `hooks/`, `services/`, `types/`, and `constants/` hold the main UI and business logic.
- `frontend/src/__tests__/` contains Vitest specs.
- `frontend/public/` stores static assets such as reference images and face-api model files.
- `backend/` contains the Python API, CRUD, schemas, and database code.
- `.claude/specs/` — avoid duplicate implementation
- `docs/eKYC_Requirments.pdf` — mandatory BFIU eKYC compliance rules

Check `CLAUDE.md` to confirm the requested step is not already
marked complete. If it is, warn the user and stop.

Before writing the spec, confirm the feature complies with:
- Simplified vs Regular eKYC requirements
- Fingerprint or face-matching onboarding rules
- NID verification requirements
- Audit trail and record retention requirements
- Screening obligations (UNSCR, adverse media, IP/PEP where applicable)
- Security controls required by the guideline
- Periodic KYC update requirements

## Step 7 — Write the spec
Generate a spec document with this exact structure:

---
# Spec: <feature_title>

## Overview
One paragraph describing what this feature does,
which onboarding model it supports, and how it satisfies
the Bangladesh BFIU eKYC guideline.

## Regulatory context
Reference the applicable eKYC sections:
- Simplified eKYC or Regular eKYC
- Fingerprint onboarding or Face-matching onboarding
- Applicable risk controls and screening requirements
- Data retention and audit obligations

## Depends on
Which previous onboarding or compliance steps must
already be complete.

## Onboarding flow
Describe the end-to-end onboarding process:
1. Data capture
2. Identity verification
3. Biometric verification
4. Screening and sanctions checks
5. Account/profile creation
6. Audit trail generation
7. Notification handling

## Routes / APIs
Every new route or API needed:
- `METHOD /path` — description — access level
- Include webhook or async processing endpoints where applicable

If no new routes: state "No new routes".

## Database changes
Describe:
- New tables
- KYC profile fields
- Audit logs
- Risk grading fields
- Verification attempt tracking
- Screening result storage
- Retention-related metadata

Always verify against `database/db.py` before writing this.
If none: state "No database changes".

## Integrations
List all external/internal integrations required:
- NID verification service
- OCR service
- Fingerprint SDK
- Face matching engine
- SMS/email notification provider
- Sanctions or adverse media screening providers

If none: state "No integrations required".

## Templates / UI
- **Create:** new onboarding or verification templates
- **Modify:** existing templates and workflow updates

Include:
- Mobile responsiveness
- Accessibility
- Capture guidance for face/fingerprint onboarding
- Error and retry states

## Files to change
Every existing file that will be modified.

## Files to create
Every new file, migration, service, SDK wrapper,
worker, or utility module that will be created.

## Security and compliance requirements
Always include:
- HTTPS only
- Encrypted sensitive data storage
- No biometric raw data stored unless explicitly required
- Parameterised queries only
- Role-based access controls
- Full audit logging
- Retry limits for biometric attempts
- Local/private cloud data hosting requirements
- No customer data transfer outside Bangladesh without approval
- Periodic KYC update support
- Failed onboarding logging

## New dependencies
Any new SDKs, libraries, or pip packages.
If none: state "No new dependencies".

## Rules for implementation
Specific constraints Claude must follow. Always include:
- Parameterised queries only
- Follow BFIU eKYC guidelines strictly
- Preserve audit trails for all onboarding attempts
- All onboarding flows must support failure recovery
- Use CSS variables — never hardcode hex values
- All templates extend `index.html`
- OTP/PIN verification must be rate limited
- Biometric retry counts must follow regulatory limits
- Support both assisted onboarding and self check-in where applicable

## Definition of done
A specific, testable checklist. Each item must be
verifiable by running the application or reviewing logs.

Checklist must include:
- Successful onboarding flow
- Failed onboarding handling
- NID verification success/failure
- Sanctions screening validation
- Audit log generation
- Notification delivery
- Retry limit enforcement
- Periodic KYC update support
- Secure data storage validation
---

## Step 8 — Save the spec
Save to:
`.claude/specs/<step_number>-<feature_slug>.md`

## Step 9 — Report to the user
Print a short summary in this exact format:
```
Branch:    <branch_name>
Spec file: .claude/specs/<step_number>-<feature_slug>.md
Title:     <feature_title>
Compliance: BFIU eKYC Guideline
```

Then tell the user:
"Review the spec at
`.claude/specs/<step_number>-<feature_slug>.md`
then enter Plan Mode with Shift+Tab twice to begin implementation."

Do not print the full spec in chat unless explicitly asked.
