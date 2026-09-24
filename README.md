# MHT-CET Engineering CAP Cutoff Admin Portal

An internal administration portal for managing, processing, validating, analyzing, and maintaining MHT-CET Engineering CAP cutoff data for Maharashtra.

## Overview

This application is an **admin-only** portal designed for a single authorized administrator to:

- Upload MHT-CET Engineering CAP cutoff PDFs (Rounds I–IV)
- Extract and parse college, course, seat section, category, stage, merit number, and percentile data
- Import parsed data into PostgreSQL with full validation
- Review parsing errors and manage manual corrections
- Browse, filter, and export cutoff records
- Compare data across CAP rounds
- Monitor data quality and system health

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic |
| **Frontend** | React 18, TypeScript, Tailwind CSS, Vite |
| **Database** | PostgreSQL 16 |
| **PDF Parsing** | PyMuPDF (pymupdf) |
| **Auth** | JWT (HTTP-only cookies), bcrypt |
| **Containerization** | Docker, Docker Compose |
| **Production Server** | Uvicorn (4 workers), nginx |

## Architecture

```
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/                # 11 API routers (40+ endpoints)
│   │   ├── auth/               # JWT auth, admin seeding, rate limiting
│   │   ├── middleware/         # Security headers
│   │   ├── models/             # 11 SQLAlchemy models
│   │   ├── parser/             # 13 PDF parser modules
│   │   ├── schemas/            # Pydantic request/response models
│   │   └── services/           # Business logic (import, audit)
│   ├── alembic/                # Database migrations
│   └── tests/                  # Unit tests (70+)
├── frontend/                   # React SPA
│   ├── src/
│   │   ├── api/                # API client functions
│   │   ├── components/         # Reusable UI components
│   │   ├── context/            # Auth context
│   │   ├── layouts/            # Admin layout, sidebar
│   │   ├── pages/              # 14 page components
│   │   └── types/              # TypeScript type definitions
│   └── nginx.conf              # Production nginx config
├── docker-compose.yml          # Development compose
├── docker-compose.prod.yml     # Production compose
└── .env.example                # Environment template
```

## Quick Start (Development)

### Prerequisites

- Docker & Docker Compose
- Git

### 1. Clone and configure

```bash
git clone <repository-url>
cd cap-allotment-portal
cp .env.example .env
# Edit .env — change SECRET_KEY to a random 64+ char string
```

### 2. Start services

```bash
docker compose up -d
```

### 3. Run database migration

```bash
docker exec cap_backend alembic upgrade head
```

### 4. Access the portal

- **Frontend**: http://localhost:5173
- **Backend API docs**: http://localhost:8000/api/docs
- **Login**: username `admin`, password `admin123`

## Production Deployment

### 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with production values:

```env
APP_ENV=production
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(64))">
DATABASE_URL=postgresql://user:password@host:5432/dbname
CORS_ORIGINS=https://your-domain.com
ADMIN_PASSWORD_HASH=<generate with: python -c "from passlib.hash import bcrypt; print(bcrypt.hash('your_password'))">
```

