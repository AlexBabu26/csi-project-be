# CSI Kalamela FastAPI Backend

A FastAPI-based backend application for the CSI Madhya Kerala Diocese Youth Movement management system. This application handles unit management, member registration, Kalamela (cultural festival) events, and conference management.

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 14+ (or Neon serverless PostgreSQL)
- pip or uv package manager

### Installation

1. **Clone the repository**
   ```bash
   cd /path/to/csi_kalamela_fastapi
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # OR
   .venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   # OR using uv (faster)
   uv pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```env
   # Database Configuration
   DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/csi_kalamela
   
   # Security
   SECRET_KEY=your-super-secret-key-change-in-production
   DEBUG=true
   
   # JWT Token Settings
   ACCESS_TOKEN_EXPIRE_MINUTES=15
   REFRESH_TOKEN_EXPIRE_DAYS=7
   
   # Backblaze B2 Storage (for file uploads)
   B2_ENDPOINT=https://s3.eu-central-003.backblazeb2.com
   B2_BUCKET_NAME=csi-youthmovement
   B2_KEY_ID=your-b2-key-id
   B2_APPLICATION_KEY=your-b2-application-key
   B2_REGION=eu-central-003
   ```

5. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

6. **Start the development server**
   ```bash
   # Option 1: Using uvicorn directly
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   
   # Option 2: Using Python
   python main.py
   ```

   The API will be available at:
   - **API Base URL**: http://localhost:8000
   - **Swagger Docs**: http://localhost:8000/docs
   - **ReDoc**: http://localhost:8000/redoc

---

## 📁 Project Structure

```
csi_kalamela_fastapi/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── alembic.ini            # Alembic configuration
├── alembic/               # Database migrations
│   └── versions/          # Migration scripts
├── app/
│   ├── admin/             # Admin module
│   │   ├── routers/
│   │   │   ├── conference.py  # Conference admin endpoints
│   │   │   ├── site.py        # Site settings endpoints
│   │   │   ├── system.py      # System/district data endpoints
│   │   │   └── units.py       # Unit management endpoints
│   │   ├── models.py
│   │   └── schemas.py
│   ├── auth/              # Authentication module
│   │   ├── router.py      # Login, register, token refresh
│   │   ├── models.py      # CustomUser, RefreshToken
│   │   ├── schemas.py
│   │   └── service.py
│   ├── common/            # Shared utilities
│   │   ├── cache.py       # In-memory caching decorator
│   │   ├── config.py      # Settings/environment config
│   │   ├── db.py          # Database engine & sessions
│   │   ├── exporter.py    # Excel export utilities
│   │   ├── security.py    # JWT & password utilities
│   │   └── storage.py     # B2 file storage
│   ├── conference/        # Conference module
│   │   ├── routers/
│   │   │   ├── official.py    # District official endpoints
│   │   │   └── public.py      # Public conference endpoints
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── service.py
│   ├── kalamela/          # Kalamela (cultural events) module
│   │   ├── routers/
│   │   │   ├── admin.py       # Event management, scoring
│   │   │   ├── official.py    # Unit registration
│   │   │   └── public.py      # Public results
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── service.py
│   └── units/             # Unit management module
│       ├── routers/
│       │   └── user.py        # Unit user endpoints
│       ├── models.py
│       ├── schemas.py
│       └── service.py
└── tests/                 # Test files
```

---

## 🔐 Authentication

The API uses JWT (JSON Web Tokens) with a refresh token mechanism:

- **Access Token**: Short-lived (15 minutes), used for API requests
- **Refresh Token**: Long-lived (7 days), used to obtain new access tokens

### User Types

| Type | Value | Description |
|------|-------|-------------|
| Admin | `ADMIN` | Full system access |
| Unit Official | `UNIT` | Unit-level management |
| District Official | `DISTRICT_OFFICIAL` | Conference/district management |

### Login Endpoints

| Module | Endpoint | Description |
|--------|----------|-------------|
| Admin/Unit | `POST /api/auth/login` | General login |
| Kalamela | `POST /api/kalamela/official/login` | Kalamela official login |
| Conference | `POST /api/conference/official/login` | District official login |

---

## 📡 API Endpoints Overview

### Health Check
```
GET /api/health
```

### Authentication (`/api/auth`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/login` | User login |
| POST | `/refresh` | Refresh access token |
| POST | `/logout` | Logout (invalidate refresh token) |
| GET | `/me` | Get current user info |

### Admin - Units (`/api/admin/units`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/home` or `/dashboard` | Admin dashboard stats |
| GET | `/` or `/all` | List all units |
| GET | `/officials` | List all unit officials |
| GET | `/councilors` | List all unit councilors |
| GET | `/members` | List all members |
| GET | `/archived-members` | List archived members |
| GET | `/{unit_id}` | View unit details |
| GET | `/transfer-requests` | List transfer requests |
| PUT | `/transfer-requests/{id}/approve` | Approve transfer |
| PUT | `/transfer-requests/{id}/revert` | Revert transfer |
| PUT | `/transfer-requests/{id}/reject` | Reject transfer |
| GET | `/member-change-requests` | List member info changes |
| PUT | `/member-change-requests/{id}/approve` | Approve change |
| PUT | `/member-change-requests/{id}/revert` | Revert change |
| PUT | `/member-change-requests/{id}/reject` | Reject change |

