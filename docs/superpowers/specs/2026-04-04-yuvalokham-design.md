# Yuvalokham — Magazine Management & Publishing Platform

## Overview

Yuvalokham is an independent magazine management and publishing module for CSI, living within the existing `csi-project-be` FastAPI monolith. It allows anyone — CSI members or outsiders — to subscribe to magazines, pay via QR code with manual admin verification, and access published digital issues. Admins manage users, subscriptions, payments, magazines, complaints, and view comprehensive analytics.

**Key constraint:** Yuvalokham does not share auth, user tables, or business logic with any other app in the monolith. It references existing district/unit tables for organisational data only.

---

## Decisions Log

| Decision | Choice |
|----------|--------|
| User system | Fully independent (`ym_user` table), separate JWT auth |
| Magazine type | Hybrid — physical copies + digital PDF accessible online |
| Subscription model | Flexible admin-defined plans with configurable duration and price |
| Payment flow | Single static QR code managed by admin; users upload proof; admin approves/rejects |
| Registration fields | Name, email, phone, password, address, pincode, district (FK → clergy_district), unit (FK → unit_name), parish, CSI member flag |
| Complaint system | Categorized tickets with single admin response |
| Analytics | Comprehensive — counts, trends, breakdowns by district/plan/category, expiring alerts |
| Architecture | Flat monolithic package (`app/yuvalokham/`) following existing codebase conventions |

---

## Architecture

### File Structure

```
app/yuvalokham/
├── __init__.py
├── models.py          # All ORM models + enums
├── schemas.py         # All Pydantic request/response schemas
├── service.py         # All business logic + auth dependencies
└── routers/
    ├── __init__.py
    ├── auth.py        # Registration, login, refresh
    ├── user.py        # User-facing endpoints
    └── admin.py       # Admin-facing endpoints
```

### Integration Points

- **`main.py`**: Three new `include_router` calls with `/api/yuvalokham/...` prefixes.
- **`alembic/env.py`**: Import `app.yuvalokham.models` for migration autogenerate.
- **`app.common.db`**: Reuses `Base`, `get_async_db`, `get_db`.
- **`app.common.security`**: Reuses `hash_password`, `verify_password`, JWT encode/decode utilities.
- **`app.common.schemas`**: Reuses `Paginated[T]`, `Message`.
- **Existing district/unit tables**: Referenced via foreign keys for organisational data (read-only relationship).

---

## Data Models

All models inherit from `app.common.db.Base`. All table names prefixed with `ym_` to avoid collisions.

### Enums

```python
class YuvalokhamUserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    PENDING_PAYMENT = "pending_payment"

class ComplaintCategory(str, enum.Enum):
    DELIVERY_ISSUE = "delivery_issue"
    PAYMENT_DISPUTE = "payment_dispute"
    CONTENT_ISSUE = "content_issue"
    SUBSCRIPTION_PROBLEM = "subscription_problem"
    OTHER = "other"

class ComplaintStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    CLOSED = "closed"

class MagazineStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
```

### Tables

#### `ym_user`

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | Auto-increment |
| name | String(150) | Required |
| email | String(255) | Unique, required |
| phone | String(20) | Required |
| password_hash | String(255) | bcrypt hash |
| role | Enum(YuvalokhamUserRole) | Default: USER |
| address | Text | Mailing address for physical delivery |
| pincode | String(10) | Postal code |
| district_id | Integer FK | References `clergy_district.id` (nullable) |
| unit_id | Integer FK | References `unit_name.id` (nullable). When both set, `unit_name.clergy_district_id` must match `district_id`. |
| parish_name | String(255) | Church/parish name |
| is_csi_member | Boolean | Default: False |
| is_active | Boolean | Default: True |
| created_at | DateTime | Server default: now |
| updated_at | DateTime | On update: now |

#### `ym_refresh_token`

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | Auto-increment |
| user_id | Integer FK | References ym_user.id |
| token | String(500) | JWT refresh token |
| expires_at | DateTime | Expiry timestamp |
| revoked | Boolean | Default: False |
| created_at | DateTime | Server default: now |

#### `ym_subscription_plan`

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | Auto-increment |
| name | String(150) | e.g. "6 Months Plan" |
| duration_months | Integer | Plan duration |
| price | Numeric(10,2) | Plan price |
| description | Text | Optional details |
| is_active | Boolean | Default: True |
| created_at | DateTime | Server default: now |
| updated_at | DateTime | On update: now |

