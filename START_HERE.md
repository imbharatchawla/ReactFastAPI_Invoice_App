# START HERE - Invoice RBAC Full Stack App

This ZIP contains BOTH backend and frontend.

## Main folders

- `backend/` - FastAPI + PostgreSQL + Alembic + JWT + RBAC APIs
- `frontend/` - React + Material UI UI application
- `sql/` - database creation and seed notes
- `README.md` - full installation and run guide
- `docker-compose.yml` - local PostgreSQL container

## Run backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# OR source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
copy .env.example .env          # Windows
# OR cp .env.example .env       # Mac/Linux
alembic upgrade head
uvicorn app.main:app --reload
```

Backend URL: http://localhost:8000
API docs: http://localhost:8000/docs

## Run frontend

```bash
cd frontend
npm install
copy .env.example .env          # Windows
# OR cp .env.example .env       # Mac/Linux
npm run dev
```

Frontend URL: http://localhost:5173

## Default login

Email: `superadmin@example.com`
Password: `Mahakal@777`

## Note

If you are opening the ZIP on phone, some file preview apps show only the first folder/files. Extract it fully on Windows using "Extract All" or 7-Zip, then open the root folder in VS Code.

## Direct PDF Download Setup

This build uses Playwright/Chromium on the backend for the invoice Download PDF button. This is required because browser Print -> Save PDF uses Chromium's print engine, while html2canvas/html2pdf does not preserve the invoice print layout correctly.

Run once after installing backend requirements:

```bash
cd backend
pip install -r requirements.txt
python -m playwright install chromium
```

Then start backend normally:

```bash
uvicorn app.main:app --reload
```