### Admin - System (`/api/admin/system` or `/api/system`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/districts` | List all clergy districts |
| GET | `/district-wise-data` | District statistics |

### Conference - Official (`/api/conference/official`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/login` | District official login |
| GET | `/view` | View conference details |
| GET | `/delegates` | List delegates |
| POST | `/delegates/{member_id}` | Register delegate |
| DELETE | `/delegates/{delegate_id}` | Remove delegate |
| POST | `/payment` | Create payment |
| POST | `/payment/{payment_id}/proof` | Upload payment proof |

### Kalamela - Admin (`/api/kalamela/admin`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/home` | Admin dashboard |
| GET | `/events` | List events |
| POST | `/events` | Create event |
| GET | `/scores/individual/event/{id}/candidates` | Get candidates for scoring |
| POST | `/scores/individual` | Submit individual scores |
| POST | `/scores/group` | Submit group scores |

### Kalamela - Official (`/api/kalamela/official`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/login` | Unit official login |
| GET | `/home` | Registration dashboard |
| POST | `/register` | Register participants |
| GET | `/preview` | Preview registration |

### Kalamela - Public (`/api/kalamela`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/results` | Public results |
| GET | `/top-performers` | Top performers list |

---

## 🗄️ Database

### Supported Databases

- **PostgreSQL** (recommended for production)
- **Neon Serverless PostgreSQL** (recommended for Vercel deployment)

### Connection String Format

```
# Local PostgreSQL
postgresql+psycopg://user:password@localhost:5432/database_name

# Neon Pooled Connection (recommended for serverless)
postgresql+psycopg://user:password@ep-xxx-pooler.region.aws.neon.tech/database_name?sslmode=require
```

### Running Migrations

```bash
# Apply all migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Rollback one migration
alembic downgrade -1
```

---

## ⚡ Performance Optimizations

The application includes several performance optimizations:

### 1. Connection Pooling
- Pool size: 5 connections
- Max overflow: 10 connections
- Pool recycle: 300 seconds

### 2. Response Caching
- Dashboard endpoints cached for 5 minutes
- Use `?refresh=true` to force cache refresh

### 3. Eager Loading
- Relationships loaded efficiently to prevent N+1 queries
- Uses `selectinload` and `joinedload` strategies

### 4. Pagination
- Default page size: 50 records
- All list endpoints support `page` and `page_size` parameters

### 5. Database Indexes
- Indexes on frequently queried columns
- Composite indexes for common query patterns

---

## 🚢 Deployment

### Vercel Deployment

The application is configured for Vercel serverless deployment.

1. **vercel.json** configuration is included
2. Use Neon pooled connection for database
3. Set environment variables in Vercel dashboard

### Environment Variables for Production

```env
DATABASE_URL=postgresql+psycopg://user:pass@ep-xxx-pooler.region.aws.neon.tech/db?sslmode=require
SECRET_KEY=your-production-secret-key
DEBUG=false
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
B2_KEY_ID=your-b2-key-id
B2_APPLICATION_KEY=your-b2-application-key
```

---

## 🔧 Development

### Running Tests

```bash
pytest tests/
```

### Code Style

The project follows PEP 8 style guidelines.

### Adding New Modules

1. Create module directory under `app/`
2. Add `models.py`, `schemas.py`, `service.py`
3. Create routers in `routers/` subdirectory
4. Register router in `main.py`
5. Create database migration if needed

---

## 📝 API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🔄 Password Compatibility

The application supports both:
- **Django's pbkdf2_sha256** hashes (for migrated users)
- **bcrypt** hashes (for new users)

This allows seamless migration from the original Django application.

---

## 📞 Frontend Integration

### CORS Configuration

Allowed origins:
- `http://localhost:3000` (local development)
- `http://127.0.0.1:3000` (local development)
- `https://csi-webapp-fe.vercel.app` (production frontend)

### Frontend Repository

The React frontend is located at:
```
/csi_frontend/csi-webapp-fe/
```

---

## 📋 Changelog

### Latest Updates

- **Conference Module**: Full CRUD for delegates, payments, and district officials
- **Performance**: Added connection pooling, caching, and pagination
- **Authentication**: JWT with refresh token support
- **Password Migration**: Support for Django pbkdf2_sha256 hashes
- **API Aliases**: Added route aliases for frontend compatibility
- **Error Handling**: Improved validation and error messages

---

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Run tests
4. Submit a pull request

---

## 📄 License

This project is proprietary software for CSI Madhya Kerala Diocese Youth Movement.

