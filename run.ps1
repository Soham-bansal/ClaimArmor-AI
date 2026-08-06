$ErrorActionPreference = "Stop"
$env:PYTHONDONTWRITEBYTECODE = "1"
python -m uvicorn app.main:app --reload

