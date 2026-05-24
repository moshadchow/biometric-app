# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
npm install

# Start development server
npm run dev        # Runs Vite dev server at http://localhost:5173

# Build production bundle
npm run build      # TypeScript type check + Vite build → dist/

# Preview built app locally
npm run preview    # Serves production build from dist/

# Run linting
npm run lint       # ESLint

# Run test suite
npm run test       # Executes Vitest (15 tests)

# Run a single test file
npx vitest run src/__tests__/imageConvert.test.ts
```

## Project Overview

- Pure client-side React + TypeScript application (no backend).
- Implements a two-step biometric onboarding workflow using a `Stepper` component.
- Step 1: Face verification with `@vladmandic/face-api` (WebGL, runs in-browser).
- Step 2: NID OCR extraction using `tesseract.js` with custom validation for Bangladesh NID cards.
- All stateful logic resides in React hooks under `src/hooks/`.
- Pure services under `src/services/` contain business logic free of React dependencies.
- Core components are under `src/components/`, including `Stepper`, `FaceCapture`, `OCRExtractor`, `NIDExtractor`, and `NIDResultView`.
- Constants and configurations are in `src/constants/` (e.g., thresholds, OCR settings).
- Pre‑trained model weights are stored in `public/models/`; required models: `ssd_mobilenetv1`, `face_landmark_68`, `face_recognition`.
- Path alias `@/` maps to `src/` for imports; `"types": ["vite/client"]` enables `import.meta.env` and `?url` imports.

## Key Areas

- **Hooks**: `useCamera`, `useModels`, `useFaceDetection`, `useFaceMatch`, `useOCR`, `useNIDOCR`.
- **Services**: `faceApi.service.ts`, `imageQuality.service.ts`, `imageConvert.service.ts`, `tesseract.service.ts`, `nidValidation.service.ts`.
- **Components**: `Stepper`, `FaceCapture`, `OCRExtractor`, `NIDExtractor`, `NIDResultView`.
- **Validation**: MIME/type/size checks, face detection quality gates, NID card detection regexes for OCR noise handling.
- **Styling**: Inline styled objects; dark theme (#0a0a0a background, #00e5a0 accent, #38b6ff active).

Future contributors should reference this file for command usage, architectural overview, and core abstractions.