### 2. Deploy

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker exec cap_backend alembic upgrade head
```

### 3. Access

- **Portal**: http://your-server (port 80)
- API docs are **disabled** in production

## Database Schema

11 tables with full referential integrity:

| Table | Description |
|-------|-------------|
| `admin_users` | Single admin user with bcrypt password |
| `colleges` | College metadata (code, name, city, type) |
| `courses` | Course metadata linked to colleges |
| `cap_rounds` | CAP round tracking (year, round 1-4) |
| `cutoffs` | Production cutoff records (categories as rows) |
| `staging_cutoffs` | Temporary staging during import |
| `import_batches` | Import job tracking |
| `import_logs` | Per-import log entries |
| `parser_errors` | PDF parsing errors |
| `manual_corrections` | Audit trail for manual edits |
| `audit_logs` | System-wide audit trail |

### Key Design Decisions

- **Percentile stored as `NUMERIC(10,7)`** — never float, preserves 7 decimal places
- **Categories stored as rows** — not columns — for flexibility
- **Soft delete** on cutoff records — `is_deleted` flag, never hard delete
- **Staging workflow** — PDF data goes to staging first, admin reviews, then commits to production

## API Endpoints (40+)

| Group | Endpoints | Description |
|-------|-----------|-------------|
| Auth | 3 | Login, logout, current user |
| Dashboard | 1 | Aggregate statistics |
| Imports | 7 | Upload, process, preview, commit, delete |
| CAP Rounds | 4 | List, detail, stats, update |
| Colleges | 4 | CRUD with search and filtering |
| Courses | 3 | CRUD with college association |
| Cutoffs | 6 | List, detail, update, delete, restore, CSV export |
| Analysis | 3 | Round comparison, data quality, category summary |
| Parser Errors | 4 | List, detail, update status, summary |
| Audit Logs | 1 | Paginated audit trail |
| Settings | 1 | System info and stats |
| Health | 1 | Health check |

## PDF Parser

The parser handles the **vertical layout** found in MHT-CET CAP cutoff PDFs:

```
01002 - Government College of Engineering, Amravati     ← College (5-digit code)
0100219110 - Civil Engineering                          ← Course (10-digit code)
State Level                                             ← Seat section
GOPENS                                                  ← Categories (one per line)
GSCS
GSTS
  I                                                     ← Stage (Roman numeral)
34692                                                   ← Merit number
(91.7858261)                                            ← Percentile
59898                                                   ← Next category's data
(85.6921506)
Stage                                                   ← End marker
```

### Parser Modules

| Module | Responsibility |
|--------|---------------|
| `pdf_loader.py` | PyMuPDF text extraction |
| `college_parser.py` | 5-digit college code detection |
| `course_parser.py` | 10-digit course code detection |
| `section_parser.py` | Seat section classification |
| `category_parser.py` | Category code detection |
| `cutoff_parser.py` | Vertical block state machine |
| `normalizer.py` | Category → gender/category/location |
| `validator.py` | Record validation + dedup |
| `importer.py` | Orchestrator with DB insertion |
| `state_machine.py` | Parser state management |
| `patterns.py` | Compiled regex patterns |

### Validated Performance

Tested against actual 1,580-page CAP Round I PDF:
- **4,775 records** extracted from first 200 pages
- **51 colleges**, **288 courses** detected
- Exact match verification on known values

## Security

- JWT stored in HTTP-only, SameSite cookies
- bcrypt password hashing (never stored in plaintext)
- Rate limiting on login (5 attempts / 15 min lockout)
- Security headers (X-Frame-Options, CSP, HSTS, etc.)
- API docs disabled in production
- Non-root Docker containers
- CORS restricted to configured origins

## Testing

```bash
# Run parser unit tests (no DB needed)
cd backend
python -m pytest tests/parser/ -v --noconftest
```

70+ tests covering all parser modules.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `ADMIN_USERNAME` | `admin` | Admin login username |
| `ADMIN_EMAIL` | — | Admin email |
| `ADMIN_PASSWORD_HASH` | — | bcrypt hash of admin password |
| `SECRET_KEY` | — | JWT signing secret (min 32 chars) |
| `JWT_EXPIRY_HOURS` | `8` | JWT token lifetime |
| `APP_ENV` | `development` | `development` or `production` |
| `APP_VERSION` | `1.0.0` | Application version |
| `PARSER_VERSION` | `1.0.0` | Parser version tag |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |
| `UPLOAD_DIRECTORY` | `/storage/uploads` | PDF upload storage path |
| `MAX_UPLOAD_SIZE_MB` | `500` | Maximum upload file size |
| `LOGIN_MAX_ATTEMPTS` | `5` | Login attempts before lockout |
| `LOGIN_LOCKOUT_MINUTES` | `15` | Lockout duration |

## License

Internal use only. Not for public distribution.