#### `ym_subscription`

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | Auto-increment |
| user_id | Integer FK | References ym_user.id |
| plan_id | Integer FK | References ym_subscription_plan.id |
| plan_name_snapshot | String(150) | Plan name at time of subscription (frozen) |
| plan_price_snapshot | Numeric(10,2) | Plan price at time of subscription (frozen) |
| plan_duration_snapshot | Integer | Plan duration_months at time of subscription (frozen) |
| start_date | Date | Set on payment approval |
| end_date | Date | Calculated: start_date + plan_duration_snapshot months |
| status | Enum(SubscriptionStatus) | Default: PENDING_PAYMENT |
| created_at | DateTime | Server default: now |
| updated_at | DateTime | On update: now |

**Snapshot rationale:** When a user subscribes, the plan's current name, price, and duration are copied into the subscription row. This ensures admin edits to plans don't retroactively change existing subscriptions.

#### `ym_payment`

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | Auto-increment |
| user_id | Integer FK | References ym_user.id |
| subscription_id | Integer FK | References ym_subscription.id |
| amount | Numeric(10,2) | Payment amount |
| proof_file_url | String(500) | Uploaded proof image/document |
| status | Enum(PaymentStatus) | Default: PENDING |
| admin_remarks | Text | Reason for rejection, etc. |
| reviewed_by | Integer FK | References ym_user.id (admin), nullable |
| reviewed_at | DateTime | Nullable |
| created_at | DateTime | Server default: now |

#### `ym_magazine`

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | Auto-increment |
| title | String(300) | Issue title |
| issue_number | String(50) | e.g. "Vol 12 Issue 3" |
| volume | String(50) | Volume identifier |
| cover_image_url | String(500) | Cover image file |
| pdf_file_url | String(500) | Digital PDF file |
| description | Text | Issue description/summary |
| published_date | Date | When published |
| status | Enum(MagazineStatus) | Default: DRAFT |
| created_at | DateTime | Server default: now |
| updated_at | DateTime | On update: now |

#### `ym_complaint`

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | Auto-increment |
| user_id | Integer FK | References ym_user.id |
| category | Enum(ComplaintCategory) | Predefined category |
| subject | String(300) | Complaint title |
| description | Text | Complaint body |
| status | Enum(ComplaintStatus) | Default: OPEN |
| admin_response | Text | Admin's reply, nullable |
| responded_by | Integer FK | References ym_user.id (admin), nullable |
| responded_at | DateTime | Nullable |
| created_at | DateTime | Server default: now |

#### `ym_qr_setting`

Single-row table. Application enforces exactly one row (upsert on update, seeded on first access).

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | Always 1 |
| qr_image_url | String(500) | QR code image |
| description | Text | Payment instructions |
| is_active | Boolean | Default: True |
| updated_at | DateTime | On update: now |
| updated_by | Integer FK | References ym_user.id (admin) |

---

## Authentication & Authorization

### Independent Auth System

- Own user table (`ym_user`), own refresh token table (`ym_refresh_token`).
- Reuses `app.common.security` utilities (bcrypt, JWT encode/decode) but with its own `OAuth2PasswordBearer(tokenUrl="/api/yuvalokham/auth/login")`.
- JWT payload includes `sub` (user id), `role` (admin/user), `iss` ("yuvalokham") to prevent cross-contamination with main CSI tokens.

### Endpoints

- `POST /api/yuvalokham/auth/register` — user registration only (role always USER).
- `POST /api/yuvalokham/auth/login` — both admin and user.
- `POST /api/yuvalokham/auth/refresh` — refresh token exchange, revokes old token.

### Auth Dependencies

- `get_ym_current_user` — decode JWT (verify `iss == "yuvalokham"`), load `ym_user`, check `is_active`.
- `get_ym_admin_user` — wraps above + checks `role == ADMIN`.

### Admin Seeding

- Admin accounts created by existing admins via `POST /api/yuvalokham/admin/admins`.
- First admin seeded via a script or migration.

---

## API Endpoints

### Auth Routes (`/api/yuvalokham/auth`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/register` | None | User registration |
| POST | `/login` | None | Login (both roles) |
| POST | `/refresh` | None | Refresh token exchange |

### User Routes (`/api/yuvalokham/user`)

