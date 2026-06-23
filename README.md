# Invoice Generator + RBAC Role Assignment App

This is a full starter project for your invoice generator and role/module access application.

## Modules included

- Home dashboard
- Users and role assignment
- Clients
- Bank details for Indian and foreign accounts
- Invoice generator
- Access requests for module access
- Finance and HR role-ready RBAC foundation

## Access rules implemented

- Superadmin can do everything.
- Admin can CRUD users, clients, banks, invoices, and access requests, but cannot modify/delete the superadmin.
- Finance has default read/create access for invoices and read access for clients/banks.
- HR can create access requests and has default read access to HR/home/clients/access requests.
- Bank manager role can CRUD bank details.
- Every API except `/auth/login` and `/health` is JWT protected.

## Tech stack

### Backend

- FastAPI
- PostgreSQL
- SQLAlchemy 2
- Alembic
- JWT auth
- Argon2 password hashing
- Pydantic schemas
- Pytest tests
- `.env` based config

### Frontend

- React
- Material UI
- Axios
- CSS Grid / Flexbox responsive layout
- Black and white theme
- Cards, table layout, border radius, box shadows, backdrop blur

## Folder structure

```text
invoice_rbac_app/
  backend/
    app/
      api/
      core/
      db/
      models/
      schemas/
      services/
      tests/
    alembic/
    requirements.txt
    .env.example
  frontend/
    src/
    package.json
    .env.example
  sql/
    00_create_database.sql
    01_after_migrations_note.sql
  docker-compose.yml
```

## Local setup

### 1. Start PostgreSQL

From project root:

```bash
docker compose up -d
```

Alternative: run `sql/00_create_database.sql` manually in PostgreSQL.

### 2. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # Windows: copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Backend will run at:

```text
http://localhost:8000
```

API docs:

```text
http://localhost:8000/docs
```

Default superadmin:

```text
Email: superadmin@example.com
Password: Mahakal@777
```

The app automatically seeds:

- modules
- admin/finance/hr/bank_manager roles
- default module permissions
- superadmin user

### 3. Frontend setup

Open a new terminal:

```bash
cd frontend
npm install
cp .env.example .env          # Windows: copy .env.example .env
npm run dev
```

Frontend will run at:

```text
http://localhost:5173
```

## Run tests

Make sure PostgreSQL is running and migrations are applied.

```bash
cd backend
pytest app/tests -q
```

## Important implementation notes

- The frontend is intentionally simple and changeable. Current create forms are generic starter forms. You can later replace each module with richer forms and edit/delete dialogs.
- The backend is already structured for scalability: models, schemas, endpoints, RBAC service, config, dependencies, and tests are separated.
- Invoice format is stored as `contract`, `milestone`, or `permanent`. Later you can create separate PDF/template services for each format.
- Bank details support Indian fields like IFSC and foreign fields like SWIFT, IBAN, routing number, country, and currency.
- Access approval currently records the decision. Next enhancement can automatically grant a temporary or permanent module permission to a user.

## Next recommended enhancements

- Add edit/delete buttons in frontend tables.
- Add invoice PDF generation service.
- Add invoice line items table.
- Add temporary module access expiry date.
- Add audit logs for user/role/bank/client/invoice changes.
- Add refresh tokens and password reset flow.
- Add Dockerfile for backend/frontend deployment.

## v4 notes: access approval fixes

This build includes three fixes:

1. Users cannot request the same module permission again if that permission is already granted.
2. Rejecting an access request now requires and stores a rejection reason. The Access Requests table shows a `REJECTION REASON` column.
3. UI cards/forms/tables now use a more squarish card style instead of large rounded/pill-like cards.

If you already ran v3 locally, pull/replace the updated files and run:

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --reload
```

Then restart frontend:

```bash
cd frontend
npm run dev
```

## v5 patch notes

### Important Alembic fix
The v4 migration revision name was too long for PostgreSQL's `alembic_version.version_num` column. In v5 it has been shortened to:

```text
0002_access_req_reason
```

Run from `backend/`:

```bash
alembic upgrade head
```

### Create user payload sample
Use this payload in Swagger for `POST /api/v1/users` after authorizing as superadmin/admin:

```json
{
  "email": "hr.user@example.com",
  "full_name": "HR User",
  "password": "Mahakal@777",
  "role_names": ["hr"]
}
```

Valid role names seeded by default:

```text
admin, finance, hr, bank_manager
```

Only superadmin can create/assign `admin` role.

### HR client-scoped invoice access
For HR invoice creation, create an access request like:

```json
{
  "module_code": "invoices",
  "requested_permission": "create",
  "client_id": "PASTE_CLIENT_UUID_HERE",
  "reason": "Need to generate invoice for this client"
}
```

After admin/superadmin approval, HR can create invoices only for that approved client ID.

## V6 catalog additions

This version adds Companies, Projects and Milestones modules.

Run after replacing the code:

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --reload
```

Then restart the frontend:

```bash
cd frontend
npm install
npm run dev
```

New API modules:

- `/api/v1/companies`
- `/api/v1/projects`
- `/api/v1/milestones`

Client records now support optional mapping fields:

- `company_id`
- `project_id`
- `milestone_id`

The Clients table also shows mapped names:

- company name
- project name
- milestone name

Recommended manual test order:

1. Create a Company.
2. Create a Project and optionally paste the Company ID.
3. Create a Milestone and paste the Project ID.
4. Create a Client and paste Company ID, Project ID and Milestone ID.
5. Open Clients list and verify mapped names are visible.

## V6.4 invoice UX/status update

Changes added:

- Invoice create form uses dropdowns for Client and Bank Account.
- Client dropdown displays client name/type while still sending `client_id` to backend.
- Bank dropdown displays bank name + account holder while still sending `bank_account_id` to backend.
- Invoice status is now `draft` or `final`.
- Invoice table has a Print button for every invoice.
- Admin and superadmin can change invoice status directly from the invoice table.
- Backend added protected lookup endpoints:
  - `GET /api/v1/invoices/lookups/clients`
  - `GET /api/v1/invoices/lookups/banks`
- Backend added admin/superadmin-only status endpoint:
  - `PATCH /api/v1/invoices/{invoice_id}/status`

No database migration is required for these changes because invoice status is already stored as a string column.
