# Yuvalokham - Frontend Integration Guide

> Complete API reference and integration notes for building the Yuvalokham frontend.
> **Base URL:** `http://localhost:8000` (dev) | `https://<production-domain>` (prod)
> **Swagger Docs:** `{BASE_URL}/docs` (interactive API explorer)

---

## Table of Contents

1. [Authentication System](#1-authentication-system)
2. [Enums & Constants](#2-enums--constants)
3. [Shared Types](#3-shared-types)
4. [Auth APIs (Public)](#4-auth-apis-public)
5. [User APIs (Authenticated)](#5-user-apis-authenticated)
6. [Admin APIs (Admin Only)](#6-admin-apis-admin-only)
7. [User Flows & Page Mapping](#7-user-flows--page-mapping)
8. [Error Handling](#8-error-handling)
9. [File Uploads](#9-file-uploads)
10. [Suggested FE Architecture](#10-suggested-fe-architecture)

---

## 1. Authentication System

### Token Architecture

Yuvalokham uses **independent JWT authentication** (fully isolated from the main CSI app). Tokens include an `iss: "yuvalokham"` claim -- main app tokens will NOT work on Yuvalokham endpoints and vice versa.

| Token | Location | Lifetime | Purpose |
|-------|----------|----------|---------|
| Access Token | `Authorization: Bearer <token>` header | ~15 minutes | Authenticate API requests |
| Refresh Token | Request body to `/refresh` | ~7 days | Get new access token silently |

### Token Storage (Recommended)

```
access_token  -> memory (React state / Zustand / context)
refresh_token -> httpOnly cookie or localStorage
role          -> memory (from login response)
```

### Auth Header Format

Every protected endpoint requires:

```
Authorization: Bearer <access_token>
```

### Token Refresh Flow

1. API call returns `401 Unauthorized`
2. Call `POST /api/yuvalokham/auth/refresh` with stored refresh token
3. On success: update both tokens in storage, retry original request
4. On failure: redirect to login page

### Role-Based Routing

| `role` value | Dashboard | Route prefix suggestion |
|--------------|-----------|------------------------|
| `"admin"` | Admin Dashboard | `/yuvalokham/admin/*` |
| `"user"` | User Dashboard | `/yuvalokham/*` |

---

## 2. Enums & Constants

Define these as TypeScript enums/constants in the FE. Values must match exactly.

```typescript
// User roles
type YuvalokhamUserRole = "admin" | "user";

// Subscription status
type SubscriptionStatus = "active" | "expired" | "pending_payment";

// Payment status
type PaymentStatus = "pending" | "approved" | "rejected";

// Magazine status
type MagazineStatus = "draft" | "published";

// Complaint category
type ComplaintCategory =
  | "delivery_issue"
  | "payment_dispute"
  | "content_issue"
  | "subscription_problem"
  | "other";

// Complaint status
type ComplaintStatus = "open" | "resolved" | "closed";
```

---

## 3. Shared Types

### Paginated Response

All paginated endpoints return this wrapper:

```typescript
interface Paginated<T> {
  items: T[];
  total: number;  // total count across all pages
  page: number;   // current page (1-indexed)
  size: number;   // page size
}
```

**Pagination query params** (all paginated endpoints accept these):

| Param | Type | Default | Range |
|-------|------|---------|-------|
| `skip` | int | `0` | >= 0 |
| `limit` | int | `20` | 1-100 |

### Common Response Types

```typescript
interface YMUser {
  id: number;
  name: string;
  email: string;
  phone: string;
  role: YuvalokhamUserRole;
  address: string | null;
  pincode: string | null;
  district_id: number | null;
  district_name: string | null;  // resolved name from clergy_district table
  unit_id: number | null;
  unit_name: string | null;      // resolved name from unit_name table
  parish_name: string | null;
  is_csi_member: boolean;
  is_active: boolean;
  created_at: string; // ISO datetime
}

interface YMPlan {
  id: number;
  name: string;
  duration_months: number;
  price: string;          // decimal as string e.g. "500.00"
  description: string | null;
  is_active: boolean;
  created_at: string;
}

interface YMSubscription {
  id: number;
  user_id: number;
  plan_id: number;
  plan_name_snapshot: string;
  plan_price_snapshot: string;  // decimal as string
  plan_duration_snapshot: number;
  start_date: string | null;    // "YYYY-MM-DD" or null
  end_date: string | null;
  status: SubscriptionStatus;
  created_at: string;
}

interface YMPayment {
  id: number;
  user_id: number;
  subscription_id: number;
  amount: string;               // decimal as string
  proof_file_url: string;       // pre-signed URL (expires in 1 hour)
  status: PaymentStatus;
  admin_remarks: string | null;
  reviewed_at: string | null;
  created_at: string;
}

interface YMMagazine {
  id: number;
  title: string;
  issue_number: string | null;
  volume: string | null;
  cover_image_url: string | null;   // pre-signed URL or null
  pdf_file_url: string | null;      // pre-signed URL or null (null if not subscribed)
  description: string | null;
  published_date: string | null;    // "YYYY-MM-DD"
  status: MagazineStatus;
  created_at: string;
}

interface YMComplaint {
  id: number;
  user_id: number;
  category: ComplaintCategory;
  subject: string;
  description: string;
  status: ComplaintStatus;
  admin_response: string | null;
  responded_at: string | null;
  created_at: string;
}

interface YMQrSetting {
  id: number;
  qr_image_url: string | null;   // pre-signed URL
  description: string | null;
  is_active: boolean;
  updated_at: string | null;
}

interface YMToken {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  role: YuvalokhamUserRole;
}
```

---

## 4. Auth APIs (Public)

No `Authorization` header needed.

### POST `/api/yuvalokham/auth/register`

Register a new user account.

**Request Body** (JSON):

```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "9876543210",
  "password": "securepass123",
  "address": "123 Church Street, Kottayam",
  "pincode": "686001",
  "district_id": 1,
  "unit_id": 5,
  "parish_name": "St. Thomas CSI Church",
  "is_csi_member": true
}
```

| Field | Required | Validation |
|-------|----------|------------|
| `name` | Yes | 2-150 chars |
| `email` | Yes | Valid email, unique |
| `phone` | Yes | 5-20 chars |
| `password` | Yes | Min 8 chars |
| `address` | No | Free text |
| `pincode` | No | Max 10 chars |
| `district_id` | No | Must exist in `clergy_district` table |
| `unit_id` | No | Must exist in `unit_name` table; must belong to `district_id` if both set |
| `parish_name` | No | Max 255 chars |
| `is_csi_member` | No | Boolean, defaults `false` |

**Response** `201`: `YMUser`

**Errors:**
- `409`: Email already registered
- `400`: Unit does not belong to selected district
- `422`: Validation error (field constraints)

**FE Notes:**
- District/unit dropdowns should use existing CSI APIs: `GET /api/auth/districts` and `GET /api/auth/unit-names?district_id=X`
- When district changes, reset unit dropdown and reload units for that district
- Show password strength indicator (min 8 chars)

---

### POST `/api/yuvalokham/auth/login`

**Request Body** (JSON):

```json
{
  "email": "john@example.com",
  "password": "securepass123"
}
```

**Response** `200`: `YMToken`

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "role": "user"
}
```

**Errors:**
- `401`: Invalid credentials (wrong email/password or inactive account)

**FE Notes:**
- Store `role` to determine routing: `admin` -> admin dashboard, `user` -> user dashboard
- Store tokens (see Token Storage above)
- Redirect based on role immediately after login

---

### POST `/api/yuvalokham/auth/refresh`

**Request Body** (JSON):

```json
{
  "refresh_token": "eyJ..."
}
```

**Response** `200`: `YMToken` (new access + refresh token pair)

**Errors:**
- `401`: Invalid or expired refresh token -> force logout

**FE Notes:**
- Old refresh token is revoked on use (one-time use)
- Implement an Axios/fetch interceptor that catches 401 on protected routes, calls refresh, then retries

---

## 5. User APIs (Authenticated)

All require `Authorization: Bearer <access_token>` header.
Base path: `/api/yuvalokham/user`

### Profile

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/profile` | Get current user profile |
| PUT | `/profile` | Update profile (partial update, only send changed fields) |

**PUT `/profile` Request Body** (JSON, all fields optional):

```json
{
  "name": "John Updated",
  "phone": "9876543211",
  "address": "New Address",
  "pincode": "686002",
  "district_id": 2,
  "unit_id": 10,
  "parish_name": "New Parish",
  "is_csi_member": true
}
```

---

### Subscription Plans

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/plans` | List all active subscription plans |

**Response** `200`: `YMPlan[]`

**FE Notes:** Display as cards with name, price, duration. Add a "Subscribe" button per plan.

---

### Subscriptions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/subscribe` | Subscribe to a plan |
| GET | `/subscriptions?skip=0&limit=20` | Paginated subscription history |
| GET | `/subscriptions/active` | Current active subscription (or `null`) |

**POST `/subscribe` Request Body**:

```json
{ "plan_id": 1 }
```

**Response** `201`: `YMSubscription` with `status: "pending_payment"`

**Errors:**
- `409`: Already have a pending subscription (only one pending allowed at a time)
- `404`: Plan not found or inactive

**FE Notes:**
- After subscribing, redirect user to the payment page
- Check `/subscriptions/active` on dashboard load to show subscription status badge
- If `end_date` is approaching (< 30 days), show renewal prompt

---

### QR Code & Payments

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/qr-code` | Get active payment QR code image |
| POST | `/payments` | Upload payment proof (**multipart/form-data**) |
| GET | `/payments?skip=0&limit=20` | Paginated payment history |

**GET `/qr-code` Response** `200`: `YMQrSetting | null`

**FE Notes:** Display `qr_image_url` as an `<img>` tag. Show `description` as payment instructions below it.

**POST `/payments`** -- **This is a file upload, NOT JSON:**

```
Content-Type: multipart/form-data

Fields:
- subscription_id: <int>  (form field)
- proof: <file>            (image/pdf of payment screenshot)
```

Example with fetch:

```typescript
const formData = new FormData();
formData.append("subscription_id", subscriptionId.toString());
formData.append("proof", file); // File object from <input type="file">

const response = await fetch(`${BASE_URL}/api/yuvalokham/user/payments`, {
  method: "POST",
  headers: { Authorization: `Bearer ${token}` },
  // Do NOT set Content-Type -- browser sets it with boundary
  body: formData,
});
```

**Response** `201`: `YMPayment` with `status: "pending"`

**Errors:**
- `404`: Subscription not found
- `400`: Subscription is not pending payment (already paid/active)

**FE Notes:**
- Payment history should show status badges: `pending` (yellow), `approved` (green), `rejected` (red)
- If rejected, show `admin_remarks` and allow resubmission
- `proof_file_url` is a pre-signed URL (expires in 1 hour) -- use for preview

---

### Magazines

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/magazines` | List published magazines |
| GET | `/magazines/{id}` | Get single magazine detail |

**Response** `200`: `YMMagazine[]` or `YMMagazine`

**Critical FE behavior -- PDF gating:**

- `cover_image_url`: Always a pre-signed URL if available (visible to all)
- `pdf_file_url`: **`null` if user does NOT have an active subscription**. Only returns a pre-signed URL when the user has `status: "active"` and `end_date >= today`.

**FE Notes:**
- Display magazine cards with cover image, title, issue number, published date
- If `pdf_file_url` is `null`, show a "Subscribe to read" overlay/lock icon
- If `pdf_file_url` is present, show a "Read" / "Download" button
- Pre-signed URLs expire in 1 hour. If user stays on page long, re-fetch on click.

---

### Complaints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/complaints` | Register a complaint |
| GET | `/complaints?skip=0&limit=20` | Paginated complaint history |

**POST `/complaints` Request Body**:

```json
{
  "category": "delivery_issue",
  "subject": "Missing December issue",
  "description": "I didn't receive the December 2025 issue at my registered address."
}
```

**Category options for dropdown:**

| Value | Display Label |
|-------|--------------|
| `delivery_issue` | Delivery Issue |
| `payment_dispute` | Payment Dispute |
| `content_issue` | Content Issue |
| `subscription_problem` | Subscription Problem |
| `other` | Other |

**FE Notes:**
- Complaint list should show status badge: `open` (blue), `resolved` (green), `closed` (gray)
- If `status === "resolved"`, display `admin_response` in an expandable section
- `closed` means admin dismissed without response

---

## 6. Admin APIs (Admin Only)

All require `Authorization: Bearer <admin_access_token>` header.
Base path: `/api/yuvalokham/admin`

### User Management

| Method | Endpoint | Query Params | Description |
|--------|----------|-------------|-------------|
| GET | `/users` | `search`, `is_active`, `district_id`, `skip`, `limit` | List all users (paginated) |
| GET | `/users/{id}` | -- | User detail |
| PUT | `/users/{id}` | -- | Update user (includes activate/deactivate) |
| PATCH | `/users/{id}/reset-password` | -- | Reset user password |
| POST | `/admins` | -- | Create another admin account |

**GET `/users` Query Params:**

| Param | Type | Description |
|-------|------|-------------|
| `search` | string | Fuzzy search on name and email |
| `is_active` | boolean | Filter by active status |
| `district_id` | int | Filter by district |

**PUT `/users/{id}` Request Body** (all fields optional):

```json
{
  "name": "Updated Name",
  "is_active": false
}
```

**POST `/admins` Request Body**:

```json
{
  "name": "New Admin",
  "email": "newadmin@csi.org",
  "phone": "1234567890",
  "password": "adminpass123"
}
```

---

### Subscription Plans

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/plans` | List ALL plans (including inactive) |
| POST | `/plans` | Create plan |
| PUT | `/plans/{id}` | Update plan |
| PATCH | `/plans/{id}/toggle` | Toggle active/inactive |

**POST `/plans` Request Body**:

```json
{
  "name": "Annual Plan",
  "duration_months": 12,
  "price": 500.00,
  "description": "Full year subscription"
}
```

**FE Notes:**
- Show inactive plans grayed out with a toggle switch
- Toggling calls `PATCH /plans/{id}/toggle` (no body needed)
- Editing existing plans does NOT affect already-created subscriptions (snapshots)

---

### Subscriptions (Admin View)

| Method | Endpoint | Query Params | Description |
|--------|----------|-------------|-------------|
| GET | `/subscriptions` | `status`, `plan_id`, `user_id`, `skip`, `limit` | All subscriptions |

**Query param `status` values:** `active`, `expired`, `pending_payment`

---

### Payments (Admin View)

| Method | Endpoint | Query Params | Description |
|--------|----------|-------------|-------------|
| GET | `/payments` | `status`, `skip`, `limit` | All payments |
| PATCH | `/payments/{id}/approve` | -- | Approve payment (activates subscription) |
| PATCH | `/payments/{id}/reject` | -- | Reject payment |

**PATCH `/payments/{id}/reject` Request Body**:

```json
{ "remarks": "Payment screenshot is blurry, please resubmit" }
```

**PATCH `/payments/{id}/approve`**: No request body needed.

**FE Notes:**
- Payment review page should show proof image (from `proof_file_url` pre-signed URL)
- Approve action: show confirmation dialog ("This will activate the user's subscription")
- Reject action: show textarea for remarks (required)
- After approve/reject, refresh the payments list

---

### Magazines (Admin Management)

| Method | Endpoint | Query Params | Description |
|--------|----------|-------------|-------------|
| GET | `/magazines` | `status` | List all magazines |
| POST | `/magazines` | -- | Create magazine (draft) |
| PUT | `/magazines/{id}` | -- | Update magazine metadata |
| POST | `/magazines/{id}/files` | -- | Upload cover/PDF (**multipart/form-data**) |
| PATCH | `/magazines/{id}/publish` | -- | Publish magazine |
| DELETE | `/magazines/{id}` | -- | Delete draft magazine (returns `204 No Content`) |

**POST `/magazines` Request Body** (JSON):

```json
{
  "title": "Yuvalokham January 2026",
  "issue_number": "Vol 12 Issue 1",
  "volume": "12",
  "description": "New Year special edition"
}
```

**POST `/magazines/{id}/files`** -- **multipart/form-data:**

```
Fields:
- cover: <file>  (optional, image file)
- pdf: <file>    (optional, PDF file)
```

Both fields are optional -- you can upload just cover, just PDF, or both.

**FE Notes -- Magazine creation flow:**
1. Create magazine with metadata -> `POST /magazines` -> get `id` back
2. Upload files -> `POST /magazines/{id}/files` with cover and/or PDF
3. Preview the magazine in draft state
4. Publish -> `PATCH /magazines/{id}/publish`

**Delete** only works on `draft` magazines. Published magazines cannot be deleted.

---

### Complaints (Admin View)

| Method | Endpoint | Query Params | Description |
|--------|----------|-------------|-------------|
| GET | `/complaints` | `status`, `category`, `skip`, `limit` | All complaints |
| PATCH | `/complaints/{id}/respond` | -- | Respond to complaint |
| PATCH | `/complaints/{id}/close` | -- | Close without response |

**PATCH `/complaints/{id}/respond` Request Body**:

```json
{ "response": "We've reshipped your December issue. Please allow 5-7 days." }
```

**PATCH `/complaints/{id}/close`**: No request body. Sets status to `closed`.

---

### QR Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/qr-settings` | Get current QR code |
| PUT | `/qr-settings` | Update QR code (**multipart/form-data**) |

**PUT `/qr-settings`** -- **multipart/form-data:**

```
Fields:
- qr_image: <file>       (optional, QR code image)
- description: <string>   (optional, payment instructions text)
```

---

### Analytics Dashboard

| Method | Endpoint | Query Params | Description |
|--------|----------|-------------|-------------|
| GET | `/analytics/summary` | -- | Dashboard counts |
| GET | `/analytics/trends` | `months` (default 12, max 24) | Monthly trends |
| GET | `/analytics/breakdowns` | -- | District/plan/category breakdowns |
| GET | `/analytics/expiring` | `days` (default 30, max 365) | Expiring subscriptions |

**GET `/analytics/summary` Response:**

```json
{
  "total_users": 150,
  "active_subscriptions": 95,
  "total_revenue": "47500.00",
  "pending_payments": 12,
  "open_complaints": 3
}
```

**GET `/analytics/trends?months=6` Response:**

```json
[
  { "month": "2025-11", "new_users": 10, "new_subscriptions": 8, "revenue": "4000.00", "complaints": 1 },
  { "month": "2025-12", "new_users": 15, "new_subscriptions": 12, "revenue": "6000.00", "complaints": 2 }
]
```

**GET `/analytics/breakdowns` Response:**

```json
{
  "by_district": [
    { "district_id": 1, "count": 35 },
    { "district_id": 2, "count": 28 }
  ],
  "plan_popularity": [
    { "plan": "Annual Plan", "count": 60 },
    { "plan": "6 Month Plan", "count": 35 }
  ],
  "complaint_categories": [
    { "category": "delivery_issue", "count": 5 },
    { "category": "payment_dispute", "count": 2 }
  ],
  "renewal_rate": 72.5
}
```

**GET `/analytics/expiring?days=30` Response:**

```json
[
  {
    "subscription_id": 42,
    "user_id": 15,
    "user_name": "John Doe",
    "user_email": "john@example.com",
    "plan_name": "Annual Plan",
    "end_date": "2026-04-20",
    "days_remaining": 16
  }
]
```

**FE Notes:**
- Summary: display as stat cards at top of admin dashboard
- Trends: render as line/bar chart (recharts, chart.js)
- Breakdowns: pie charts for district, plan, category. Show renewal rate as a percentage gauge.
- Expiring: table with user details + "days remaining" badge (red if < 7 days)

---

## 7. User Flows & Page Mapping

### User Pages

| Page | Primary APIs | Notes |
|------|-------------|-------|
| **Registration** | `POST /auth/register` | District/unit dropdowns from existing CSI API |
| **Login** | `POST /auth/login` | Redirect based on `role` |
| **Dashboard** | `GET /user/subscriptions/active`, `GET /user/profile` | Show active plan, expiry, quick actions |
| **Plans** | `GET /user/plans` | Cards with subscribe buttons |
| **Payment** | `GET /user/qr-code`, `POST /user/payments` | Show QR, file upload for proof |
| **Subscriptions** | `GET /user/subscriptions` | History table with status badges |
| **Payments** | `GET /user/payments` | History with status, proof preview, rejection remarks |
| **Magazines** | `GET /user/magazines` | Card grid, PDF gated behind subscription |
| **Magazine Detail** | `GET /user/magazines/{id}` | Full metadata + PDF viewer/download |
| **Complaints** | `GET /user/complaints`, `POST /user/complaints` | List + create form |
| **Profile** | `GET /user/profile`, `PUT /user/profile` | Edit form |

### Admin Pages

| Page | Primary APIs | Notes |
|------|-------------|-------|
| **Dashboard** | `GET /admin/analytics/summary`, `GET /admin/analytics/trends` | Stat cards + charts |
| **Users** | `GET /admin/users`, `PUT /admin/users/{id}` | Table with search, filter, activate/deactivate |
| **Subscriptions** | `GET /admin/subscriptions` | Filterable table |
| **Plans** | `GET /admin/plans`, `POST /admin/plans`, `PUT /admin/plans/{id}`, `PATCH /plans/{id}/toggle` | CRUD + toggle |
| **Payments** | `GET /admin/payments`, `PATCH /payments/{id}/approve`, `PATCH /payments/{id}/reject` | Review queue |
| **Magazines** | `GET /admin/magazines`, `POST /magazines`, `POST /magazines/{id}/files`, `PATCH /magazines/{id}/publish` | Full management |
| **Complaints** | `GET /admin/complaints`, `PATCH /complaints/{id}/respond`, `PATCH /complaints/{id}/close` | Response queue |
| **QR Settings** | `GET /admin/qr-settings`, `PUT /admin/qr-settings` | Upload QR image |
| **Analytics** | All `/admin/analytics/*` endpoints | Full breakdown charts |
| **Expiring** | `GET /admin/analytics/expiring` | Actionable list |
| **Admin Management** | `POST /admin/admins` | Create new admins |

### Key User Flow: Subscribe + Pay

```
User Dashboard
  |
  v
Plans Page (GET /user/plans)
  |-- clicks "Subscribe" on a plan
  v
POST /user/subscribe { plan_id }
  |-- returns subscription with status "pending_payment"
  v
Payment Page
  |-- GET /user/qr-code (display QR)
  |-- User scans QR, pays externally
  |-- User uploads proof: POST /user/payments (multipart)
  v
Waiting State (payment status: "pending")
  |
  v
[ADMIN] Reviews payment (GET /admin/payments)
  |-- PATCH /admin/payments/{id}/approve  --> subscription becomes "active"
  |-- PATCH /admin/payments/{id}/reject   --> user sees rejection + remarks
  v
User can now access magazine PDFs
```

---

## 8. Error Handling

### Standard Error Response

```json
{ "detail": "Error message here" }
```

### HTTP Status Codes

| Code | Meaning | FE Action |
|------|---------|-----------|
| `200` | Success | Process response |
| `201` | Created | Process response, show success toast |
| `204` | No Content | Success, no body (e.g., delete) |
| `400` | Validation / Business rule error | Show `detail` as form error |
| `401` | Unauthenticated / Token expired | Attempt refresh, then redirect to login |
| `403` | Wrong role | Show "Access denied" page |
| `404` | Resource not found | Show "Not found" state |
| `409` | Conflict (duplicate email, pending sub exists) | Show `detail` as inline error |
| `422` | Request validation error | Parse `detail` array for field-level errors |

### 422 Validation Error Format

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

Map `loc[1]` to form field names for inline error display.

---

## 9. File Uploads

### Upload Pattern

All file upload endpoints use `multipart/form-data` (NOT JSON).

**Do NOT set `Content-Type` header manually** -- the browser/fetch will set it automatically with the correct boundary.

### Endpoints That Accept Files

| Endpoint | Fields | Max Size |
|----------|--------|----------|
| `POST /user/payments` | `subscription_id` (form), `proof` (file) | From server config |
| `POST /admin/magazines/{id}/files` | `cover` (file, optional), `pdf` (file, optional) | From server config |
| `PUT /admin/qr-settings` | `qr_image` (file, optional), `description` (form, optional) | From server config |

### Pre-signed URLs

File URLs returned by the API (e.g., `cover_image_url`, `pdf_file_url`, `proof_file_url`, `qr_image_url`) are **pre-signed B2 URLs that expire in 1 hour**.

- Use them directly in `<img src>` or `<a href>` tags
- If the user stays on a page for > 1 hour, re-fetch the resource to get a fresh URL
- Do NOT cache these URLs in local storage

---

## 10. Suggested FE Architecture

### Route Structure

```
/yuvalokham/
├── login
├── register
├── user/
│   ├── dashboard
│   ├── profile
│   ├── plans
│   ├── subscriptions
│   ├── payments
│   ├── payment/new          (QR + upload proof page)
│   ├── magazines
│   ├── magazines/:id
│   └── complaints
└── admin/
    ├── dashboard
    ├── users
    ├── users/:id
    ├── subscriptions
    ├── plans
    ├── payments             (review queue)
    ├── magazines
    ├── magazines/new
    ├── magazines/:id/edit
    ├── complaints
    ├── qr-settings
    └── admins/new
```

### API Service Layer

Create a dedicated API service module:

```typescript
// api/yuvalokham.ts

const BASE = "/api/yuvalokham";

// Auth (no token needed)
export const ymAuth = {
  register: (data: RegisterForm) => post(`${BASE}/auth/register`, data),
  login: (data: LoginForm) => post(`${BASE}/auth/login`, data),
  refresh: (token: string) => post(`${BASE}/auth/refresh`, { refresh_token: token }),
};

// User (token required)
export const ymUser = {
  getProfile: () => get(`${BASE}/user/profile`),
  updateProfile: (data: Partial<ProfileForm>) => put(`${BASE}/user/profile`, data),
  getPlans: () => get(`${BASE}/user/plans`),
  subscribe: (planId: number) => post(`${BASE}/user/subscribe`, { plan_id: planId }),
  getSubscriptions: (skip = 0, limit = 20) => get(`${BASE}/user/subscriptions`, { skip, limit }),
  getActiveSubscription: () => get(`${BASE}/user/subscriptions/active`),
  getQrCode: () => get(`${BASE}/user/qr-code`),
  submitPayment: (subscriptionId: number, proof: File) => uploadForm(`${BASE}/user/payments`, { subscription_id: subscriptionId, proof }),
  getPayments: (skip = 0, limit = 20) => get(`${BASE}/user/payments`, { skip, limit }),
  getMagazines: () => get(`${BASE}/user/magazines`),
  getMagazine: (id: number) => get(`${BASE}/user/magazines/${id}`),
  createComplaint: (data: ComplaintForm) => post(`${BASE}/user/complaints`, data),
  getComplaints: (skip = 0, limit = 20) => get(`${BASE}/user/complaints`, { skip, limit }),
};

// Admin (admin token required)
export const ymAdmin = {
  // Users
  getUsers: (params: UserFilters) => get(`${BASE}/admin/users`, params),
  getUser: (id: number) => get(`${BASE}/admin/users/${id}`),
  updateUser: (id: number, data: Partial<AdminUserUpdate>) => put(`${BASE}/admin/users/${id}`, data),
  createAdmin: (data: AdminCreateForm) => post(`${BASE}/admin/admins`, data),
  // Plans
  getPlans: () => get(`${BASE}/admin/plans`),
  createPlan: (data: PlanForm) => post(`${BASE}/admin/plans`, data),
  updatePlan: (id: number, data: Partial<PlanForm>) => put(`${BASE}/admin/plans/${id}`, data),
  togglePlan: (id: number) => patch(`${BASE}/admin/plans/${id}/toggle`),
  // Subscriptions
  getSubscriptions: (params: SubFilters) => get(`${BASE}/admin/subscriptions`, params),
  // Payments
  getPayments: (params: PaymentFilters) => get(`${BASE}/admin/payments`, params),
  approvePayment: (id: number) => patch(`${BASE}/admin/payments/${id}/approve`),
  rejectPayment: (id: number, remarks: string) => patch(`${BASE}/admin/payments/${id}/reject`, { remarks }),
  // Magazines
  getMagazines: (status?: string) => get(`${BASE}/admin/magazines`, { status }),
  createMagazine: (data: MagazineForm) => post(`${BASE}/admin/magazines`, data),
  updateMagazine: (id: number, data: Partial<MagazineForm>) => put(`${BASE}/admin/magazines/${id}`, data),
  uploadMagazineFiles: (id: number, files: { cover?: File; pdf?: File }) => uploadForm(`${BASE}/admin/magazines/${id}/files`, files),
  publishMagazine: (id: number) => patch(`${BASE}/admin/magazines/${id}/publish`),
  deleteMagazine: (id: number) => del(`${BASE}/admin/magazines/${id}`),
  // Complaints
  getComplaints: (params: ComplaintFilters) => get(`${BASE}/admin/complaints`, params),
  respondComplaint: (id: number, response: string) => patch(`${BASE}/admin/complaints/${id}/respond`, { response }),
  closeComplaint: (id: number) => patch(`${BASE}/admin/complaints/${id}/close`),
  // QR
  getQrSettings: () => get(`${BASE}/admin/qr-settings`),
  updateQrSettings: (data: { qr_image?: File; description?: string }) => uploadForm(`${BASE}/admin/qr-settings`, data),
  // Analytics
  getSummary: () => get(`${BASE}/admin/analytics/summary`),
  getTrends: (months = 12) => get(`${BASE}/admin/analytics/trends`, { months }),
  getBreakdowns: () => get(`${BASE}/admin/analytics/breakdowns`),
  getExpiring: (days = 30) => get(`${BASE}/admin/analytics/expiring`, { days }),
};
```

### Auth Guard

```typescript
// Wrap protected routes
function YMAuthGuard({ requiredRole, children }) {
  const { token, role } = useYMAuth();

  if (!token) return <Navigate to="/yuvalokham/login" />;
  if (requiredRole && role !== requiredRole) return <Navigate to="/yuvalokham/login" />;

  return children;
}

// Usage in routes
<Route path="/yuvalokham/admin/*" element={<YMAuthGuard requiredRole="admin"><AdminLayout /></YMAuthGuard>} />
<Route path="/yuvalokham/user/*" element={<YMAuthGuard requiredRole="user"><UserLayout /></YMAuthGuard>} />
```

---

## Quick Reference Card

| What | Where |
|------|-------|
| Swagger UI | `{BASE_URL}/docs` |
| Auth prefix | `/api/yuvalokham/auth` |
| User prefix | `/api/yuvalokham/user` |
| Admin prefix | `/api/yuvalokham/admin` |
| Auth header | `Authorization: Bearer <token>` |
| File uploads | `multipart/form-data` (no manual Content-Type) |
| Pagination | `?skip=0&limit=20` on list endpoints |
| File URLs | Pre-signed, expire in 1 hour |
| Token refresh | `POST /auth/refresh` with refresh_token |
| Admin seed | `yuvalokham.admin@csi.org` / `admin@123` |

---

## FE Change Notes (2026-04-05)

Three backend changes that require frontend updates:

---

### Change 1: Admin Password Reset Endpoint (NEW)

**New endpoint:** `PATCH /api/yuvalokham/admin/users/{id}/reset-password`

```typescript
// Request
interface AdminResetPassword {
  new_password: string; // min 8 chars
}

// Response: YMUser (same as other user endpoints)
```

**Where to add in the UI:**

- Admin > User Detail page: add a "Reset Password" button/action
- On click, show a modal/form with a single `new_password` field (min 8 chars) + confirmation field
- Call `PATCH /admin/users/{id}/reset-password` with `{ "new_password": "..." }`
- On success, show toast: "Password reset successfully"

**API service addition:**

```typescript
// Add to admin API service
resetUserPassword: (userId: number, newPassword: string) =>
  patch(`${BASE}/admin/users/${userId}/reset-password`, { new_password: newPassword }),
```

---

### Change 2: User Response Now Includes District & Unit Names

**`YMUser` type updated** -- two new fields added:

```typescript
// BEFORE
interface YMUser {
  // ...
  district_id: number | null;
  unit_id: number | null;
  // ...
}

// AFTER
interface YMUser {
  // ...
  district_id: number | null;
  district_name: string | null;  // NEW - e.g. "Kanyakumari Diocese"
  unit_id: number | null;
  unit_name: string | null;      // NEW - e.g. "Nagercoil Unit"
  // ...
}
```

**Affected pages -- display `district_name` / `unit_name` instead of IDs:**

| Page | What to change |
|------|----------------|
| User Profile (`/yuvalokham/profile`) | Show `district_name` and `unit_name` in profile card |
| Admin User List (`/yuvalokham/admin/users`) | Show district/unit names in table columns |
| Admin User Detail (`/yuvalokham/admin/users/{id}`) | Show names in detail view |
| Registration form | No change needed (still sends `district_id` / `unit_id`) |
| Profile edit form | No change needed (still sends IDs for updates) |

**Key point:** The names are **read-only display fields** returned by the server. Forms still submit `district_id` and `unit_id` as integers. You do NOT need a separate API call to look up names.

---

### Change 3: Magazine File Upload Response Now Returns Viewable URLs

**What changed:** `POST /admin/magazines/{id}/files` now returns pre-signed URLs in `cover_image_url` and `pdf_file_url` fields (same as the GET endpoints). Previously it returned raw B2 object keys that weren't usable as URLs.

**FE impact:**

- If you were ignoring the response from the upload call and re-fetching the magazine list to get proper URLs -- you no longer need to. The upload response now gives you ready-to-use URLs.
- If you display a preview after upload (e.g., show the cover thumbnail), you can use the response directly without an extra GET call.

**No type changes needed** -- the `YMMagazine` interface stays the same. The only difference is the **values** of `cover_image_url` and `pdf_file_url` in the upload response are now pre-signed URLs (like `https://f005.backblazeb2.com/...?X-Amz-Signature=...`) instead of raw object keys (like `yuvalokham/magazines/covers/abc123.jpg`).

---

### Summary of FE Type Changes

```typescript
// Updated YMUser interface
interface YMUser {
  id: number;
  name: string;
  email: string;
  phone: string;
  role: YuvalokhamUserRole;
  address: string | null;
  pincode: string | null;
  district_id: number | null;
  district_name: string | null;   // NEW
  unit_id: number | null;
  unit_name: string | null;       // NEW
  parish_name: string | null;
  is_csi_member: boolean;
  is_active: boolean;
  created_at: string;
}

// New request type
interface AdminResetPassword {
  new_password: string;
}
```

### New API Endpoint Summary

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| PATCH | `/admin/users/{id}/reset-password` | Admin | Reset a user's password |
