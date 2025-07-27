import os
import subprocess
import shlex
import json


class TrufflehogScanner:
    def __init__(self):
        pass

    def scan(self):
        command = (
            shlex.join(self.build_trufflehog_command())
            + " > trufflehog_report_sec-m8.json"
        )
        print("Running trufflehog command:\n", command)  # for debug

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True,
        )

        print("STDOUT:\n", result.stdout)
        # print("STDERR:\n", result.stderr)

        return result.returncode

    def report(self):
        report_path = "trufflehog_report_sec-m8.json"
        if not os.path.isfile(report_path):
            raise FileNotFoundError(f"{report_path} not found in current directory.")

        with open(report_path, "r") as f:
            return json.load(f)

    def normalize_flag(self, name: str) -> str:
        """Convert env var to CLI flag, e.g."""
        if len(name.replace("trufflehog_", "")) == 1:
            return "-" + name.replace("trufflehog_", "").lower()
        else:
            return "--" + name.replace("trufflehog_", "").lower().replace("_", "-")

    def build_trufflehog_command(self):
        # trufflehog git
        # Get current branch name using git
        try:
            branch_name = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
            ).strip()
        except subprocess.CalledProcessError:
            branch_name = "HEAD"

        base_command = [
            "trufflehog",
            "git",
            "file://.",
            "--branch",
            branch_name,
            "--json",
        ]
        cli_flags = []

        for key, value in os.environ.items():
            if not key.startswith("trufflehog_"):
                continue

            flag = self.normalize_flag(key)
            if flag in ["--json"]:
                # Skip flags that are already set in base_command
                continue
            # Boolean flag (true/false) with no value
            if value.lower() in ("1", "true", "yes"):
                cli_flags.append(flag)
            elif value.lower() in ("0", "false", "no"):
                continue  # skip false flags
            else:
                # Handle flags with values, e.g. --log-level=debug
                cli_flags.append(f"{flag}={value}")

        return base_command + cli_flags
