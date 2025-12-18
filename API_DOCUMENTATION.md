# CSI Kalamela FastAPI - Complete API Documentation

## Base URL
```
{BASE_URL} = http://localhost:8000
```

## Authentication
All authenticated endpoints require JWT Bearer token in the Authorization header:
```
Authorization: Bearer {access_token}
```

---

## Table of Contents
1. [System](#1-system)
2. [Authentication (auth)](#2-authentication-auth)
3. [Units Module](#3-units-module)
4. [Conference Module](#4-conference-module)
5. [Kalamela Module](#5-kalamela-module)
6. [Admin Modules](#6-admin-modules)

---

## 1. System

### GET /health
**Description:** Health check endpoint

**Authentication:** None

**Response (200):**
```json
{
  "status": "ok"
}
```

---

## 2. Authentication (auth)

### POST /auth/login
**Description:** User login

**Authentication:** None

**Request Body:**
```json
{
  "username": "string",  // Can be username, email, or phone number
  "password": "string"
}
```

**Success Response (200):**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Error Response (401):**
```json
{
  "detail": "Invalid credentials"
}
```

---

### POST /auth/register-unit
**Description:** Register a new unit user

**Authentication:** None

**Request Body:**
```json
{
  "email": "user@example.com",
  "phone_number": "string",
  "first_name": "string",
  "last_name": "string | null",  // optional
  "unit_name_id": 1,  // integer
  "clergy_district_id": 1,  // integer
  "password": "string"  // min 8 characters
}
```

**Success Response (201):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "user@example.com",
  "first_name": "string",
  "last_name": "string | null",
  "phone_number": "string",
  "user_type": "UNIT",
  "unit_name_id": 1,
  "clergy_district_id": 1,
  "is_active": true
}
```

**Error Response (400):**
```json
{
  "detail": "User already exists"
}
```

---

### GET /auth/unit-names
**Description:** Get list of unit names for registration

**Authentication:** None

**Query Parameters:**
- `district_id` (optional): Filter by district ID

**Success Response (200):**
```json
[
  {
    "id": 1,
    "clergy_district_id": 1,
    "name": "Unit Name"
  }
]
```

---

### GET /auth/me
**Description:** Get current user information

**Authentication:** Required

**Success Response (200):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "string",
  "first_name": "string",
  "last_name": "string | null",
  "phone_number": "string",
  "user_type": "UNIT | DISTRICT_OFFICIAL | ADMIN",
  "unit_name_id": 1,
  "clergy_district_id": 1,
  "is_active": true
}
```

**Error Response (404):**
```json
{
  "detail": "User not found"
}
```

---

### POST /auth/forgot-password/request
**Description:** Request password reset

**Authentication:** None

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Success Response (200):**
```json
{
  "message": "Password reset link would be sent if this were wired to email."
}
```

---

### POST /auth/forgot-password/confirm
**Description:** Confirm password reset

**Authentication:** None

**Request Body:**
```json
{
  "token": "string",
  "new_password": "string"  // min 8 characters
}
```

**Success Response (200):**
```json
{
  "message": "Password reset not implemented in this sample."
}
```

---

## 3. Units Module

### GET /units/application-form
**Description:** Get application form data with current registration status

**Authentication:** Required (Unit user)

**Success Response (200):**
```json
{
  "user_data": {
    "id": 1,
    "username": "string",
    "email": "string",
    "unit_name": "string | null"
  },
  "registration_status": "Registration Started | Unit Details | Unit Members Completed | Unit Officials Completed | Unit Councilors Completed | Registration Completed",
  "unit_details": {
    "id": 1,
    "registered_user_id": 1,
    "registration_year": 2025,
    "number_of_unit_members": 0
  } | null,
  "unit_officials": {
    "id": 1,
    "registered_user_id": 1,
    "president_designation": "string",
    "president_name": "string",
    "president_phone": "string",
    "vice_president_name": "string",
    "vice_president_phone": "string",
    "secretary_name": "string",
    "secretary_phone": "string",
    "joint_secretary_name": "string",
    "joint_secretary_phone": "string",
    "treasurer_name": "string",
    "treasurer_phone": "string"
  } | null,
  "unit_members": [
    {
      "id": 1,
      "registered_user_id": 1,
      "name": "string",
      "gender": "M | F",
      "dob": "2000-01-01",
      "number": "string",
      "qualification": "string",
      "blood_group": "string"
    }
  ],
  "unit_councilors": [
    {
      "id": 1,
      "registered_user_id": 1,
      "unit_member_id": 1
    }
  ],
  "member_count": 0,
  "councilor_count": 0,
  "number_of_councilor_fields": 1,
  "members_amount": 0,
  "total_amount": 100
}
```

---

### POST /units/details
**Description:** Save unit details and president information

**Authentication:** Required (Unit user)

**Request Body:**
```json
{
  "president_designation": "string",  // min 1 char
  "president_name": "string",  // min 1 char
  "president_phone": "string"  // min 1 char
}
```

**Success Response (200):**
```json
{
  "message": "Unit details saved successfully"
}
```

---

### POST /units/members
**Description:** Add a unit member

**Authentication:** Required (Unit user)

**Request Body:**
```json
{
  "name": "string",  // min 1 char
  "gender": "M | F | null",  // optional
  "dob": "2000-01-01 | null",  // optional (YYYY-MM-DD)
  "number": "string | null",  // optional
  "qualification": "string | null",  // optional
  "blood_group": "string | null"  // optional
}
```

**Success Response (200):**
```json
{
  "message": "Unit member added successfully",
  "member_id": 1
}
```

**Error Response (400):**
```json
{
  "detail": "A member with the same name already exists"
}
```

---

### POST /units/members/submit
**Description:** Mark members section as complete

**Authentication:** Required (Unit user)

**Success Response (200):**
```json
{
  "message": "Members section completed successfully"
}
```

---

### PUT /units/members/{member_id}
**Description:** Update a unit member

**Authentication:** Required (Unit user)

**Path Parameters:**
- `member_id`: Member ID (integer)

**Request Body:**
```json
{
  "name": "string | null",
  "gender": "M | F | null",
  "dob": "2000-01-01 | null",
  "number": "string | null",
  "qualification": "string | null",
  "blood_group": "string | null"
}
```

**Success Response (200):**
```json
{
  "message": "Member updated successfully"
}
```

**Error Response (404):**
```json
{
  "detail": "Member not found"
}
```

---

### DELETE /units/members/{member_id}
**Description:** Delete a unit member

**Authentication:** Required (Unit user)

**Path Parameters:**
- `member_id`: Member ID (integer)

**Success Response (200):**
```json
{
  "message": "Member removed successfully"
}
```

**Error Response (404):**
```json
{
  "detail": "Member not found"
}
```

---

### POST /units/officials
**Description:** Add or update unit officials

**Authentication:** Required (Unit user)

**Request Body:**
```json
{
  "position": "President | Vice President | Secretary | Joint Secretary | Treasurer",
  "name": "string",  // min 1 char
  "phone": "string",  // min 1 char
  "designation": "string | null"  // required for President only
}
```

**Success Response (200):**
```json
{
  "message": "{Position} data added successfully"
}
```

**Error Response (400):**
```json
{
  "detail": "Designation is required for President"
}
```

---

### POST /units/officials/confirm
**Description:** Mark officials section as complete

**Authentication:** Required (Unit user)

**Success Response (200):**
```json
{
  "message": "Officials section completed successfully"
}
```

---

### PUT /units/officials
**Description:** Update unit officials (same as POST)

**Authentication:** Required (Unit user)

---

### POST /units/councilors
**Description:** Add a unit councilor

**Authentication:** Required (Unit user)

**Request Body:**
```json
{
  "unit_member_id": 1  // must be > 0
}
```

**Success Response (200):**
```json
{
  "message": "Member added to unit council successfully",
  "councilor_id": 1
}
```

**Error Response (400):**
```json
{
  "detail": "Member is already a councilor"
}
```

---

### POST /units/councilors/confirm
**Description:** Mark councilors section as complete

**Authentication:** Required (Unit user)

**Success Response (200):**
```json
{
  "message": "Councilors section completed successfully"
}
```

---

### PUT /units/councilors/{councilor_id}
**Description:** Update a councilor

**Authentication:** Required (Unit user)

**Path Parameters:**
- `councilor_id`: Councilor ID (integer)

**Request Body:**
```json
{
  "unit_member_id": 1
}
```

**Success Response (200):**
```json
{
  "message": "Councilor updated successfully"
}
```

---

### POST /units/declaration
**Description:** Complete declaration and finalize registration

**Authentication:** Required (Unit user)

**Success Response (200):**
```json
{
  "message": "Registration completed successfully"
}
```

---

### GET /units/finish-registration
**Description:** Get final registration summary

**Authentication:** Required (Unit user)

**Success Response (200):**
```json
{
  "unit_details": { ... },
  "unit_officials": { ... },
  "unit_members": [ ... ],
  "unit_councilors": [ ... ],
  "councilors_count": 0,
  "members_count": 0,
  "members_amount": 0,
  "total_amount": 100
}
```

---

### GET /units/archived-members
**Description:** Get list of archived members

**Authentication:** Required (Unit user)

**Success Response (200):**
```json
[
  {
    "id": 1,
    "registered_user_id": 1,
    "name": "string",
    "gender": "string",
    "dob": "2000-01-01",
    "number": "string",
    "qualification": "string",
    "blood_group": "string",
    "archived_at": "2025-01-01T00:00:00Z"
  }
]
```

---

### POST /units/transfer-request
**Description:** Create a unit transfer request

**Authentication:** Required (Unit user)

**Request Body:**
```json
{
  "unit_member_id": 1,
  "destination_unit_id": 1,
  "reason": "string",  // min 10 chars
  "proof": "string"  // file path, must end with .pdf, .png, .jpg, or .jpeg
}
```

**Success Response (200):**
```json
{
  "id": 1,
  "unit_member_id": 1,
  "destination_unit_id": 1,
  "reason": "string",
  "current_unit_id": 1,
  "original_registered_user_id": 1,
  "proof": "string",
  "status": "PENDING",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

---

### GET /units/transfer-requests
**Description:** Get transfer requests for current user

**Authentication:** Required (Unit user)

**Success Response (200):**
```json
[
  {
    "id": 1,
    "unit_member_id": 1,
    "destination_unit_id": 1,
    "reason": "string",
    "current_unit_id": 1,
    "original_registered_user_id": 1,
    "proof": "string",
    "status": "PENDING | APPROVED | REJECTED",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z"
  }
]
```

---

### POST /units/member-change-request
**Description:** Create a member information change request

**Authentication:** Required (Unit user)

**Request Body:**
```json
{
  "unit_member_id": 1,
  "reason": "string",  // min 10 chars
  "name": "string | null",
  "gender": "string | null",
  "dob": "2000-01-01 | null",
  "blood_group": "string | null",
  "qualification": "string | null",
  "proof": "string"  // file path
}
```

**Success Response (200):**
```json
{
  "id": 1,
  "unit_member_id": 1,
  "reason": "string",
  "name": "string | null",
  "gender": "string | null",
  "dob": "2000-01-01 | null",
  "blood_group": "string | null",
  "qualification": "string | null",
  "original_name": "string",
  "original_gender": "string",
  "original_dob": "2000-01-01",
  "original_blood_group": "string",
  "original_qualification": "string",
  "proof": "string",
  "status": "PENDING",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

---

### GET /units/member-change-requests
**Description:** Get member change requests for current user

**Authentication:** Required (Unit user)

**Success Response (200):** Array of member change request objects

---

### POST /units/officials-change-request
**Description:** Create an officials change request

**Authentication:** Required (Unit user)

**Request Body:**
```json
{
  "unit_official_id": 1,
  "reason": "string",  // min 10 chars
  "president_designation": "string | null",
  "president_name": "string | null",
  "president_phone": "string | null",
  "vice_president_name": "string | null",
  "vice_president_phone": "string | null",
  "secretary_name": "string | null",
  "secretary_phone": "string | null",
  "joint_secretary_name": "string | null",
  "joint_secretary_phone": "string | null",
  "treasurer_name": "string | null",
  "treasurer_phone": "string | null",
  "proof": "string"  // file path
}
```

**Success Response (200):** Officials change request response object with original values

---

### GET /units/officials-change-requests
**Description:** Get officials change requests for current user

**Authentication:** Required (Unit user)

---

### POST /units/councilor-change-request
**Description:** Create a councilor change request

**Authentication:** Required (Unit user)

**Request Body:**
```json
{
  "unit_councilor_id": 1,
  "reason": "string",  // min 10 chars
  "unit_member_id": 1,  // new member to assign
  "proof": "string"  // file path
}
```

---

### GET /units/councilor-change-requests
**Description:** Get councilor change requests for current user

**Authentication:** Required (Unit user)

---

### POST /units/member-add-request
**Description:** Create a request to add a new member

**Authentication:** Required (Unit user)

**Request Body:**
```json
{
  "name": "string",
  "gender": "string",
  "dob": "2000-01-01",
  "number": "string",
  "qualification": "string | null",
  "blood_group": "string | null",
  "reason": "string",  // min 10 chars
  "proof": "string | null"  // file path
}
```

---

## 4. Conference Module

### Public Routes (No Auth Required)

#### GET /conference/public/list
**Description:** List all active conferences

**Success Response (200):**
```json
[
  {
    "id": 1,
    "title": "string",
    "details": "string",
    "added_on": "2025-01-01T00:00:00Z",
    "status": "Active"
  }
]
```

---

#### GET /conference/public/{conference_id}
**Description:** Get conference details by ID

**Path Parameters:**
- `conference_id`: Conference ID (integer)

**Success Response (200):**
```json
{
  "id": 1,
  "title": "string",
  "details": "string",
  "added_on": "2025-01-01T00:00:00Z",
  "status": "Active"
}
```

**Error Response (404):**
```json
{
  "detail": "Conference not found"
}
```

---

### Official Routes (District Official Auth Required)

#### GET /conference/official/view
**Description:** View conference details and available members for the official's district

**Authentication:** Required (District Official)

**Success Response (200):**
```json
{
  "conference": {
    "id": 1,
    "title": "string",
    "details": "string",
    "status": "Active"
  },
  "rem_count": 20,
  "max_count": 25,
  "allowed_count": 25,
  "member_count": 5,
  "district": "District Name",
  "unit_members": [
    {
      "id": 1,
      "name": "string",
      "number": "string",
      "gender": "M | F"
    }
  ]
}
```

---

#### POST /conference/official/delegates/{member_id}
**Description:** Add a member as a delegate

**Authentication:** Required (District Official)

**Path Parameters:**
- `member_id`: Member ID (integer)

**Success Response (200):**
```json
{
  "message": "Delegate added successfully"
}
```

---

#### GET /conference/official/delegates
**Description:** View all delegates (officials + members) for this district

**Authentication:** Required (District Official)

**Success Response (200):**
```json
{
  "delegate_members": [
    {
      "id": 1,
      "name": "string",
      "number": "string",
      "gender": "M | F"
    }
  ],
  "delegate_officials": [
    {
      "id": 1,
      "name": "string",
      "phone": "string"
    }
  ],
  "delegates_count": 10,
  "max_count": 30,
  "payment_status": "PAID | NOT PAID | PENDING | null",
  "amount_to_pay": 9000,
  "food_preference": {
    "veg_count": 5,
    "non_veg_count": 5
  } | null
}
```

---

#### DELETE /conference/official/delegates/members/{member_id}
**Description:** Remove a member from delegates

**Authentication:** Required (District Official)

**Success Response (200):**
```json
{
  "message": "Delegate member removed successfully"
}
```

---

#### POST /conference/official/payment
**Description:** Upload payment proof

**Authentication:** Required (District Official)

**Request Body:**
```json
{
  "conference_id": 1,  // auto-set from user context
  "amount_to_pay": 9000,  // optional
  "proof": "string | null",  // file path
  "status": "PENDING | PAID | NOT_PAID"
}
```

**Success Response (200):**
```json
{
  "message": "Payment data uploaded successfully",
  "payment_id": 1
}
```

---

#### POST /conference/official/food-preference
**Description:** Set food preferences for the district

**Authentication:** Required (District Official)

**Request Body:**
```json
{
  "conference_id": 1,  // auto-set from user context
  "veg_count": 10,
  "non_veg_count": 15
}
```

**Success Response (200):**
```json
{
  "id": 1,
  "conference_id": 1,
  "veg_count": 10,
  "non_veg_count": 15,
  "uploaded_by_id": 1,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

---

#### GET /conference/official/export-excel
**Description:** Export district conference data to Excel

**Authentication:** Required (District Official)

**Success Response (200):**
```json
{
  "message": "Excel export functionality to be implemented",
  "district": "District Name",
  "data": { ... }
}
```

---

## 5. Kalamela Module

### Public Routes (No Auth Required)

#### GET /kalamela/home
**Description:** Landing page data with event statistics

**Success Response (200):**
```json
{
  "total_individual_events": 50,
  "total_group_events": 20,
  "total_individual_participants": 500,
  "total_group_teams": 100,
  "message": "Welcome to CSI Madhya Kerala Diocese Youth Movement Kalamela"
}
```

---

#### POST /kalamela/find-participant
**Description:** Search participant by chest number

**Query Parameters:**
- `chest_number`: string (required)

**Success Response (200):**
```json
{
  "chest_number": "string",
  "individual_participations": [
    {
      "event_name": "string",
      "participant_name": "string",
      "unit_name": "string",
      "district_name": "string",
      "chest_number": "string",
      "score": 85 | null,
      "grade": "A | null",
      "awarded_mark": 80 | null
    }
  ],
  "group_participations": [...]
}
```

**Error Response (404):**
```json
{
  "detail": "No participant found with this chest number"
}
```

---

#### GET /kalamela/results
**Description:** Get top 3 results for each event

**Success Response (200):**
```json
{
  "individual_results": {
    "Event Name": [
      {
        "position": 1,
        "participant_name": "string",
        "unit_name": "string",
        "district_name": "string",
        "chest_number": "string",
        "total_points": 95,
        "grade": "A"
      }
    ]
  },
  "group_results": {
    "Event Name": [
      {
        "position": 1,
        "chest_number": "string",
        "total_points": 95,
        "grade": "A"
      }
    ]
  }
}
```

---

#### GET /kalamela/kalaprathibha
**Description:** Get Kalaprathibha (Male) and Kalathilakam (Female) results

**Success Response (200):**
```json
{
  "kalaprathibha": [
    {
      "participant_name": "string",
      "participant_unit": "string",
      "participant_district": "string",
      "combined_score": 180,
      "event_count": 3
    }
  ],
  "kalathilakam": [...]
}
```

---

#### POST /kalamela/appeal/check
**Description:** Check if appeal can be submitted

**Query Parameters:**
- `chest_number`: string (required)
- `event_name`: string (required)

**Success Response (200) - Eligible:**
```json
{
  "eligible": true,
  "score_time": "2025-01-01T00:00:00Z",
  "time_remaining_minutes": 15,
  "appeal_fee": 1000
}
```

**Success Response (200) - Not Eligible:**
```json
{
  "eligible": false,
  "reason": "Appeal window expired (30 minutes from score publication)",
  "score_time": "2025-01-01T00:00:00Z",
  "time_elapsed_minutes": 45
}
```

---

#### POST /kalamela/appeal/submit
**Description:** Submit appeal with ₹1000 payment

**Request Body:**
```json
{
  "participant_id": 1,
  "chest_number": "string",
  "event_name": "string",
  "statement": "string",  // min 10 chars
  "payment_type": "Appeal Fee"
}
```

**Success Response (200):**
```json
{
  "id": 1,
  "added_by_id": 1,
  "chest_number": "string",
  "event_name": "string",
  "statement": "string",
  "reply": null,
  "status": "Pending",
  "created_on": "2025-01-01T00:00:00Z"
}
```

---

#### GET /kalamela/appeals/status
**Description:** View appeal status with replies

**Query Parameters:**
- `participant_id`: integer (optional)
- `chest_number`: string (optional)
- At least one parameter required

**Success Response (200):**
```json
[
  {
    "id": 1,
    "chest_number": "string",
    "event_name": "string",
    "statement": "string",
    "reply": "string | null",
    "status": "Pending | Approved | Rejected",
    "created_on": "2025-01-01T00:00:00Z"
  }
]
```

---

### Official Routes (District Official Auth Required)

#### GET /kalamela/official/home
**Description:** Official home page with all events and participation counts

**Authentication:** Required (District Official)

**Success Response (200):**
```json
{
  "individual_events": [
    {
      "id": 1,
      "name": "string",
      "category": "string",
      "description": "string",
      "participant_count": 2,
      "remaining_slots": 1
    }
  ],
  "group_events": [
    {
      "id": 1,
      "name": "string",
      "description": "string",
      "max_allowed_limit": 15,
      "per_unit_allowed_limit": 15,
      "team_count": 2
    }
  ],
  "district_id": 1
}
```

---

#### POST /kalamela/official/events/individual/select
**Description:** Select individual event and show eligible members

**Authentication:** Required (District Official)

**Request Body:**
```json
{
  "event_id": 1,
  "unit_id": 1 | null  // optional unit filter
}
```

**Success Response (200):**
```json
{
  "event": {
    "id": 1,
    "name": "string",
    "category": "string",
    "description": "string"
  },
  "members": [
    {
      "id": 1,
      "name": "string",
      "gender": "M | F",
      "dob": "2000-01-01",
      "number": "string"
    }
  ],
  "units": [
    {
      "id": 1,
      "name": "string"
    }
  ]
}
```

---

#### POST /kalamela/official/events/individual/add
**Description:** Add participant to individual event

**Authentication:** Required (District Official)

**Request Body:**
```json
{
  "individual_event_id": 1,
  "participant_id": 1,
  "seniority_category": "NA | Junior | Senior"
}
```

**Success Response (200):**
```json
{
  "message": "Participant added successfully",
  "participation": {
    "id": 1,
    "individual_event_id": 1,
    "participant_id": 1,
    "added_by_id": 1,
    "chest_number": "string",
    "seniority_category": "NA",
    "created_on": "2025-01-01T00:00:00Z"
  }
}
```

---

#### GET /kalamela/official/participants/individual
**Description:** View all individual participants from district grouped by event

**Authentication:** Required (District Official)

**Success Response (200):**
```json
{
  "individual_event_participations": {
    "Event Name": [
      {
        "individual_event_participation_id": 1,
        "participant_id": 1,
        "participant_name": "string",
        "participant_unit": "string",
        "participant_district": "string",
        "participant_phone": "string",
        "participant_chest_number": "string",
        "participant_gender": "M | F"
      }
    ]
  }
}
```

---

#### DELETE /kalamela/official/participants/individual/{participation_id}
**Description:** Remove individual participant

**Authentication:** Required (District Official)

**Path Parameters:**
- `participation_id`: Participation ID (integer)

**Success Response (200):**
```json
{
  "message": "Participant removed successfully"
}
```

---

#### POST /kalamela/official/events/group/select
**Description:** Select group event and show eligible members

**Authentication:** Required (District Official)

**Request Body:**
```json
{
  "event_id": 1,
  "unit_id": 1 | null
}
```

**Success Response (200):**
```json
{
  "event": { ... },
  "members": [ ... ],
  "units": [ ... ],
  "current_team_size": 5,
  "remaining_slots": 10,
  "max_allowed_limit": 15
}
```

---

#### POST /kalamela/official/events/group/add
**Description:** Add multiple participants to group event (team formation)

**Authentication:** Required (District Official)

**Request Body:**
```json
{
  "group_event_id": 1,
  "participant_ids": [1, 2, 3, 4, 5]  // array of participant IDs
}
```

**Success Response (200):**
```json
{
  "message": "Added 5 participants successfully",
  "participations": [ ... ]
}
```

---

#### GET /kalamela/official/participants/group
**Description:** View all group participants from district grouped by event and team

**Authentication:** Required (District Official)

**Success Response (200):**
```json
{
  "group_event_participations": {
    "Event Name": {
      "TEAM001": [
        {
          "group_event_participation_id": 1,
          "participant_id": 1,
          "participant_name": "string",
          "participant_unit": "string",
          "participant_district": "string",
          "participant_phone": "string",
          "participant_chest_number": "TEAM001"
        }
      ]
    }
  }
}
```

---

#### DELETE /kalamela/official/participants/group/{participation_id}
**Description:** Remove group participant

**Authentication:** Required (District Official)

---

#### GET /kalamela/official/preview
**Description:** Preview all district participations with payment calculation

**Authentication:** Required (District Official)

**Success Response (200):**
```json
{
  "individual_events_count": 50,
  "group_events_count": 10,
  "individual_event_amount": 2500,
  "group_event_amount": 1000,
  "total_amount_to_pay": 3500,
  "payment_status": "Pending | Paid | null",
  "individual_event_participations": { ... },
  "group_event_participations": { ... }
}
```

---

#### POST /kalamela/official/payment
**Description:** Create payment record based on current participations

**Authentication:** Required (District Official)

**Success Response (200):**
```json
{
  "id": 1,
  "paid_by_id": 1,
  "individual_events_count": 50,
  "group_events_count": 10,
  "total_amount_to_pay": 3500,
  "payment_proof_path": null,
  "payment_status": "Pending",
  "created_on": "2025-01-01T00:00:00Z"
}
```

---

#### POST /kalamela/official/payment/{payment_id}/proof
**Description:** Upload payment proof

**Authentication:** Required (District Official)

**Path Parameters:**
- `payment_id`: Payment ID (integer)

**Request:** Form data with file upload

**Success Response (200):**
```json
{
  "id": 1,
  "paid_by_id": 1,
  "individual_events_count": 50,
  "group_events_count": 10,
  "total_amount_to_pay": 3500,
  "payment_proof_path": "path/to/proof.pdf",
  "payment_status": "Proof Uploaded",
  "created_on": "2025-01-01T00:00:00Z"
}
```

---

#### GET /kalamela/official/print
**Description:** Formatted view for printing district participation

**Authentication:** Required (District Official)

---

## 6. Admin Modules

### Admin Units (Admin Auth Required)

#### GET /admin/units/home
**Description:** Get admin dashboard statistics

**Authentication:** Required (Admin)

**Success Response (200):**
```json
{
  "total_dist_count": 12,
  "total_units_count": 150,
  "completed_dist_count": 10,
  "completed_units_count": 120,
  "completed_dists_percent": "83.33",
  "completed_units_percent": "80.00",
  "total_unit_members": 5000,
  "total_male_members": 2500,
  "total_female_members": 2500,
  "max_member_unit": "Unit Name",
  "max_member_unit_count": 75
}
```

---

#### GET /admin/units/all
**Description:** List all registered units

**Authentication:** Required (Admin)

**Success Response (200):**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "username": "string",
    "unit_name": "string",
    "status": "Registration Completed"
  }
]
```

---

#### GET /admin/units/{unit_id}
**Description:** View individual unit details

**Authentication:** Required (Admin)

**Path Parameters:**
- `unit_id`: Unit ID (integer)

**Success Response (200):**
```json
{
  "user": {
    "id": 1,
    "username": "string",
    "unit_name": "string"
  },
  "officials": { ... },
  "councilors": [ ... ],
  "members": [ ... ],
  "member_count": 50
}
```

---

#### GET /admin/units/transfer-requests
**Description:** List all transfer requests

**Authentication:** Required (Admin)

---

#### POST /admin/units/transfer-requests/{request_id}/approve
**Description:** Approve a transfer request

**Authentication:** Required (Admin)

---

#### POST /admin/units/transfer-requests/{request_id}/revert
**Description:** Revert a transfer request

**Authentication:** Required (Admin)

---

#### GET /admin/units/member-change-requests
**Description:** List all member change requests

**Authentication:** Required (Admin)

---

#### POST /admin/units/member-change-requests/{request_id}/approve
**Description:** Approve a member change request

**Authentication:** Required (Admin)

---

#### POST /admin/units/member-change-requests/{request_id}/revert
**Description:** Revert a member change request

**Authentication:** Required (Admin)

---

#### GET /admin/units/officials-change-requests
**Description:** List all officials change requests

**Authentication:** Required (Admin)

---

#### POST /admin/units/officials-change-requests/{request_id}/approve
**Description:** Approve an officials change request

**Authentication:** Required (Admin)

---

#### POST /admin/units/officials-change-requests/{request_id}/revert
**Description:** Revert an officials change request

**Authentication:** Required (Admin)

---

#### POST /admin/units/officials-change-requests/{request_id}/reject
**Description:** Reject an officials change request

**Authentication:** Required (Admin)

---

#### GET /admin/units/councilor-change-requests
**Description:** List all councilor change requests

**Authentication:** Required (Admin)

---

#### POST /admin/units/councilor-change-requests/{request_id}/approve
**Description:** Approve a councilor change request

**Authentication:** Required (Admin)

---

#### POST /admin/units/councilor-change-requests/{request_id}/revert
**Description:** Revert a councilor change request

**Authentication:** Required (Admin)

---

#### POST /admin/units/councilor-change-requests/{request_id}/reject
**Description:** Reject a councilor change request

**Authentication:** Required (Admin)

---

#### GET /admin/units/member-add-requests
**Description:** List all member add requests

**Authentication:** Required (Admin)

---

#### POST /admin/units/member-add-requests/{request_id}/approve
**Description:** Approve a member add request

**Authentication:** Required (Admin)

---

#### POST /admin/units/member-add-requests/{request_id}/reject
**Description:** Reject a member add request

**Authentication:** Required (Admin)

---

#### DELETE /admin/units/members/{member_id}
**Description:** Archive a unit member

**Authentication:** Required (Admin)

**Success Response (200):**
```json
{
  "message": "Member archived successfully"
}
```

---

#### POST /admin/units/reset-password
**Description:** Reset a user's password

**Authentication:** Required (Admin)

**Query Parameters:**
- `username`: string (required)
- `new_password`: string (required)

**Success Response (200):**
```json
{
  "message": "Password for user {username} reset successfully"
}
```

---

### Admin Conference (Admin Auth Required)

#### GET /admin/conference/home
**Description:** Get conference dashboard with list of conferences

**Authentication:** Required (Admin)

**Success Response (200):**
```json
[
  {
    "id": 1,
    "title": "string",
    "details": "string",
    "added_on": "2025-01-01T00:00:00Z",
    "status": "Active"
  }
]
```

---

#### POST /admin/conference
**Description:** Create a new conference

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "title": "string",
  "details": "string"
}
```

**Success Response (200):**
```json
{
  "id": 1,
  "title": "string",
  "details": "string",
  "added_on": "2025-01-01T00:00:00Z",
  "status": "Active"
}
```

---

#### PUT /admin/conference/{conference_id}
**Description:** Update a conference

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "title": "string | null",
  "details": "string | null",
  "status": "Active | Inactive | Completed | null"
}
```

---

#### DELETE /admin/conference/{conference_id}
**Description:** Delete a conference

**Authentication:** Required (Admin)

**Success Response (200):**
```json
{
  "message": "Conference deleted successfully"
}
```

---

#### GET /admin/conference/{conference_id}/info
**Description:** Get all conference information aggregated by district

**Authentication:** Required (Admin)

**Success Response (200):**
```json
{
  "conference_id": 1,
  "district_info": {
    "District Name": {
      "officials": [ ... ],
      "members": [ ... ],
      "count_of_members": 20,
      "count_of_officials": 5,
      "count_of_male_members": 10,
      "count_of_female_members": 10,
      "total_count": 25,
      "veg_count": 15,
      "non_veg_count": 10
    }
  }
}
```

---

#### GET /admin/conference/{conference_id}/payment-info
**Description:** Get payment information aggregated by district

**Authentication:** Required (Admin)

---

#### GET /admin/conference/officials
**Description:** List all district officials

**Authentication:** Required (Admin)

**Success Response (200):**
```json
[
  {
    "id": 1,
    "name": "string",
    "phone": "string",
    "district": "string",
    "conference_id": 1,
    "conference_official_count": 5,
    "conference_member_count": 25
  }
]
```

---

#### POST /admin/conference/officials
**Description:** Add a district official (create delegate account)

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "conference_id": 1,
  "member_id": 1  // unit member to be made official
}
```

**Success Response (200):**
```json
{
  "message": "District official added successfully",
  "official_id": 1,
  "username": "9876543210"
}
```

---

#### PUT /admin/conference/officials/{official_id}
**Description:** Update district official

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "conference_official_count": 5,
  "conference_member_count": 25
}
```

---

#### DELETE /admin/conference/officials/{official_id}
**Description:** Delete a district official

**Authentication:** Required (Admin)

---

#### GET /admin/conference/{conference_id}/districts/{district_id}/members
**Description:** View all members from a district for conference registration

**Authentication:** Required (Admin)

---

### Admin System (Admin Auth Required)

#### GET /admin/system/districts
**Description:** List all clergy districts

**Authentication:** Required (Admin)

**Success Response (200):**
```json
[
  {
    "id": 1,
    "name": "District Name"
  }
]
```

---

#### POST /admin/system/districts
**Description:** Create a new clergy district

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "name": "string"
}
```

**Success Response (200):**
```json
{
  "message": "District created successfully",
  "id": 1,
  "name": "string"
}
```

---

#### GET /admin/system/unit-names
**Description:** List all unit names

**Authentication:** Required (Admin)

**Query Parameters:**
- `district_id`: integer (optional)

**Success Response (200):**
```json
[
  {
    "id": 1,
    "name": "string",
    "clergy_district_id": 1,
    "district_name": "string"
  }
]
```

---

#### POST /admin/system/unit-names
**Description:** Create a new unit name

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "clergy_district_id": 1,
  "name": "string"
}
```

---

#### POST /admin/system/users
**Description:** Create a registered unit user

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "district_id": 1,
  "unit_name_id": 1,
  "phone_number": "string",
  "password": "string"
}
```

**Success Response (200):**
```json
{
  "message": "User registration successful",
  "user_id": 1,
  "registration_number": "MKDYM/DIS/001",
  "username": "MKDYM/DIS/001"
}
```

---

### Kalamela Admin (Admin Auth Required)

#### GET /kalamela/admin/home
**Description:** Admin dashboard with all events

**Authentication:** Required (Admin)

**Success Response (200):**
```json
{
  "individual_events": [ ... ],
  "group_events": [ ... ]
}
```

---

#### GET /kalamela/admin/units
**Description:** List all units with district information

**Authentication:** Required (Admin)

---

#### POST /kalamela/admin/units/{unit_id}/members
**Description:** View all members of a unit with ages

**Authentication:** Required (Admin)

---

#### PUT /kalamela/admin/members/{member_id}
**Description:** Edit unit member details

**Authentication:** Required (Admin)

**Query Parameters:**
- `name`: string (required)
- `gender`: string (optional)
- `dob`: date (optional)
- `number`: string (optional)
- `qualification`: string (optional)
- `blood_group`: string (optional)

---

#### POST /kalamela/admin/members/{member_id}/exclude
**Description:** Exclude a member from all events

**Authentication:** Required (Admin)

---

#### GET /kalamela/admin/excluded-members
**Description:** List all excluded members

**Authentication:** Required (Admin)

---

#### DELETE /kalamela/admin/excluded-members/{exclusion_id}
**Description:** Remove member from exclusion list

**Authentication:** Required (Admin)

---

#### POST /kalamela/admin/events/individual
**Description:** Create individual event

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "name": "string",
  "category": "string | null",
  "description": "string | null"
}
```

---

#### PUT /kalamela/admin/events/individual/{event_id}
**Description:** Update individual event

**Authentication:** Required (Admin)

---

#### POST /kalamela/admin/events/group
**Description:** Create group event

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "name": "string",
  "description": "string | null",
  "max_allowed_limit": 15,
  "min_allowed_limit": 5,
  "per_unit_allowed_limit": 15
}
```

---

#### PUT /kalamela/admin/events/group/{event_id}
**Description:** Update group event

**Authentication:** Required (Admin)

---

#### GET /kalamela/admin/participants/individual
**Description:** List all individual participants grouped by event

**Authentication:** Required (Admin)

---

#### GET /kalamela/admin/participants/group
**Description:** List all group participants grouped by event and team

**Authentication:** Required (Admin)

---

#### PUT /kalamela/admin/participants/group/{participation_id}/chest-number
**Description:** Update chest number for group participation

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "chest_number": "string"
}
```

---

#### GET /kalamela/admin/events/preview
**Description:** View events preview with participation counts and payment info

**Authentication:** Required (Admin)

**Query Parameters:**
- `district_id`: integer (optional)

---

#### GET /kalamela/admin/payments
**Description:** List all payments

**Authentication:** Required (Admin)

---

#### POST /kalamela/admin/payments/{payment_id}/approve
**Description:** Approve payment

**Authentication:** Required (Admin)

---

#### POST /kalamela/admin/payments/{payment_id}/decline
**Description:** Decline payment and clear proof

**Authentication:** Required (Admin)

---

#### POST /kalamela/admin/events/individual/candidates
**Description:** Get candidates for scoring by event name

**Authentication:** Required (Admin)

**Query Parameters:**
- `event_name`: string (required)

---

#### POST /kalamela/admin/scores/individual
**Description:** Bulk add individual scores

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "participants": [
    {
      "event_participation_id": 1,
      "awarded_mark": 85,
      "grade": "A",
      "total_points": 90
    }
  ]
}
```

---

#### POST /kalamela/admin/events/group/candidates
**Description:** Get team candidates for scoring by event name

**Authentication:** Required (Admin)

---

#### POST /kalamela/admin/scores/group
**Description:** Bulk add group scores

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "participants": [
    {
      "event_name": "string",
      "chest_number": "string",
      "awarded_mark": 85,
      "grade": "A",
      "total_points": 90
    }
  ]
}
```

