# Trim bmo_voice.mp3 to a clean 25-second reference.wav for XTTS voice cloning.
# Run once after starting the container:
#   powershell -ExecutionPolicy Bypass -File tests\prep_voice.ps1

$CONTAINER = "brain-app-1"  # adjust if your container name differs

Write-Host "Converting bmo_voice.mp3 → reference.wav (25s, 22050Hz mono)..."

docker exec $CONTAINER ffmpeg -y `
    -i /app/data/bmo/bmo_voice.mp3 `
    -ss 0 -t 25 `
    -ar 22050 -ac 1 -sample_fmt s16 `
    /app/data/bmo_voice/reference.wav

if ($LASTEXITCODE -eq 0) {
    Write-Host "Done. reference.wav updated." -ForegroundColor Green
    Write-Host ""
    Write-Host "Now restart the container to clear cached conditioning latents:"
    Write-Host "  docker compose restart app"
} else {
    Write-Host "ffmpeg failed. Check the container name with: docker ps" -ForegroundColor Red
}
