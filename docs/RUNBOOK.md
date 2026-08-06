# Local runbook

## Start

```powershell
cd E:\Capstone
python -m pip install -r requirements.txt
.\run.ps1
```

Open `http://127.0.0.1:8000`.

## Verify

```powershell
.\verify.ps1
```

Use `-Retrain` only when the synthetic generator or features changed:

```powershell
.\verify.ps1 -Retrain
```

## Reset local demonstration data

Stop the server, move `claimarmor.db` to a backup location, and restart. The
application creates a fresh database and seeds the demonstration users and
claims. Avoid deleting the database if review evidence must be retained.

## Common failures

- `401`: sign in again; access tokens expire after eight hours.
- `403`: the current role cannot perform that action.
- model not ready: run `python -m app.ml.train --regenerate --rows 3000`.
- evaluation unavailable: run `python -m app.evaluation`.
- provider enhancement unavailable: keep offline mode or validate the API key.
- PostgreSQL connection failure: unset `CLAIMARMOR_DATABASE_URL` to return to
  local SQLite while investigating the database service.

