# Complete API Documentation - CSI KalaMela FastAPI

**Base URL (Local):** `http://localhost:8000` or `http://0.0.0.0:8000`  
**Base URL (Production):** `https://csi-project-be.vercel.app`

---

## 🔐 Authentication

All protected endpoints require a Bearer token in the Authorization header:
```bash
Authorization: Bearer {access_token}
```

Get token by logging in via `/auth/login`

---

## 📋 Complete API Endpoints

### **1. System Endpoints**

#### Health Check
```http
GET /health
```
**Authorization:** None  
**Response:**
```json
{"status": "ok"}
```

---

### **2. Auth Module (`/auth`)**

#### Login
```http
POST /auth/login
```
**Authorization:** None  
**Payload:**
```json
{
  "username": "admin",
  "password": "admin"
}
```
**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Get Current User
```http
GET /auth/me
```
**Authorization:** Required  
**Response:**
```json
{
  "id": 1,
  "email": "admin@test.com",
  "username": "admin",
  "first_name": "Admin",
  "last_name": "User",
  "phone_number": "1234567890",
  "user_type": "1",
  "unit_name_id": null,
  "clergy_district_id": null,
  "is_active": true
}
```

#### Register Unit
```http
POST /auth/register-unit
```
**Authorization:** None  
**Payload:**
```json
{
  "email": "newunit@test.com",
  "phone_number": "9999999999",
  "first_name": "New",
  "last_name": "Unit",
  "unit_name_id": 1,
  "clergy_district_id": 1,
  "password": "password123"
}
```
**Response:** User object (UserType=UNIT/2)

#### Get Unit Names
```http
GET /auth/unit-names
GET /auth/unit-names?district_id=1
```
**Authorization:** None  
**Query Params:**
- `district_id` (optional): Filter by clergy district
**Response:**
```json
[
  {
    "id": 1,
    "clergy_district_id": 1,
    "name": "Test Unit"
  }
]
```

---

### **3. Admin Module (`/admin`)**

**Required Role:** Admin (1)

#### Dashboard
```http
GET /admin/dashboard
```
**Authorization:** Admin  
**Response:**
```json
{
  "users": 4,
  "units": 2,
  "members": 1,
  "individual_participations": 1,
  "group_participations": 1,
  "payments": 1
}
```

#### Export Users
```http
GET /admin/exports/users
```
**Authorization:** Admin  
**Response:** Excel file download (`users.xlsx`)

#### District Statistics (All)
```http
GET /admin/statistics/districts
```
**Authorization:** Admin  
**Response:**
```json
[
  {
    "district_id": 1,
    "district_name": "Test District",
    "units": 2,
    "members": 1,
    "individual_participations": 1,
    "group_participations": 1,
    "payments": 1,
    "total_payment_amount": 200
  }
]
```

#### District Statistics (Single)
```http
GET /admin/statistics/districts/{district_id}
```
**Authorization:** Admin  
**Path Params:**
- `district_id`: District ID
**Response:** Single district statistics object

---

### **4. Conference Module (`/conference`)**

#### List Conferences
```http
GET /conference/
```
**Authorization:** Admin(1) or Official(3)  
**Response:**
```json
[
  {
    "id": 1,
    "title": "Test Conference",
    "details": "This is a test conference",
    "status": "active",
    "created_on": "2025-12-07T17:24:16.992758"
  }
]
```

#### Create Conference
```http
POST /conference/
```
**Authorization:** Admin(1)  
**Payload:**
```json
{
  "title": "Test Conference",
  "details": "This is a test conference"
}
```
**Response:** Conference object

#### Add Delegate
```http
POST /conference/delegate
```
**Authorization:** Admin(1) or Official(3)  
**Payload:**
```json
{
  "conference_id": 1,
  "official_user_id": 3,
  "member_id": 1
}
```
**Response:**
```json
{"status": "ok"}
```

#### Create Conference Payment
```http
POST /conference/payment
```
**Authorization:** Admin(1) or Official(3)  
**Payload:**
```json
{
  "conference_id": 1,
  "amount_to_pay": 500,
  "payment_reference": "REF123"
}
```
**Response:**
```json
{
  "id": 1,
  "conference_id": 1,
  "amount_to_pay": 500,
  "status": "Pending",
  "proof_path": null,
  "date": "2025-12-07T17:26:41.373819"
}
```

#### Upload Payment Proof
```http
POST /conference/payment/{payment_id}/proof
```
**Authorization:** Admin(1) or Official(3)  
**Content-Type:** multipart/form-data  
**Form Data:**
- `file`: Payment proof image/PDF

#### Update Payment Status
```http
POST /conference/payment/{payment_id}/status?status_value={status}
```
**Authorization:** Admin(1)  
**Query Params:**
- `status_value`: `Pending` | `Proof Uploaded` | `Paid` | `Declined`
**Response:** Updated payment object

