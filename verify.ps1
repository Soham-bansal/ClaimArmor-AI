param([switch]$Retrain)

$ErrorActionPreference = "Stop"
$env:PYTHONDONTWRITEBYTECODE = "1"

if ($Retrain) {
    python -m app.ml.train --regenerate --rows 3000
}

python -m app.evaluation
python -m app.identity_evaluation
python -m app.full_evaluation
python -m unittest discover -s tests -v
Write-Output "ClaimArmor verification completed successfully."
