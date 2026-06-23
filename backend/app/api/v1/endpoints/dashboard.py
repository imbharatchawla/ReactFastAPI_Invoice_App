from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.bank import BankAccount
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {
        "clients": db.query(Client).count(),
        "bank_accounts": db.query(BankAccount).count(),
        "invoices": db.query(Invoice).count(),
    }


@router.get("/home")
def home_dashboard(year: int | None = None, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Compact home dashboard data.

    Graph shows monthly totals of all non-draft invoices for the selected year.
    If no year is passed, current calendar year is used by default.
    """
    selected_year = year or date.today().year
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly_totals = {month: Decimal("0.00") for month in range(1, 13)}

    invoice_month_rows = (
        db.query(
            func.extract("month", Invoice.invoice_date).label("month_no"),
            func.coalesce(func.sum(Invoice.total_amount), 0).label("amount"),
            func.count(Invoice.id).label("count"),
        )
        .filter(Invoice.status != "draft")
        .filter(Invoice.invoice_date.isnot(None))
        .filter(func.extract("year", Invoice.invoice_date) == selected_year)
        .group_by("month_no")
        .all()
    )
    monthly_counts = {month: 0 for month in range(1, 13)}
    for row in invoice_month_rows:
        month_no = int(row.month_no or 0)
        if month_no in monthly_totals:
            monthly_totals[month_no] = Decimal(str(row.amount or 0))
            monthly_counts[month_no] = int(row.count or 0)

    available_year_rows = (
        db.query(func.extract("year", Invoice.invoice_date).label("year"))
        .filter(Invoice.invoice_date.isnot(None))
        .group_by("year")
        .order_by("year")
        .all()
    )
    available_years = [int(row.year) for row in available_year_rows if row.year]
    if selected_year not in available_years:
        available_years.append(selected_year)
    available_years = sorted(set(available_years))

    clients = db.query(Client).order_by(Client.created_at.desc()).all()
    invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).all()

    return {
        "selected_year": selected_year,
        "available_years": available_years,
        "invoice_months": [
            {"month": month_labels[month - 1], "count": monthly_counts[month], "amount": str(monthly_totals[month])}
            for month in range(1, 13)
        ],
        "clients": [
            {
                "id": str(client.id),
                "client_name": client.name,
                "company_name": client.company.name if client.company else "-",
                "currency": client.currency or "-",
                "countries": client.countries or client.country or "-",
                "created_at": client.created_at,
            }
            for client in clients
        ],
        "invoices": [
            {
                "id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "client_name": invoice.client.name if invoice.client else "-",
                "invoice_date": invoice.invoice_date,
                "status": invoice.status,
                "currency": invoice.currency,
                "total_amount": str(invoice.total_amount),
                "created_at": invoice.created_at,
            }
            for invoice in invoices
        ],
    }