All require authenticated USER.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/profile` | Get own profile |
| PUT | `/profile` | Update own profile |
| GET | `/plans` | List active subscription plans |
| POST | `/subscribe` | Subscribe to a plan (creates pending subscription) |
| GET | `/subscriptions` | Own subscription history |
| GET | `/subscriptions/active` | Current active subscription |
| GET | `/qr-code` | Get active payment QR code |
| POST | `/payments` | Upload payment proof |
| GET | `/payments` | Own payment history |
| GET | `/magazines` | List published magazines (metadata always visible; PDF URL only if actively subscribed) |
| GET | `/magazines/{id}` | Magazine detail (metadata always; PDF URL gated behind active subscription) |
| POST | `/complaints` | Register a complaint |
| GET | `/complaints` | Own complaints with admin responses |

### Admin Routes (`/api/yuvalokham/admin`)

All require authenticated ADMIN.

| Method | Path | Description |
|--------|------|-------------|
| **Users** | | |
| GET | `/users` | List all users (paginated, filterable) |
| GET | `/users/{id}` | User detail |
| PUT | `/users/{id}` | Update user (activate/deactivate, edit) |
| POST | `/admins` | Create admin account |
| **Subscriptions** | | |
| GET | `/subscriptions` | List all subscriptions (filterable by status, plan, user) |
| **Plans** | | |
| GET | `/plans` | List all plans (including inactive) |
| POST | `/plans` | Create subscription plan |
| PUT | `/plans/{id}` | Update plan |
| PATCH | `/plans/{id}/toggle` | Activate/deactivate plan |
| **Payments** | | |
| GET | `/payments` | List all payments (filterable by status) |
| PATCH | `/payments/{id}/approve` | Approve payment → activates subscription |
| PATCH | `/payments/{id}/reject` | Reject payment with remarks |
| **Magazines** | | |
| GET | `/magazines` | List all magazines |
| POST | `/magazines` | Create magazine (draft) |
| PUT | `/magazines/{id}` | Update magazine |
| PATCH | `/magazines/{id}/publish` | Publish magazine |
| DELETE | `/magazines/{id}` | Delete draft magazine |
| **Complaints** | | |
| GET | `/complaints` | List all complaints (filterable) |
| PATCH | `/complaints/{id}/respond` | Respond to complaint (sets status to RESOLVED) |
| PATCH | `/complaints/{id}/close` | Close complaint without response (invalid/duplicate) |
| **QR Settings** | | |
| GET | `/qr-settings` | Get current QR |
| PUT | `/qr-settings` | Update QR image |
| **Analytics** | | |
| GET | `/analytics/summary` | Total counts |
| GET | `/analytics/trends` | Monthly trends |
| GET | `/analytics/breakdowns` | By district, plan, complaint category, renewal rates |
| GET | `/analytics/expiring` | Subscriptions expiring soon |

---

## Key Business Rules

### Subscription + Payment Flow

1. User selects a plan → `POST /subscribe` → creates `ym_subscription` with status `PENDING_PAYMENT`. Plan name, price, and duration are **snapshotted** onto the subscription row at this point.
2. User views QR code → `GET /qr-code` → makes external payment.
3. User uploads proof → `POST /payments` → creates `ym_payment` with status `PENDING`.
4. Admin reviews → `PATCH /payments/{id}/approve`:
   - Payment status → `APPROVED`.
   - Subscription `start_date` → today (or end of current active subscription if renewing).
   - Subscription `end_date` → start_date + `plan_duration_snapshot` months.
   - Subscription status → `ACTIVE`.
5. On rejection: payment status → `REJECTED`, subscription stays `PENDING_PAYMENT`, admin adds remarks.

### Pending Subscription Constraints

- A user may have **at most one** subscription with status `PENDING_PAYMENT` at any time. Attempting to create another returns 409 Conflict.
- After payment rejection, the user **may submit a new payment** (`POST /payments`) for the **same** pending subscription. The old rejected payment row stays for audit; a new `ym_payment` row is created.

### Subscription Stacking (Renewal)

If a user subscribes while having an active subscription, the new subscription's `start_date` begins at the current subscription's `end_date`. This prevents overlap and rewards early renewals.

### Subscription Expiry

Subscriptions do **not** require a background job to expire. Expiry is determined **lazily on read**: any subscription where `end_date < today` and `status == ACTIVE` is treated as expired. The `GET /subscriptions/active` endpoint checks `status == ACTIVE AND end_date >= today`. Analytics queries use the same date-based logic.

Optionally, a periodic task can bulk-update status to `EXPIRED` for cleanliness, but the system does not depend on it.

### Magazine Access Control

- `GET /magazines` and `GET /magazines/{id}` are available to **all authenticated users**.
- Magazine **metadata** (title, issue_number, cover image, description, published_date) is always returned.
- **PDF download URL** is only included in the response if the user has an active subscription (`status == ACTIVE AND end_date >= today`). Otherwise, the `pdf_file_url` field is `null` in the response.

### Complaint Lifecycle

1. User creates complaint → status `OPEN`.
2. Admin responds via `PATCH /complaints/{id}/respond` → status becomes `RESOLVED`, admin response text saved.
3. Admin can close without response via `PATCH /complaints/{id}/close` → status becomes `CLOSED` (for invalid/duplicate complaints).

### Plan Editing Safety

Admin edits to `ym_subscription_plan` (price, duration, name) only affect **future** subscriptions. Existing subscriptions use snapshot values frozen at subscription creation time.

---

## Analytics Specifications

### Summary (`GET /analytics/summary`)
- Total registered users
- Active subscriptions count
- Total revenue (sum of approved payments)
- Pending payments count
- Open complaints count

### Trends (`GET /analytics/trends`)
- Query parameter: `months` (default: 12)
- Monthly data points: new users, new subscriptions, revenue, complaints

### Breakdowns (`GET /analytics/breakdowns`)
- Subscriptions by district
- Subscription plan popularity (count per plan)
- Complaint category distribution
- Subscription renewal rate: percentage of users whose previous subscription expired and who created a new subscription within 30 days of that expiry. Calculated as `(renewed_count / expired_count) * 100`.

### Expiring Soon (`GET /analytics/expiring`)
- Query parameter: `days` (default: 30)
- List of subscriptions expiring within the window, with user details

---

## Pagination & Filtering

All list endpoints (admin and user) use `app.common.schemas.Paginated[T]` with `skip` (offset) and `limit` query parameters (defaults: `skip=0`, `limit=20`).

Admin list endpoints support filtering via query parameters:
- `/admin/users`: `search` (name/email), `is_active`, `district_id`
- `/admin/subscriptions`: `status`, `plan_id`, `user_id`
- `/admin/payments`: `status`
- `/admin/complaints`: `status`, `category`
- `/admin/magazines`: `status`

User list endpoints filter implicitly to the authenticated user's own records.

---

## File Uploads & Storage

File uploads use the existing Backblaze B2 storage system (`app.common.storage`).

- **Upload method**: FastAPI `UploadFile` (multipart form-data) → `save_upload_file()` from `app.common.storage`.
- **Subdirectories**: `yuvalokham/payments/` (payment proofs), `yuvalokham/magazines/covers/` (cover images), `yuvalokham/magazines/pdfs/` (PDF files), `yuvalokham/qr/` (QR code images).
- **Validation**: Handled by `_validate_upload()` — checks extension whitelist and max file size from settings.
- **Access**: All files are private. Pre-signed URLs generated via `get_file_url()` with 1-hour expiry for authorized access.
- **Deletion**: Draft magazine deletion calls `delete_file()` for associated cover and PDF objects.

---

## Security

- **Access token TTL**: Reuses `access_token_expire_minutes` from `app.common.config` settings (same as main app).
- **Refresh token TTL**: Reuses `refresh_token_expire_days` from settings. Refresh tokens are stored as plain JWT strings in `ym_refresh_token` (consistent with existing `refresh_token` table pattern).
- **Token isolation**: JWT payload includes `"iss": "yuvalokham"`. The `get_ym_current_user` dependency verifies `iss == "yuvalokham"` to prevent main app tokens from accessing Yuvalokham routes and vice versa.
- **Rate limiting**: Not in initial scope (no rate limiting exists in current codebase). Can be added via middleware later.
- **Registration**: Email uniqueness enforced at DB level (unique constraint). Phone is not unique (family members may share).

---

## Error Handling

- Standard HTTP status codes: 400 (validation), 401 (unauthenticated), 403 (wrong role), 404 (not found), 409 (conflict like duplicate email, duplicate pending subscription).
- Error responses use `app.common.schemas.Message` format: `{"detail": "error description"}`.
- Magazine endpoints do **not** return 403 for unsubscribed users. Instead, `pdf_file_url` is `null` in the response. The 403 code is reserved for role-based access violations (e.g., user accessing admin routes).

---

## Migration Strategy

- Single Alembic migration creating all `ym_*` tables and enums.
- Add `import app.yuvalokham.models` to `alembic/env.py`.
- Seed initial admin user via migration or standalone script.
