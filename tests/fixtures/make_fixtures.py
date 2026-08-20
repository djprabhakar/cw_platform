from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

FIXTURES_DIR = Path(__file__).parent


def make_bank_statement_pdf() -> None:
    path = FIXTURES_DIR / "bank_statement_sample.pdf"
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica", 12)
    c.drawString(72, 720, "Monthly Bank Statement")
    c.drawString(72, 690, "Account Number: 1234567890")
    c.drawString(72, 670, "Statement Period End: 01/31/2026")
    c.drawString(72, 620, "Ending Balance")
    c.drawString(250, 620, "1,200.00")
    c.save()


def make_agent_bank_notice_pdf() -> None:
    path = FIXTURES_DIR / "agent_bank_notice_sample.pdf"
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica", 12)
    c.drawString(72, 720, "Interest Payment Notice")
    c.drawString(72, 680, "Payment Amount")
    c.drawString(250, 680, "45,000")
    c.drawString(72, 660, "Interest Rate")
    c.drawString(250, 660, "4.75%")
    c.drawString(72, 640, "Payment Date: 02/15/2026")
    c.setFont("Helvetica", 9)
    c.drawString(72, 100, "Note 1: Payment Amount is reported in whole dollars.")
    c.save()


if __name__ == "__main__":
    make_bank_statement_pdf()
    make_agent_bank_notice_pdf()
    print("Fixtures written to", FIXTURES_DIR)
