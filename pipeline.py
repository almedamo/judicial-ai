import csv, json, re
from pathlib import Path
from datetime import datetime
import fitz
from openpyxl import Workbook

DOC_TYPES = {
    "court_order": ["судебный приказ"],
    "writ_of_execution": ["исполнительный лист"],
    "fssp_resolution": ["постановление судебного пристава", "фссп"],
}
FIELDS = ["file_name", "document_type", "case_number", "debtor", "debt_amount", "document_date", "status", "missing_fields", "needs_legal_review"]

def read_pdf(path: Path) -> str:
    doc = fitz.open(path)
    return "
".join(page.get_text() for page in doc)

def read_xml(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def classify(text: str, is_xml: bool) -> str:
    low = text.lower()
    if is_xml: return "fssp_resolution"
    for kind, phrases in DOC_TYPES.items():
        if any(p in low for p in phrases): return kind
    return "unknown"

def one(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text, flags=re.I | re.M)
    return m.group(1).strip() if m else None

def extract(text: str, name: str, is_xml: bool) -> dict:
    dtype = classify(text, is_xml)
    case = one(r"(?:дел[оа]\s*№?|номер дела)\s*[:№]?\s*([A-Za-zА-Яа-я0-9\-/]+)", text)
    debtor = one(r"(?:должник|взыскать с)\s*[:\-]?\s*([^
,;]{3,120})", text)
    amount = one(r"(?:сумм[ау]|задолженн(?:ость|ости))\s*[:\-]?\s*([0-9\s]+(?:[,.][0-9]{1,2})?)\s*(?:руб|₽)", text)
    date = one(r"(?:от)\s*(\d{2}[.]\d{2}[.]\d{4})", text)
    if is_xml:
        case = case or one(r"(?:НомерДела|CaseNumber)[="'>:\s]+([A-Za-zА-Яа-я0-9\-/]+)", text)
        debtor = debtor or one(r"(?:Должник|Debtor)[="'>:\s]+([^<"']+)", text)
        amount = amount or one(r"(?:Сумма|Amount)[="'>:\s]+([0-9., ]+)", text)
    found = {"case_number": case, "debtor": debtor, "debt_amount": amount, "document_date": date}
    missing = [k for k, v in found.items() if not v]
    review = dtype == "unknown" or bool(missing)
    return {"file_name": name, "document_type": dtype, **found,
            "status": "needs_review" if review else "ok",
            "missing_fields": ",".join(missing), "needs_legal_review": review}

def process_file(path: Path, original_name: str) -> dict:
    if path.suffix.lower() == ".pdf": text, xml = read_pdf(path), False
    elif path.suffix.lower() == ".xml": text, xml = read_xml(path), True
    else: text, xml = path.read_text(encoding="utf-8", errors="ignore"), False
    return extract(text, original_name, xml)

def write_outputs(job_id: str, rows: list[dict], out: Path):
    out.mkdir(parents=True, exist_ok=True)
    csv_path, xlsx_path = out / f"{job_id}.csv", out / f"{job_id}.xlsx"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    wb = Workbook(); ws = wb.active; ws.title = "Results"; ws.append(FIELDS)
    for row in rows: ws.append([row.get(k) for k in FIELDS])
    wb.save(xlsx_path)
    return csv_path, xlsx_path