---

#### GET /kalamela/admin/scores/individual
**Description:** View all individual scores grouped by event

**Authentication:** Required (Admin)

---

#### GET /kalamela/admin/scores/group
**Description:** View all group scores grouped by event

**Authentication:** Required (Admin)

---

#### POST /kalamela/admin/scores/individual/update
**Description:** Bulk update individual scores

**Authentication:** Required (Admin)

---

#### POST /kalamela/admin/scores/group/update
**Description:** Bulk update group scores

**Authentication:** Required (Admin)

---

#### POST /kalamela/admin/scores/individual/event
**Description:** Get all scores for a specific individual event for editing

**Authentication:** Required (Admin)

**Query Parameters:**
- `event_name`: string (required)

---

#### POST /kalamela/admin/scores/group/event
**Description:** Get all scores for a specific group event for editing

**Authentication:** Required (Admin)

---

#### GET /kalamela/admin/appeals
**Description:** List all appeals with payment status

**Authentication:** Required (Admin)

---

#### POST /kalamela/admin/appeals/{appeal_id}/reply
**Description:** Reply to appeal and approve it

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "reply": "string"
}
```

---

#### GET /kalamela/admin/results/unit-wise
**Description:** Get top 3 results per unit

**Authentication:** Required (Admin)

---

#### GET /kalamela/admin/results/district-wise
**Description:** Get top 3 results per district with aggregated points

**Authentication:** Required (Admin)

---

#### POST /kalamela/admin/export/events
**Description:** Export call sheet with full formatting (Excel download)

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "district_id": 1 | null,
  "individual_event_id": 1 | null,
  "group_event_id": 1 | null
}
```

