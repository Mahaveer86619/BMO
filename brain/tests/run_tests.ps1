# BMO pipeline test - creates WAV files via Windows TTS, sends to /api/v1/talk, saves responses.
# Run from brain/ directory:
#   powershell -ExecutionPolicy Bypass -File tests\run_tests.ps1

$SERVER = "http://localhost:8000"
$OUT    = "tests\audio"

New-Item -ItemType Directory -Force -Path $OUT | Out-Null

# ── Create test WAV files via Windows TTS ─────────────────────────────────────
Add-Type -AssemblyName System.Speech
$synth      = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = -3   # slower helps Whisper STT accuracy

$tests = @(
    @{ f="01_tell_me.wav";   t="LUMI, tell me what is the capital of France" },
    @{ f="02_time.wav";      t="LUMI, what time is it" },
    @{ f="03_joke.wav";      t="LUMI, joke" },
    @{ f="04_calculate.wav"; t="LUMI, calculate 15 times 7" },
    @{ f="05_define.wav";    t="LUMI, define photosynthesis" },
    @{ f="06_search.wav";    t="LUMI, search for black holes" },
    @{ f="07_greeting.wav";  t="Hey there" },
    @{ f="08_bye.wav";       t="Goodbye" },
    @{ f="09_no_lumi.wav";   t="What is the weather like today" }
)

Write-Host ""
Write-Host "=== Creating test WAV files ===" -ForegroundColor Cyan
foreach ($t in $tests) {
    $path = Join-Path $OUT $t.f
    $synth.SetOutputToWaveFile($path)
    $synth.Speak($t.t)
    Write-Host "  $($t.f)  ->  $($t.t)"
}
$synth.SetOutputToDefaultAudioDevice()
Write-Host "Done."
Write-Host ""

# ── Check server ──────────────────────────────────────────────────────────────
Write-Host "=== Checking server ===" -ForegroundColor Cyan
try {
    $ready = Invoke-RestMethod "$SERVER/ready" -ErrorAction Stop
    $loaded = $ready.loaded -join ", "
    Write-Host "  Status: $($ready.status)   Loaded: $loaded"
} catch {
    Write-Host "  WARNING: $($_.Exception.Message)" -ForegroundColor Yellow
}
Write-Host ""

# ── Run each test via HTTP /talk ──────────────────────────────────────────────
Write-Host "=== Running pipeline tests ===" -ForegroundColor Cyan

$results = @()

foreach ($t in $tests) {
    $inPath  = Join-Path $OUT $t.f
    $outPath = Join-Path $OUT ("resp_" + $t.f)

    Write-Host ""
    Write-Host "[$($t.f)]  $($t.t)" -ForegroundColor Yellow

    $sw = [Diagnostics.Stopwatch]::StartNew()

    try {
        & curl.exe -s -o $outPath -F "audio=@$inPath" "$SERVER/api/v1/talk"
        $sw.Stop()

        $httpOk      = $LASTEXITCODE -eq 0
        $elapsed     = [math]::Round($sw.Elapsed.TotalSeconds, 2)
        $respSize    = if (Test-Path $outPath) { (Get-Item $outPath).Length } else { 0 }
        $color       = if ($httpOk -and $respSize -gt 100) { "Green" } else { "Red" }
        $status      = if ($httpOk) { "OK" } else { "FAIL" }

        Write-Host "  $status   time=${elapsed}s   response=${respSize} bytes" -ForegroundColor $color

        $results += [PSCustomObject]@{
            Test     = $t.f
            Status   = $status
            Secs     = $elapsed
            RespSize = $respSize
            Input    = $t.t
        }
    } catch {
        $sw.Stop()
        Write-Host "  ERROR: $_" -ForegroundColor Red
    }
}

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
$results | Format-Table Test, Status, Secs, RespSize -AutoSize

Write-Host ""
Write-Host "Response WAVs saved to: $OUT" -ForegroundColor Green
Write-Host "Play a response:  Start-Process `"$OUT\resp_02_time.wav`""
