"""
Wake word detection test for BMO.
Tests the "hey_jarvis" pre-trained model from openWakeWord as a stand-in
for a "Hey BMO" wake word (closest available pre-trained phrase).

Usage:
    # Test with a WAV file:
    python test_wakeword.py --file path/to/audio.wav

    # Test with live microphone input:
    python test_wakeword.py --mic

    # Test with a WAV file and a custom threshold:
    python test_wakeword.py --file path/to/audio.wav --threshold 0.5
"""

import argparse
import sys
import numpy as np

try:
    import openwakeword
    from openwakeword.model import Model
except ImportError:
    print("ERROR: openwakeword is not installed. Run: pip install openwakeword")
    sys.exit(1)


# The wake word model to use. "hey_jarvis" is the closest available pre-trained
# model to "Hey BMO". Swap this out once a custom "hey_bmo" model is trained.
WAKE_WORD_MODEL = "hey_jarvis"
DEFAULT_THRESHOLD = 0.5
CHUNK_SIZE = 1280  # 80 ms of 16 kHz 16-bit mono audio (80ms * 16000 / 1000 = 1280 samples)


def download_models():
    print("Downloading pre-trained models (one-time setup)...")
    openwakeword.utils.download_models()
    print("Models ready.\n")


def load_model() -> Model:
    return Model(
        wakeword_models=[WAKE_WORD_MODEL],
        enable_speex_noise_suppression=False,
        vad_threshold=0.0,
    )


def test_wav_file(file_path: str, threshold: float) -> bool:
    """
    Run wake word detection against a WAV file.
    Returns True if the wake word was detected at least once.
    """
    print(f"Testing wake word detection on: {file_path}")
    print(f"Model: {WAKE_WORD_MODEL}  |  Threshold: {threshold}\n")

    model = load_model()
    predictions = model.predict_clip(file_path)

    detected = False
    for model_name, scores in predictions.items():
        max_score = float(np.max(scores)) if len(scores) > 0 else 0.0
        print(f"  Model '{model_name}': max score = {max_score:.4f}")
        if max_score >= threshold:
            print(f"  DETECTED (score {max_score:.4f} >= threshold {threshold})")
            detected = True
        else:
            print(f"  NOT detected (score {max_score:.4f} < threshold {threshold})")

    return detected


def test_microphone(threshold: float):
    """
    Stream audio from the default microphone and print detections in real time.
    Press Ctrl-C to stop.
    """
    try:
        import pyaudio
    except ImportError:
        print("ERROR: pyaudio is not installed. Run: pip install pyaudio")
        sys.exit(1)

    print(f"Listening on microphone...", flush=True)
    print(f"Model: {WAKE_WORD_MODEL}  |  Threshold: {threshold}", flush=True)
    print("Say the wake word. Press Ctrl-C to stop.\n", flush=True)

    print("Initializing PyAudio...", flush=True)
    audio = pyaudio.PyAudio()

    # List available devices for debugging and find one that works
    print("Available audio devices:", flush=True)
    num_devices = audio.get_device_count()
    input_device_index = None
    
    for i in range(num_devices):
        try:
            device_info = audio.get_device_info_by_index(i)
            if device_info.get('maxInputChannels', 0) > 0:
                name = device_info.get('name')
                default_rate = device_info.get('defaultSampleRate')
                print(f"  [{i}] {name} (Channels: {device_info.get('maxInputChannels')}, Default Rate: {default_rate})", flush=True)
                
                # Try to see if it supports 16000
                try:
                    if audio.is_format_supported(16000, input_device=i, input_channels=1, input_format=pyaudio.paInt16):
                        print(f"      - Supports 16000 Hz", flush=True)
                        if input_device_index is None:
                            input_device_index = i
                except Exception:
                    print(f"      - Does NOT support 16000 Hz", flush=True)
        except Exception as e:
            print(f"  [{i}] Error getting device info: {e}", flush=True)

    if input_device_index is None:
        print("WARNING: No device explicitly reported support for 16000 Hz. Trying default device.", flush=True)
    else:
        print(f"Using device index {input_device_index}", flush=True)

    model = load_model()

    stream = None
    try:
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            input_device_index=input_device_index,
            frames_per_buffer=CHUNK_SIZE,
        )

        while True:
            raw = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            frame = np.frombuffer(raw, dtype=np.int16)
            predictions = model.predict(frame)

            for model_name, score in predictions.items():
                if score >= threshold:
                    print(f"  WAKE WORD DETECTED  |  model={model_name}  score={score:.4f}")
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        audio.terminate()


def main():
    parser = argparse.ArgumentParser(description="BMO wake word detection test")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", metavar="WAV", help="Path to a 16-bit 16 kHz mono WAV file")
    group.add_argument("--mic", action="store_true", help="Use the default microphone")
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Detection threshold (default: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download pre-trained models before running",
    )
    args = parser.parse_args()

    if args.download:
        download_models()

    if args.file:
        detected = test_wav_file(args.file, args.threshold)
        sys.exit(0 if detected else 1)
    else:
        test_microphone(args.threshold)


if __name__ == "__main__":
    main()