---

### **5. Kalamela Public Module (`/kalamela`)**

**No authentication required**

#### List Individual Events
```http
GET /kalamela/events/individual
```
**Response:**
```json
[
  {
    "id": 1,
    "name": "Singing",
    "category": "Arts",
    "description": "Individual singing competition",
    "created_on": "2025-12-07T17:24:33.314250"
  }
]
```

#### List Group Events
```http
GET /kalamela/events/group
```
**Response:**
```json
[
  {
    "id": 1,
    "name": "Group Dance",
    "description": "Group dance competition",
    "max_allowed_limit": 10,
    "min_allowed_limit": 5,
    "per_unit_allowed_limit": 2,
    "created_on": "2025-12-07T17:24:42.191462"
  }
]
```

#### Get Individual Event Details
```http
GET /kalamela/events/individual/{event_id}
```
**Response:**
```json
{
  "event": {
    "id": 1,
    "name": "Singing",
    "category": "Arts",
    "description": "Individual singing competition",
    "created_on": "2025-12-07T17:24:33.314250"
  },
  "participations_count": 1,
  "participations": [
    {
      "id": 1,
      "individual_event_id": 1,
      "participant_id": 1,
      "added_by_id": 2,
      "chest_number": "S001-01-001",
      "seniority_category": "Senior",
      "created_on": "2025-12-07T17:25:36.213266"
    }
  ]
}
```

#### Get Group Event Details
```http
GET /kalamela/events/group/{event_id}
```
**Response:** Similar structure with group event data

#### List Individual Participations
```http
GET /kalamela/participations/individual
GET /kalamela/participations/individual?event_id=1
GET /kalamela/participations/individual?district_id=1
GET /kalamela/participations/individual?event_id=1&district_id=1
```
**Query Params:**
- `event_id` (optional): Filter by event
- `district_id` (optional): Filter by district
**Response:**
```json
[
  {
    "id": 1,
    "individual_event_id": 1,
    "participant_id": 1,
    "added_by_id": 2,
    "chest_number": "S001-01-001",
    "seniority_category": "Senior",
    "created_on": "2025-12-07T17:25:36.213266"
  }
]
```

#### List Group Participations
```http
GET /kalamela/participations/group
GET /kalamela/participations/group?event_id=1
GET /kalamela/participations/group?district_id=1
```
**Query Params:**
- `event_id` (optional): Filter by event
- `district_id` (optional): Filter by district
**Response:** Array of group participation objects

#### Individual Results
```http
GET /kalamela/results/individual
```
**Response:**
```json
[
  {
    "id": 1,
    "participant_id": 1,
    "event_participation_id": 1,
    "awarded_mark": 95,
    "grade": "A",
    "total_points": 95,
    "added_on": "2025-12-07T17:25:57.715052"
  }
]
```

#### Group Results
```http
GET /kalamela/results/group
```
**Response:**
```json
[
  {
    "id": 1,
    "event_name": "Group Dance",
    "chest_number": "GD001-01-001",
    "awarded_mark": 88,
    "grade": "B+",
    "total_points": 88,
    "added_on": "2025-12-07T17:27:07.975146"
  }
]
```

#### Submit Appeal
```http
POST /kalamela/appeals
```
**Payload:**
```json
{
  "participant_id": 1,
  "chest_number": "S001-01-001",
  "event_name": "Singing",
  "statement": "I believe my performance deserves reconsideration"
}
```
**Response:**
```json
{
  "id": 1,
  "added_by_id": 1,
  "chest_number": "S001-01-001",
  "event_name": "Singing",
  "statement": "I believe my performance deserves reconsideration",
  "status": "Pending",
  "created_on": "2025-12-07T17:26:47.078527"
}
```

---

### **6. Kalamela Official Module (`/kalamela/official`)**

**Required Role:** Unit(2) or Official(3)

#### Add Individual Participation
```http
POST /kalamela/official/individual-participations
```
**Authorization:** Unit(2) or Official(3)  
**Payload:**
```json
{
  "individual_event_id": 1,
  "participant_id": 1,
  "seniority_category": "Senior"
}
```
**Response:**
```json
{
  "id": 1,
  "individual_event_id": 1,
  "participant_id": 1,
  "added_by_id": 2,
  "chest_number": "S001-01-001",
  "seniority_category": "Senior",
  "created_on": "2025-12-07T17:25:36.213266"
}
```

#### Add Group Participation
```http
POST /kalamela/official/group-participations
```
**Authorization:** Unit(2) or Official(3)  
**Payload:**
```json
{
  "group_event_id": 1,
  "participant_id": 1
}
```
**Response:**
```json
{
  "id": 1,
  "group_event_id": 1,
  "participant_id": 1,
  "added_by_id": 2,
  "chest_number": "GD001-01-001"
}
```