**Success Response:** Excel file download

---

#### POST /kalamela/admin/export/chest-numbers
**Description:** Export all individual chest numbers (Excel download)

**Authentication:** Required (Admin)

**Success Response:** Excel file download

---

#### POST /kalamela/admin/export/results
**Description:** Export top 3 results for all events (Excel download)

**Authentication:** Required (Admin)

**Success Response:** Excel file download

---

## Common Error Responses

### 400 Bad Request
```json
{
  "detail": "Error message describing the validation error"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```
or
```json
{
  "detail": "Invalid credentials"
}
```

### 403 Forbidden
```json
{
  "detail": "Access denied. {Role} privileges required."
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 422 Unprocessable Entity (Validation Error)
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "Error message",
      "type": "error_type"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## User Types

| User Type | Value | Access Level |
|-----------|-------|--------------|
| Unit | `UNIT` | Unit registration and management |
| District Official | `DISTRICT_OFFICIAL` | Conference and Kalamela delegation |
| Admin | `ADMIN` | Full system access |

---

## Status Enums

### Registration Status
- `Registration Started`
- `Unit Details`
- `Unit Members Completed`
- `Unit Officials Completed`
- `Unit Councilors Completed`
- `Registration Completed`

### Request Status
- `PENDING`
- `APPROVED`
- `REJECTED`

### Payment Status (Kalamela)
- `Pending`
- `Proof Uploaded`
- `Paid`
- `Declined`

### Payment Status (Conference)
- `PAID`
- `NOT PAID`
- `PENDING`

### Appeal Status
- `Pending`
- `Approved`
- `Rejected`

### Conference Status
- `Active`
- `Inactive`
- `Completed`

### Seniority Category
- `NA`
- `Junior`
- `Senior`

---

## File Upload Guidelines

- Supported file extensions: `.pdf`, `.png`, `.jpg`, `.jpeg`
- Maximum file size: Check server configuration
- Files are uploaded as multipart/form-data for payment proof uploads
- For change requests, provide the file path string in the request body

---

## Notes for Frontend Development

1. **Token Management**: Store tokens securely and include them in the Authorization header for authenticated requests.

2. **Error Handling**: Always handle the common error responses appropriately in your UI.

3. **Date Formats**: All dates should be in `YYYY-MM-DD` format for requests and ISO 8601 format in responses.

4. **Pagination**: Currently not implemented in most list endpoints. Consider implementing client-side pagination.

5. **Real-time Updates**: For features like appeal window timing, implement countdown timers on the client side.

6. **File Uploads**: Use multipart/form-data for file upload endpoints.

7. **User Routing**: After login, route users based on their `user_type`:
   - `UNIT` → Unit management pages
   - `DISTRICT_OFFICIAL` → Conference/Kalamela official pages
   - `ADMIN` → Admin dashboard


