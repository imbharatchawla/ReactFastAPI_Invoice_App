from fastapi import APIRouter

from app.api.v1.endpoints import access_requests, auth, banks, catalog, clients, dashboard, documents, forgot_password, health, invoices, users

router = APIRouter()
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(dashboard.router)
router.include_router(users.router)
router.include_router(clients.router)
router.include_router(catalog.companies_router)
router.include_router(catalog.projects_router)
router.include_router(catalog.milestones_router)
router.include_router(catalog.consultants_router)
router.include_router(banks.router)
router.include_router(invoices.router)
router.include_router(documents.router)
router.include_router(access_requests.router)
router.include_router(forgot_password.router)
