#!/usr/bin/env python3
import os
import sys

def create_valid_pdf(filename):
    # Minimal binary PDF 1.4 generation
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length 215 >>\nstream\n"
        b"BT\n"
        b"/F1 18 Tf\n"
        b"50 720 Td\n"
        b"(VerdantOS ISO 50001:2018 Audit Evidence Report) Tj\n"
        b"0 -30 Td\n"
        b"/F1 12 Tf\n"
        b"(Tenant: Campus North Tenant | Site: Campus North | Asset: AHU-01) Tj\n"
        b"0 -20 Td\n"
        b"(Status: VERIFIED IMMUTABLE | SHA-256 Ledger Chain Intact) Tj\n"
        b"0 -20 Td\n"
        b"(IPMVP Approach: IPMVP Option A - Retrofit Isolation) Tj\n"
        b"0 -20 Td\n"
        b"(Annual Realized Savings: 24,500 kWh / $3,675/yr +- $250) Tj\n"
        b"ET\n"
        b"endstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000244 00000 n \n0000000509 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\n"
        b"startxref\n578\n"
        b"%%EOF\n"
    )
    
    with open(filename, "wb") as f:
        f.write(pdf_content)
    print(f"Generated binary PDF report at: {filename} ({len(pdf_content)} bytes)")

if __name__ == "__main__":
    out_path = "docs/slice/sample_iso50001_report.pdf"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    create_valid_pdf(out_path)
