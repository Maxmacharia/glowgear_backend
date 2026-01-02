from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import date


def generate_daily_report_pdf(report_data: dict, file_path: str):
    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    y = height - 50

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Daily Profit & Loss Report")

    y -= 40
    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Date: {report_data['date']}")

    y -= 40
    c.drawString(50, y, f"Receipts Profit: {report_data['receipts_profit']}")
    y -= 25
    c.drawString(50, y, f"Invoices Profit: {report_data['invoices_profit']}")
    y -= 25
    c.drawString(50, y, f"Expenses: {report_data['expenses']}")

    y -= 40
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, f"Net Profit / Loss: {report_data['net_profit']}")

    c.showPage()
    c.save()
