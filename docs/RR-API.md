# Reactive-Resume v5 — HTTP API Reference

> **Source**: [AmruthPillai/Reactive-Resume @ main](https://github.com/AmruthPillai/Reactive-Resume/tree/main)
> **Backend stack**: Hono HTTP server · oRPC (typed RPC with REST paths) · Better Auth
> **Last verified**: 2026-06-02 against commit `b9e4ab78`

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Authentication Model](#2-authentication-model)
3. [HTTP Route Map (Hono layer)](#3-http-route-map-hono-layer)
4. [oRPC Endpoint Convention](#4-orpc-endpoint-convention)
5. [Auth API Endpoints](#5-auth-api-endpoints)
6. [Resume CRUD Endpoints](#6-resume-crud-endpoints)
7. [Resume Sharing Endpoints](#7-resume-sharing-endpoints)
8. [PDF Export Endpoint](#8-pdf-export-endpoint)
9. [Auxiliary Endpoints](#9-auxiliary-endpoints)
10. [Resume JSON Structure (GET /resumes/:id response)](#10-resume-json-structure)
11. [Verification on User's LXC — curl Commands](#11-verification-on-users-lxc--curl-commands)

---

## 1. Architecture Overview

RR v5 is **not** NestJS. The backend is:

| Layer | Technology | File |
|-------|-----------|------|
| HTTP server | [Hono](https://hono.dev/) | `apps/server/src/http/app.ts:1` |
| Typed RPC | [oRPC](https://orpc.io/) (`@orpc/server`) | `apps/server/src/rpc/handler.ts:1` |
| Auth | [Better Auth](https://better-auth.com/) | `packages/api/src/context.ts:1` |
| Database | Drizzle ORM + PostgreSQL | `packages/db/` |
| PDF rendering | Chromium/Puppeteer | `packages/pdf/server/` |

All application business logic lives in `packages/api/src/` (the `@reactive-resume/api` package).
The server app at `apps/server/` wires Hono routes to handlers and starts the process.

---

## 2. Authentication Model

**Source**: `packages/api/src/context.ts:21-67`

RR v5 supports **three** authentication methods, checked in priority order:

### 2a. API Key (highest priority)
```
x-api-key: <api-key>
```
- Header: `x-api-key`
- Managed via Better Auth API key plugin
- Code: `context.ts:43-48` — calls `auth.api.verifyApiKey({ body: { key: apiKey } })`

### 2b. Bearer Token (OAuth / machine-to-machine)
```
Authorization: Bearer <token>
```
- Header: `Authorization`
- Token is a JWT issued via the OAuth2 flow (`/api/auth/oauth2/*`)
- Verified via `verifyOAuthToken()` from `@reactive-resume/auth/config`
- Code: `context.ts:23-35` — `getUserFromBearerToken()`

### 2c. Session Cookie (browser / interactive)
```
Cookie: better-auth.session_token=<session>
```
- Standard browser session set by Better Auth after login
- Code: `context.ts:37-45` — `auth.api.getSession({ headers })`

**No auth** (public procedures) — certain endpoints are accessible without any credentials (public resumes, provider list, password verification).

### Procedure guards
- `publicProcedure` — tries to resolve user but does not require auth
- `protectedProcedure` — throws `UNAUTHORIZED` (HTTP 401) if no user resolves

Source: `packages/api/src/context.ts:69-86`

---

## 3. HTTP Route Map (Hono layer)

**Source**: `apps/server/src/http/app.ts:22-44`

| Method | Path | Handler | Auth |
|--------|------|---------|------|
| `POST/GET` | `/api/rpc` | oRPC handler (all RPC calls) | Per-procedure |
| `POST/GET` | `/api/rpc/*` | oRPC handler (REST-style paths) | Per-procedure |
| `GET/POST` | `/api/openapi` | OpenAPI spec handler | None |
| `GET` | `/api/auth/oauth` | OAuth callback | None |
| `ALL` | `/api/auth/*` | Better Auth handler | None |
| `GET` | `/api/health` | Health check | None |
| `GET` | `/api/resumes/:id/pdf` | PDF download (token-gated) | Signed token |
| `GET` | `/api/uploads/*` | Static file uploads | None |
| `GET` | `/uploads/*` | Static file uploads (alias) | None |
| `GET` | `/schema.json` | Resume JSON schema | None |
| `ALL` | `/mcp` | MCP (Model Context Protocol) | OAuth |
| `GET` | `/.well-known/oauth-authorization-server` | OAuth metadata | None |
| `GET` | `/.well-known/openid-configuration` | OIDC metadata | None |

---

## 4. oRPC Endpoint Convention

**Source**: `apps/server/src/rpc/handler.ts:1-20`

All business-logic endpoints go through `POST /api/rpc` or REST-style `GET/POST /api/rpc{path}`.

### Standard oRPC call (POST to procedure key path)
```
POST /api/rpc/{router}.{procedure}
Content-Type: application/json

{"input": { ...payload }}
```

### REST-style call (defined by `.route()` decorator)
Each procedure defines a `.route({ method, path })` that maps to a REST path under `/api/rpc`:
```
GET /api/rpc/resumes          → resume.list
GET /api/rpc/resumes/{id}     → resume.getById
POST /api/rpc/resumes         → resume.create
...etc
```

### Batch requests
Multiple calls in one HTTP round-trip (via `BatchHandlerPlugin`):
```
POST /api/rpc
Content-Type: application/json

[
  {"procedure": "resume/list", "input": {}},
  {"procedure": "resume/getById", "input": {"id": "abc123"}}
]
```

---

## 5. Auth API Endpoints

**Source**: `packages/api/src/features/auth/router.ts:1-47`

Better Auth mounts its own handler at `/api/auth/*`. The oRPC auth router adds two extra procedures.

### 5a. Better Auth endpoints (under `/api/auth/*`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/api/auth/sign-in/email` | Sign in with email + password | None |
| `POST` | `/api/auth/sign-up/email` | Register with email + password | None |
| `POST` | `/api/auth/sign-out` | Sign out (invalidate session) | Session |
| `GET` | `/api/auth/session` | Get current session | Session |
| `GET` | `/api/auth/oauth` | OAuth2 authorization redirect | None |
| `POST` | `/api/auth/api-key/create` | Create a new API key | Session |
| `DELETE` | `/api/auth/api-key/:id` | Delete an API key | Session |

> These are Better Auth's built-in endpoints. Full list at https://better-auth.com/docs

### 5b. oRPC auth procedures

| oRPC Procedure | Method | Path | Auth | Description |
|---------------|--------|------|------|-------------|
| `auth.providers.list` | GET | `/auth/providers` | None | List enabled OAuth providers |
| `auth.deleteAccount` | DELETE | `/auth/account` | Required | Delete current user account (irreversible) |

**Source**: `packages/api/src/features/auth/router.ts:6-47`

#### Example — list providers
```
GET /api/rpc/auth/providers
```
Response:
```json
{
  "github": "GitHub",
  "google": "Google",
  "credentials": "Email & Password"
}
```

---

## 6. Resume CRUD Endpoints

**Source**: `packages/api/src/features/resume/crud.ts:1`

All resume CRUD procedures require authentication (`protectedProcedure`).

### Endpoint Table

| oRPC Procedure | Method | Path | Auth | Description |
|---------------|--------|------|------|-------------|
| `resume.list` | GET | `/resumes` | Required | List user's resumes (metadata only, no `data` field) |
| `resume.getById` | GET | `/resumes/{id}` | Required | Get full resume by ID (includes `data`) |
| `resume.create` | POST | `/resumes` | Required | Create new resume |
| `resume.import` | POST | `/resumes/import` | Required | Import resume from JSON data |
| `resume.update` | PUT | `/resumes/{id}` | Required | Full replace update |
| `resume.patch` | PATCH | `/resumes/{id}` | Required | Partial JSON-Patch update |
| `resume.setLocked` | PUT | `/resumes/{id}/locked` | Required | Lock/unlock resume from editing |
| `resume.duplicate` | POST | `/resumes/{id}/duplicate` | Required | Duplicate a resume |
| `resume.delete` | DELETE | `/resumes/{id}` | Required | Delete a resume permanently |

**Source file**: `packages/api/src/features/resume/crud.ts`

---

### 6a. List Resumes
```
GET /api/rpc/resumes
```
or
```
POST /api/rpc/resume/list
Authorization: Bearer <token>   # OR x-api-key OR Cookie
Content-Type: application/json

{"input": {"tags": [], "sort": "lastUpdatedAt"}}
```

**Input** (`packages/api/src/dto/resume.ts:22-26`):
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `tags` | `string[]` | `[]` | Filter by tags (empty = no filter) |
| `sort` | `"lastUpdatedAt" \| "createdAt" \| "name"` | `"lastUpdatedAt"` | Sort order |

**Response** — array of resume objects **without** `data`, `password`, `userId`:
```json
[
  {
    "id": "clxyz123",
    "name": "Senior Engineer CV",
    "slug": "senior-engineer-cv",
    "tags": ["tech", "2025"],
    "isPublic": false,
    "isLocked": false,
    "createdAt": "2025-01-01T00:00:00.000Z",
    "updatedAt": "2025-06-01T12:00:00.000Z"
  }
]
```
Source: `packages/api/src/dto/resume.ts:22-26` (output omits `data`, `password`, `userId`)

---

### 6b. Get Resume by ID
```
GET /api/rpc/resumes/{id}
Authorization: Bearer <token>
```

**Input**: `id` — string resume UUID (path param)

**Response** — full resume object **including** `data`:
```json
{
  "id": "clxyz123",
  "name": "Senior Engineer CV",
  "slug": "senior-engineer-cv",
  "tags": ["tech"],
  "isPublic": false,
  "isLocked": false,
  "hasPassword": false,
  "updatedAt": "2025-06-01T12:00:00.000Z",
  "data": { ... }
}
```
Note: `password` field is stripped from response; `hasPassword: boolean` is added instead.
Source: `packages/api/src/dto/resume.ts:28-31`

---

### 6c. Create Resume
```
POST /api/rpc/resumes
Authorization: Bearer <token>
Content-Type: application/json

{
  "input": {
    "name": "My New CV",
    "slug": "my-new-cv",
    "tags": [],
    "withSampleData": false
  }
}
```

**Response**: `string` — the ID of the created resume.

Error codes:
- `RESUME_SLUG_ALREADY_EXISTS` (HTTP 400) — slug already in use for this user

Source: `packages/api/src/features/resume/crud.ts:47-79`

---

### 6d. Update Resume
```
PUT /api/rpc/resumes/{id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "input": {
    "id": "clxyz123",
    "name": "Updated CV",
    "slug": "updated-cv",
    "tags": ["new"],
    "isPublic": true,
    "data": { ... }
  }
}
```

All fields except `id` are optional. Response is the updated full resume object with `hasPassword`.

Source: `packages/api/src/dto/resume.ts:38-42`, `packages/api/src/features/resume/crud.ts`

---

### 6e. Patch Resume (JSON-Patch)
```
PATCH /api/rpc/resumes/{id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "input": {
    "id": "clxyz123",
    "operations": [
      { "op": "replace", "path": "/data/basics/name", "value": "Jane Doe" }
    ]
  }
}
```

Uses RFC 6902 JSON Patch operations.
Source: `packages/api/src/features/resume/crud.ts` (uses `jsonPatchOperationSchema` from `@reactive-resume/resume/patch`)

---

## 7. Resume Sharing Endpoints

**Source**: `packages/api/src/features/resume/sharing.ts:1`

### Endpoint Table

| oRPC Procedure | Method | Path | Auth | Description |
|---------------|--------|------|------|-------------|
| `resume.getBySlug` | GET | `/resumes/{username}/{slug}` | None (public) | Get public resume by owner username + slug |
| `resume.setPassword` | PUT | `/resumes/{id}/password` | Required | Set password on a resume |
| `resume.verifyPassword` | POST | `/resumes/{username}/{slug}/password/verify` | None | Verify password for protected resume |
| `resume.removePassword` | DELETE | `/resumes/{id}/password` | Required | Remove password from resume |

### 7a. Get Public Resume by Slug
```
GET /api/rpc/resumes/{username}/{slug}
```
No auth required for public resumes. Returns 401 with `NEED_PASSWORD` error code if password-protected.

**Response**: Same shape as `getById` but:
- `name` field is redacted to `""` for non-owner viewers
- `password` is stripped, no `hasPassword` field

Source: `packages/api/src/features/resume/sharing.ts:6-38`, access policy: `packages/api/src/features/resume/access-policy.ts`

### 7b. Set Resume Password
```
PUT /api/rpc/resumes/{id}/password
Authorization: Bearer <token>
Content-Type: application/json

{"input": {"id": "clxyz123", "password": "mypassword"}}
```

Password must be 6–64 characters. Response: void (204).
Source: `packages/api/src/features/resume/sharing.ts:40-61`, `packages/api/src/dto/resume.ts:48-52`

---

## 8. PDF Export Endpoint

Two-step process. **Source**: `packages/api/src/features/resume/export.ts`

### Step 1 — Get signed download URL (oRPC)

**Source**: `packages/api/src/features/resume/export.ts:37-64`

```
GET /api/rpc/resumes/{id}/pdf
Authorization: Bearer <token>
```

oRPC procedure: `resume.export.downloadPdf` (or via REST path: `GET /api/rpc/resumes/{id}/pdf`)

**Response**: Streams the PDF directly with headers:
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="Senior Engineer CV.pdf"
```

### Step 2 — Direct PDF download URL (Hono layer)

**Source**: `apps/server/src/http/resume-pdf.ts`, `packages/api/src/features/resume/pdf-download-url.ts`

The signed token URL is generated by `createResumePdfDownloadUrl()`:
```
GET /api/resumes/{id}/pdf?token={signed-token}
```

Token is an HMAC-SHA256 signed payload (not a JWT) with:
- `v: 1` — version
- `resumeId` — the resume UUID
- `userId` — the owner's user ID
- `expiresAt` — Unix timestamp (ms)
- `issuedAt` — Unix timestamp (ms)

**TTL**: 10 minutes (`MAX_PDF_DOWNLOAD_URL_TTL_SECONDS = 600`)
Source: `packages/api/src/features/resume/pdf-download-url.ts:9`

**Token format**: `base64url(json_payload).hmac_sha256_signature`

This endpoint does **not** require an `Authorization` header — the token is self-contained.

**Error responses**:
- `401 Unauthorized` — missing or invalid token
- `410 Gone` — token has expired
- `404 Not Found` — resume not found
- `500 Internal Server Error` — PDF generation failure

Source: `apps/server/src/http/resume-pdf.ts:1-50`

---

## 9. Auxiliary Endpoints

### 9a. Health Check
```
GET /api/health
```
No auth. Returns HTTP 200 with health status.
Source: `apps/server/src/http/health.ts` (via `handleHealth()`)

### 9b. JSON Schema
```
GET /schema.json
```
Returns the complete Zod-derived JSON Schema for the `resumeData` object.
Source: `apps/server/src/static/schema.ts`

### 9c. OpenAPI Specification
```
GET /api/openapi
```
Returns the OpenAPI 3.x specification auto-generated from oRPC `.route()` decorators.
Source: `apps/server/src/openapi/handler.ts`

### 9d. Statistics
```
GET /api/rpc/resume/statistics/{id}
```
oRPC procedure: `resume.statistics`
Returns view/download statistics for a resume.
Source: `packages/api/src/features/resume/statistics.ts`

---

## 10. Resume JSON Structure

**Source**: `packages/schema/src/resume/data.ts`

The `data` field returned by `GET /resumes/{id}` is a `resumeDataSchema` object.

### Top-level shape

```json
{
  "basics": { ... },
  "sections": { ... },
  "metadata": { ... }
}
```

### `basics` object
```json
{
  "name":       "string — full name",
  "headline":   "string — professional headline",
  "email":      "string — email address",
  "phone":      "string — phone number",
  "location":   "string — city, country",
  "url":        { "url": "string", "label": "string" },
  "customFields": [
    { "id": "uuid", "icon": "string", "text": "string", "link": "string" }
  ],
  "picture": {
    "hidden":      "boolean",
    "url":         "string — /uploads/... or external URL",
    "size":        "number — pt (32–512)",
    "rotation":    "number — degrees (0–360)",
    "aspectRatio": "number — width/height (0.5–2.5)",
    "borderRadius":"number — pt (0–100)",
    "borderColor": "string — rgba(r,g,b,a)",
    "borderWidth": "number — pt",
    "shadowColor": "string — rgba(r,g,b,a)",
    "shadowWidth": "number — pt"
  }
}
```
Source: `packages/schema/src/resume/data.ts:24-150`

### `sections` object

Contains arrays of resume items organized by section type:

```json
{
  "summary":      { "id": "summary",      "name": "string", "visible": true, "content": "string (HTML)" },
  "experience":   { "id": "experience",   "name": "string", "visible": true, "columns": 1, "separateLinks": true, "items": [ ... ] },
  "education":    { "id": "education",    "name": "string", "visible": true, "columns": 1, "separateLinks": true, "items": [ ... ] },
  "skills":       { "id": "skills",       "name": "string", "visible": true, "columns": 1, "separateLinks": true, "items": [ ... ] },
  "languages":    { "id": "languages",    "name": "string", "visible": true, "columns": 1, "separateLinks": true, "items": [ ... ] },
  "awards":       { "id": "awards",       "name": "string", "visible": true, "columns": 1, "separateLinks": true, "items": [ ... ] },
  "certifications":{ "id": "certifications", "name": "string", "visible": true, "columns": 1, "separateLinks": true, "items": [ ... ] },
  "interests":    { "id": "interests",    "name": "string", "visible": true, "columns": 1, "separateLinks": true, "items": [ ... ] },
  "projects":     { "id": "projects",     "name": "string", "visible": true, "columns": 1, "separateLinks": true, "items": [ ... ] },
  "publications": { "id": "publications", "name": "string", "visible": true, "columns": 1, "separateLinks": true, "items": [ ... ] },
  "volunteering": { "id": "volunteering", "name": "string", "visible": true, "columns": 1, "separateLinks": true, "items": [ ... ] },
  "references":   { "id": "references",   "name": "string", "visible": true, "columns": 1, "separateLinks": true, "items": [ ... ] },
  "profiles":     { "id": "profiles",     "name": "string", "visible": true, "columns": 1, "separateLinks": true, "items": [ ... ] },
  "custom":       { ... }
}
```

### Typical section item (e.g. `experience.items[]`)
```json
{
  "id":          "uuid",
  "visible":     true,
  "company":     "string",
  "position":    "string",
  "date":        "string — e.g. 'Jan 2022 – Present'",
  "location":    "string",
  "summary":     "string (HTML)",
  "url":         { "url": "string", "label": "string", "inlineLink": false }
}
```

### `metadata` object
```json
{
  "template":   "string — template ID",
  "layout":     "array — column layout config",
  "css":        { "value": "string — custom CSS", "visible": false },
  "page":       { "margin": 18, "format": "a4", "options": { "breakLine": true, "pageNumbers": true } },
  "theme":      { "background": "#ffffff", "text": "#000000", "primary": "#ca9a3e" },
  "typography": { "font": { "family": "IBM Plex Serif", "subset": "latin", "variants": ["regular","600"], "size": 14 }, "lineHeight": 1.5, "hideIcons": false, "underlineLinks": true },
  "notes":      "string — private notes about the resume"
}
```
Source: `packages/schema/src/resume/data.ts:200-400`

---

## 11. Verification on User's LXC — curl Commands

Replace `{{RR_URL}}` with your RR instance base URL (e.g. `https://resume.example.com`)
and `{{TOKEN}}` with a Bearer token from the OAuth flow or use a session cookie.

### 1. Health check (no auth)
```bash
curl -s "{{RR_URL}}/api/health"
```
Expected: `200 OK`

### 2. Get session / verify auth
```bash
curl -s "{{RR_URL}}/api/auth/session" \
  -H "Authorization: Bearer {{TOKEN}}" \
  | jq .
```
Expected: JSON with `user` object containing `id`, `email`, `name`.

### 3. List auth providers (no auth)
```bash
curl -s "{{RR_URL}}/api/rpc/auth/providers" | jq .
```
Expected: Object mapping provider keys to display names.

### 4. List all resumes
```bash
curl -s "{{RR_URL}}/api/rpc/resumes" \
  -H "Authorization: Bearer {{TOKEN}}" \
  | jq '.[] | {id, name, slug, updatedAt}'
```
Expected: Array of resume metadata objects (no `data` field).

### 5. Get a single resume (full data)
```bash
RESUME_ID="<paste-id-from-step-4>"
curl -s "{{RR_URL}}/api/rpc/resumes/${RESUME_ID}" \
  -H "Authorization: Bearer {{TOKEN}}" \
  | jq '{id, name, hasPassword, "basics": .data.basics.name}'
```
Expected: Full resume object with `data.basics`, `data.sections`, `data.metadata`.

### 6. Get resume via POST (oRPC native style)
```bash
RESUME_ID="<paste-id>"
curl -s -X POST "{{RR_URL}}/api/rpc/resume/getById" \
  -H "Authorization: Bearer {{TOKEN}}" \
  -H "Content-Type: application/json" \
  -d "{\"input\": {\"id\": \"${RESUME_ID}\"}}" \
  | jq .
```

### 7. Download PDF (oRPC — streams directly)
```bash
RESUME_ID="<paste-id>"
curl -s -L "{{RR_URL}}/api/rpc/resumes/${RESUME_ID}/pdf" \
  -H "Authorization: Bearer {{TOKEN}}" \
  -o "resume.pdf"
echo "PDF saved to resume.pdf"
```

### 8. Get public resume by slug (no auth)
```bash
USERNAME="<owner-username>"
SLUG="<resume-slug>"
curl -s "{{RR_URL}}/api/rpc/resumes/${USERNAME}/${SLUG}" | jq .
```
Expected: Public resume data (name redacted if not owner).

### 9. Create a new resume
```bash
curl -s -X POST "{{RR_URL}}/api/rpc/resumes" \
  -H "Authorization: Bearer {{TOKEN}}" \
  -H "Content-Type: application/json" \
  -d '{"input": {"name": "Test CV", "slug": "test-cv", "tags": [], "withSampleData": false}}' \
  | jq .
```
Expected: String (new resume ID).

### 10. Get OpenAPI spec
```bash
curl -s "{{RR_URL}}/api/openapi" | jq '.info, (.paths | keys)'
```
Expected: OpenAPI 3.x spec with all endpoints from oRPC `.route()` definitions.

---

## Appendix A — Auth Flow for API Key (Recommended for automation)

1. Log into RR UI
2. Navigate to **Settings → Account → API Keys**
3. Create a new API key and copy it
4. Use in requests: `x-api-key: <your-api-key>`

```bash
curl -s "{{RR_URL}}/api/rpc/resumes" \
  -H "x-api-key: {{API_KEY}}" \
  | jq '.[].name'
```

---

## Appendix B — Key Source File Index

| File | Purpose |
|------|---------|
| `apps/server/src/http/app.ts` | Hono route registrations — the authoritative HTTP route map |
| `apps/server/src/rpc/handler.ts` | oRPC handler setup (prefix, plugins) |
| `apps/server/src/http/auth.ts` | Better Auth handler + OAuth sanitization |
| `apps/server/src/http/resume-pdf.ts` | PDF token-gated download endpoint |
| `packages/api/src/context.ts` | Auth resolution (API key, Bearer, session) · `publicProcedure` / `protectedProcedure` |
| `packages/api/src/routers/index.ts` | Root router — maps `resume`, `auth`, `ai`, etc. |
| `packages/api/src/features/resume/router.ts` | Resume sub-router, re-exports from crud/sharing/export |
| `packages/api/src/features/resume/crud.ts` | list, getById, create, import, update, patch, setLocked, duplicate, delete |
| `packages/api/src/features/resume/sharing.ts` | getBySlug, setPassword, verifyPassword, removePassword |
| `packages/api/src/features/resume/export.ts` | downloadResumePdfProcedure + createResumePdfDownload |
| `packages/api/src/features/resume/pdf-download-url.ts` | Signed token generation/verification for PDF download |
| `packages/api/src/features/auth/router.ts` | oRPC auth procedures (providers.list, deleteAccount) |
| `packages/api/src/dto/resume.ts` | Zod schemas for all resume request/response shapes |
| `packages/schema/src/resume/data.ts` | Full `resumeDataSchema` — the resume JSON structure |
