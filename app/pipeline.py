import csv
import re
from pathlib import Path
import fitz
import pytesseract
from PIL import Image
from openpyxl import Workbook

DOC_TYPES = {
    "court_order": ["судебный приказ"],
    "writ_of_execution": ["исполнительный лист"],
    "fssp_resolution": ["постановление судебного пристава", "фссп"],
}
FIELDS = ["file_name", "document_type", "case_number", "debtor", "debt_amount", "document_date", "status", "missing_fields", "needs_legal_review"]

def read_pdf(path: Path) -> str:
    with fitz.open(path) as doc:
        pages = []
        for page in doc:
            text = page.get_text()
            if len(text.strip()) < 50:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                text = pytesseract.image_to_string(image, lang="rus")
            pages.append(text)
        return "\n".join(pages)

def one(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text, flags=re.I | re.M)
    return m.group(1).strip() if m else None

def process_file(path: Path, name: str) -> dict:
    if path.suffix.lower() == ".pdf":
        text = read_pdf(path)
    else:
        text = path.read_text(encoding="utf-8", errors="ignore")
    low = text.lower()
    if path.suffix.lower() == ".xml":
        dtype = "fssp_resolution"
    else:
        dtype = next((k for k, phrases in DOC_TYPES.items() if any(p in low for p in phrases)), "unknown")
    case = one(r"(?:дел[оа]\s*№?|номер дела)\s*[:№]?\s*([A-Za-zА-Яа-я0-9\-/]+)", text)
    debtor = one(r"(?:должник|взыскать с должника)\s*[:\-]?\s*([^\n,;]{3,120})", text)
    amount = one(r"(?:сумм[ау]|задолженн(?:ость|ости))\s*[:\-]?\s*([0-9\s]+(?:[,.][0-9]{1,2})?)\s*(?:руб|₽)", text)
    date = one(r"(?:от)\s*(\d{2}[.]\d{2}[.]\d{4})", text)
    if path.suffix.lower() == ".xml":
        case = case or one(r"<CaseNumber>([^<]+)</CaseNumber>", text)
        debtor = debtor or one(r"<Debtor>([^<]+)</Debtor>", text)
        amount = amount or one(r"<Amount>([^<]+)</Amount>", text)
    found = {"case_number": case, "debtor": debtor, "debt_amount": amount, "document_date": date}
    missing = [key for key, value in found.items() if not value]
    review = dtype == "unknown" or bool(missing)
    return {"file_name": name, "document_type": dtype, **found,
            "status": "needs_review" if review else "ok", "missing_fields": ",".join(missing),
            "needs_legal_review": review}

def write_outputs(job_id: str, rows: list[dict], out: Path):
    out.mkdir(parents=True, exist_ok=True)
    csv_path, xlsx_path = out / f"{job_id}.csv", out / f"{job_id}.xlsx"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    wb = Workbook()
    ws = wb.active
    ws.title = "Results"
    ws.append(FIELDS)
    for row in rows:
        ws.append([row.get(key) for key in FIELDS])
    wb.save(xlsx_path)
    return csv_path, xlsx_path
