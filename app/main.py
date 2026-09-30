from pathlib import Path
from typing import Annotated
from uuid import uuid4
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from .pipeline import process_file, write_outputs

app = FastAPI(title="Judicial AI Starter")
BASE = Path("data")
INBOX, OUT = BASE / "input", BASE / "output"
JOBS: dict[str, dict] = {}
INBOX.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/v1/batches")
async def create_batch(files: Annotated[list[UploadFile], File(...)]):
    job_id = str(uuid4())
    job_dir = INBOX / job_id
    job_dir.mkdir()
    results = []
    for upload in files:
        suffix = Path(upload.filename or "upload").suffix.lower()
        if suffix not in {".pdf", ".xml", ".txt"}:
            raise HTTPException(400, "Allowed formats: PDF, XML, TXT")
        path = job_dir / f"{uuid4()}{suffix}"
        path.write_bytes(await upload.read())
        results.append(process_file(path, upload.filename or path.name))
    csv_path, xlsx_path = write_outputs(job_id, results, OUT)
    JOBS[job_id] = {"job_id": job_id, "count": len(results), "results": results,
                    "csv": str(csv_path), "xlsx": str(xlsx_path)}
    return JOBS[job_id]

@app.get("/api/v1/jobs/{job_id}")
def job(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(404, "Job not found")
    return JOBS[job_id]

@app.get("/api/v1/jobs/{job_id}/result.{fmt}")
def result(job_id: str, fmt: str):
    if job_id not in JOBS or fmt not in {"csv", "xlsx"}:
        raise HTTPException(404, "Result not found")
    path = JOBS[job_id][fmt]
    return FileResponse(path, filename=Path(path).name)
