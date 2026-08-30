# BMO full test suite - 50 cases covering every server capability.
# Generates input WAVs via Windows TTS, sends each to /api/v1/talk, saves responses.
#
# Run from brain/ directory:
#   powershell -ExecutionPolicy Bypass -File tests\run_full_tests.ps1
#
# After the run, paste docker logs here to match server output to each test.

$SERVER = "http://localhost:8000"
$OUT    = "tests\audio\full"

New-Item -ItemType Directory -Force -Path $OUT | Out-Null

# ── Test definitions ──────────────────────────────────────────────────────────
# id  : zero-padded filename prefix
# cat : category label for the summary
# txt : spoken text (Windows TTS input)

$tests = @(
    # ── TIME (5) ──────────────────────────────────────────────────────────────
    @{ id="01"; cat="time";    txt="LUMI what time is it" },
    @{ id="02"; cat="time";    txt="LUMI tell me the current time" },
    @{ id="03"; cat="time";    txt="LUMI what time is it right now" },
    @{ id="04"; cat="time";    txt="LUMI time please" },
    @{ id="05"; cat="time";    txt="LUMI what is the time" },

    # ── WEATHER (5) ───────────────────────────────────────────────────────────
    @{ id="06"; cat="weather"; txt="LUMI what is the weather" },
    @{ id="07"; cat="weather"; txt="LUMI weather in London" },
    @{ id="08"; cat="weather"; txt="LUMI how is the weather in New York" },
    @{ id="09"; cat="weather"; txt="LUMI is it raining in Tokyo" },
    @{ id="10"; cat="weather"; txt="LUMI what is the temperature in Paris" },

    # ── SEARCH (8) ────────────────────────────────────────────────────────────
    @{ id="11"; cat="search";  txt="LUMI search for black holes" },
    @{ id="12"; cat="search";  txt="LUMI search for artificial intelligence" },
    @{ id="13"; cat="search";  txt="LUMI look up the solar system" },
    @{ id="14"; cat="search";  txt="LUMI search for quantum computing" },
    @{ id="15"; cat="search";  txt="LUMI find info on the Great Wall of China" },
    @{ id="16"; cat="search";  txt="LUMI search for dinosaurs" },
    @{ id="17"; cat="search";  txt="LUMI look up the Amazon rainforest" },
    @{ id="18"; cat="search";  txt="LUMI search about the human brain" },

    # ── CALCULATE (5) ─────────────────────────────────────────────────────────
    @{ id="19"; cat="calc";    txt="LUMI calculate 15 times 7" },
    @{ id="20"; cat="calc";    txt="LUMI calculate 100 divided by 4" },
    @{ id="21"; cat="calc";    txt="LUMI calculate 25 plus 37" },
    @{ id="22"; cat="calc";    txt="LUMI what is 12 times 12" },
    @{ id="23"; cat="calc";    txt="LUMI calculate 200 minus 85" },

    # ── DEFINE / EXPLAIN (5) ──────────────────────────────────────────────────
    @{ id="24"; cat="define";  txt="LUMI define photosynthesis" },
    @{ id="25"; cat="define";  txt="LUMI what is gravity" },
    @{ id="26"; cat="define";  txt="LUMI explain machine learning" },
    @{ id="27"; cat="define";  txt="LUMI define democracy" },
    @{ id="28"; cat="define";  txt="LUMI what is the internet" },

    # ── GENERAL KNOWLEDGE (5) ─────────────────────────────────────────────────
    @{ id="29"; cat="llm";     txt="LUMI what is the capital of France" },
    @{ id="30"; cat="llm";     txt="LUMI who invented the telephone" },
    @{ id="31"; cat="llm";     txt="LUMI how far is the moon from earth" },
    @{ id="32"; cat="llm";     txt="LUMI what is the largest ocean on earth" },
    @{ id="33"; cat="llm";     txt="LUMI how many planets are in the solar system" },

    # ── JOKES AND CREATIVE (5) ────────────────────────────────────────────────
    @{ id="34"; cat="llm";     txt="LUMI tell me a joke" },
    @{ id="35"; cat="llm";     txt="LUMI joke" },
    @{ id="36"; cat="llm";     txt="LUMI tell me something funny" },
    @{ id="37"; cat="llm";     txt="LUMI make me laugh" },
    @{ id="38"; cat="llm";     txt="LUMI tell me a riddle" },

    # ── REMINDERS (5) ─────────────────────────────────────────────────────────
    @{ id="39"; cat="reminder";txt="LUMI remind me to drink water" },
    @{ id="40"; cat="reminder";txt="LUMI remind me to call mum at 5 pm" },
    @{ id="41"; cat="reminder";txt="LUMI set a reminder to take my medicine" },
    @{ id="42"; cat="reminder";txt="LUMI remind me to check the oven in 30 minutes" },
    @{ id="43"; cat="reminder";txt="LUMI remember to buy groceries tomorrow" },

    # ── SOCIAL / GREETINGS (5) ────────────────────────────────────────────────
    @{ id="44"; cat="social";  txt="Hey there" },
    @{ id="45"; cat="social";  txt="Good morning" },
    @{ id="46"; cat="social";  txt="Goodbye" },
    @{ id="47"; cat="social";  txt="Thanks a lot" },
    @{ id="48"; cat="social";  txt="How are you doing" },

    # ── HELP (2) ──────────────────────────────────────────────────────────────
    @{ id="49"; cat="help";    txt="LUMI what can you do" },
    @{ id="50"; cat="help";    txt="LUMI help" }
)

