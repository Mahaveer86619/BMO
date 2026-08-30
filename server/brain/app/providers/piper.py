import subprocess
import os

class PiperProvider:
    @staticmethod
    def synthesize(text: str, output_path: str, model_path: str):
        # Assumes piper binary is in PATH (provided by Docker)
        command = [
            "piper",
            "--model", model_path,
            "--output_file", output_path
        ]
        subprocess.run(command, input=text.encode(), check=True)