#### Create Payment
```http
POST /kalamela/official/payments
```
**Authorization:** Unit(2) or Official(3)  
**Payload:**
```json
{
  "individual_events_count": 2,
  "group_events_count": 1
}
```
**Response:**
```json
{
  "id": 1,
  "paid_by_id": 2,
  "individual_events_count": 2,
  "group_events_count": 1,
  "total_amount_to_pay": 200,
  "payment_proof_path": null,
  "payment_status": "Pending",
  "created_on": "2025-12-07T17:26:22.520231"
}
```
*Note: Fee = (individual × ₹50) + (group × ₹100)*

#### Upload Payment Proof
```http
POST /kalamela/official/payments/{payment_id}/proof
```
**Authorization:** Unit(2) or Official(3)  
**Content-Type:** multipart/form-data  
**Form Data:**
- `file`: Payment proof image/PDF

---

### **7. Kalamela Admin Module (`/kalamela/admin`)**

**Required Role:** Admin(1)

#### Create Individual Event
```http
POST /kalamela/admin/events/individual
```
**Authorization:** Admin(1)  
**Payload:**
```json
{
  "name": "Singing",
  "category": "Arts",
  "description": "Individual singing competition"
}
```
**Response:** Event object with ID

#### Create Group Event
```http
POST /kalamela/admin/events/group
```
**Authorization:** Admin(1)  
**Payload:**
```json
{
  "name": "Group Dance",
  "description": "Group dance competition",
  "max_allowed_limit": 10,
  "min_allowed_limit": 5,
  "per_unit_allowed_limit": 2
}
```
**Response:** Event object with ID

#### Add Individual Score
```http
POST /kalamela/admin/scores/individual
```
**Authorization:** Admin(1)  
**Payload:**
```json
{
  "participation_id": 1,
  "awarded_mark": 95,
  "grade": "A",
  "total_points": 95
}
```
**Response:**
```json
{
  "id": 1,
  "event_participation_id": 1,
  "participant_id": 1,
  "awarded_mark": 95,
  "grade": "A",
  "total_points": 95,
  "added_on": "2025-12-07T17:25:57.715052"
}
```

#### Add Group Score
```http
POST /kalamela/admin/scores/group
```
**Authorization:** Admin(1)  
**Payload:**
```json
{
  "event_name": "Group Dance",
  "chest_number": "GD001-01-001",
  "awarded_mark": 88,
  "grade": "B+",
  "total_points": 88
}
```
**Response:** Score object with ID

#### Update Payment Status
```http
POST /kalamela/admin/payments/{payment_id}/status?status_value={status}
```
**Authorization:** Admin(1)  
**Query Params:**
- `status_value`: `Paid` | `Declined`
**Response:** Updated payment object

---

## 📊 Summary of New Endpoints

### ✅ **Listing Registrations/Participants**
1. `GET /kalamela/participations/individual` - List all individual participations with filters
2. `GET /kalamela/participations/group` - List all group participations with filters

### ✅ **Getting Event Details**
3. `GET /kalamela/events/individual` - List all individual events
4. `GET /kalamela/events/group` - List all group events
5. `GET /kalamela/events/individual/{event_id}` - Get event with participations
6. `GET /kalamela/events/group/{event_id}` - Get event with participations

### ✅ **Fetching Scores for Events**
7. `GET /kalamela/results/individual` - Already existed (top 3)
8. `GET /kalamela/results/group` - Already existed (top 3)

### ✅ **District Participation Statistics**
9. `GET /admin/statistics/districts` - All districts statistics
10. `GET /admin/statistics/districts/{district_id}` - Single district statistics

---

## 🧪 Testing Examples

### Get all events
```bash
curl http://localhost:8000/kalamela/events/individual
curl http://localhost:8000/kalamela/events/group
```

### Get participations with filters
```bash
# All individual participations
curl http://localhost:8000/kalamela/participations/individual

# Filter by event
curl "http://localhost:8000/kalamela/participations/individual?event_id=1"

# Filter by district
curl "http://localhost:8000/kalamela/participations/individual?district_id=1"

# Both filters
curl "http://localhost:8000/kalamela/participations/individual?event_id=1&district_id=1"
```

### Get district statistics (requires admin token)
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# All districts
curl -s http://localhost:8000/admin/statistics/districts \
  -H "Authorization: Bearer $TOKEN"

# Single district
curl -s http://localhost:8000/admin/statistics/districts/1 \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🔑 Test Credentials

- **Admin:** username=`admin`, password=`admin` (role 1)
- **Unit:** username=`unit`, password=`unit` (role 2)
- **Official:** username=`official`, password=`official` (role 3)

---

**Total Endpoints:** 36 (26 original + 10 new)  
**All endpoints tested and working** ✅