# ── Synthesize input WAVs ──────────────────────────────────────────────────────
Add-Type -AssemblyName System.Speech
$synth      = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = -3   # slower = better Whisper accuracy

Write-Host ""
Write-Host "=== Synthesizing 50 input WAVs ===" -ForegroundColor Cyan

foreach ($t in $tests) {
    $path = Join-Path $OUT "$($t.id)_$($t.cat).wav"
    $synth.SetOutputToWaveFile($path)
    $synth.Speak($t.txt)
    Write-Host "  $($t.id)  [$($t.cat)]  $($t.txt)"
}
$synth.SetOutputToDefaultAudioDevice()
Write-Host "Done." -ForegroundColor Green
Write-Host ""

# ── Wait for server ────────────────────────────────────────────────────────────
Write-Host "=== Checking server ===" -ForegroundColor Cyan
try {
    $ready  = Invoke-RestMethod "$SERVER/ready" -ErrorAction Stop
    $loaded = $ready.loaded -join ", "
    Write-Host "  Status: $($ready.status)   Loaded: $loaded" -ForegroundColor Green
} catch {
    Write-Host "  WARNING: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "  Server may not be ready yet - proceeding anyway." -ForegroundColor Yellow
}
Write-Host ""

# ── Run all 50 tests ──────────────────────────────────────────────────────────
Write-Host "=== Running 50 pipeline tests ===" -ForegroundColor Cyan
Write-Host "  (each request logged separately - match IDs to docker logs)" -ForegroundColor DarkGray
Write-Host ""

$results = @()

foreach ($t in $tests) {
    $inPath  = Join-Path $OUT "$($t.id)_$($t.cat).wav"
    $outPath = Join-Path $OUT "resp_$($t.id)_$($t.cat).wav"

    $label = "[$($t.id)] [$($t.cat)]  $($t.txt)"
    Write-Host $label -ForegroundColor Yellow

    $sw = [Diagnostics.Stopwatch]::StartNew()

    try {
        & curl.exe -s -o $outPath -F "audio=@$inPath" "$SERVER/api/v1/talk"
        $sw.Stop()

        $ok      = $LASTEXITCODE -eq 0
        $elapsed = [math]::Round($sw.Elapsed.TotalSeconds, 2)
        $size    = if (Test-Path $outPath) { (Get-Item $outPath).Length } else { 0 }
        $status  = if ($ok -and $size -gt 100) { "OK  " } else { "FAIL" }
        $color   = if ($status -eq "OK  ") { "Green" } else { "Red" }

        Write-Host "  $status  time=${elapsed}s  response=${size} bytes" -ForegroundColor $color

        $results += [PSCustomObject]@{
            ID       = $t.id
            Category = $t.cat
            Status   = $status.Trim()
            Secs     = $elapsed
            Bytes    = $size
            Input    = $t.txt
        }
    } catch {
        $sw.Stop()
        Write-Host "  ERROR: $_" -ForegroundColor Red
        $results += [PSCustomObject]@{
            ID = $t.id; Category = $t.cat; Status = "ERROR"
            Secs = 0; Bytes = 0; Input = $t.txt
        }
    }
}

# ── Summary ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
$results | Format-Table ID, Category, Status, Secs, Bytes -AutoSize

$passed = ($results | Where-Object { $_.Status -eq "OK" }).Count
$failed = ($results | Where-Object { $_.Status -ne "OK" }).Count
$avgMs  = [math]::Round(($results | Where-Object { $_.Status -eq "OK" } | Measure-Object -Property Secs -Average).Average, 2)

Write-Host ""
Write-Host "  Passed : $passed / 50" -ForegroundColor $(if ($passed -eq 50) { "Green" } else { "Yellow" })
Write-Host "  Failed : $failed" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Red" })
Write-Host "  Avg time (OK): ${avgMs}s" -ForegroundColor Cyan

Write-Host ""
Write-Host "--- Per-category averages ---" -ForegroundColor Cyan
$results | Where-Object { $_.Status -eq "OK" } |
    Group-Object Category |
    ForEach-Object {
        $avg = [math]::Round(($_.Group | Measure-Object -Property Secs -Average).Average, 2)
        Write-Host ("  {0,-10}  avg {1}s  ({2} tests)" -f $_.Name, $avg, $_.Count)
    }

Write-Host ""
Write-Host "Response WAVs saved to: $OUT" -ForegroundColor Green
Write-Host "Play a response:  Start-Process `"$OUT\resp_01_time.wav`""
Write-Host ""
Write-Host "Paste docker logs output here for full analysis." -ForegroundColor DarkGray
