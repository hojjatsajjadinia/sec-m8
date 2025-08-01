from utils.http import post
from utils.get_env_variable import get_env_variable
import subprocess
import re


class Gitlab:
    def __init__(self, gitlab_url, gitlab_token, logger):
        self.gitlab_url = gitlab_url.strip()
        self.gitlab_token = gitlab_token.strip()
        self.logger = logger

    def comment_on_merge_request(self, report, tool_name):
        try:
            ci_merge_request_iid = get_env_variable("CI_MERGE_REQUEST_IID")
            ci_project_id = get_env_variable("CI_PROJECT_ID")
        except EnvironmentError:
            self.logger.info("No Merge Request ID found.")
            return
        headers = {
            "PRIVATE-TOKEN": self.gitlab_token,
            "Content-Type": "application/json",
        }
        if tool_name.lower() == "gitleaks":
            table = self.format_gitleaks_report(report)
        elif tool_name.lower() == "trufflehog":
            table = self.format_trufflehog_report(report)
        print(table)
        if not table:
            self.logger.info("No findings to report.")
            return
        response = post(
            f"{self.gitlab_url}/api/v4/projects/{ci_project_id}/merge_requests/{ci_merge_request_iid}/notes",
            headers=headers,
            data={"body": f"### Gitleaks Report\n\n{table}"},
        )
        if response.status_code == 201:
            self.logger.info("Comment posted successfully on the Merge Request.")
        else:
            self.logger.error(
                f"Failed to post comment on Merge Request: {response.status_code} - {response.text}"
            )

    def format_gitleaks_report(self, report):
        scan_code_change = get_env_variable("SCAN_CODE_CHANGE", False)
        hashes = []
        if str(scan_code_change).lower() in ("1", "true", "yes"):
            self.logger.info("Fetching commit hashes for code changes.")
            target_branch = get_env_variable("CI_MERGE_REQUEST_TARGET_BRANCH_NAME")
            diff_base_sha = get_env_variable("CI_MERGE_REQUEST_DIFF_BASE_SHA")
            commit_sha = get_env_variable("CI_COMMIT_SHA")
            # Fetch the target branch without printing output
            subprocess.run(
                ["git", "fetch", "origin", target_branch],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Get the commit hashes
            result = subprocess.run(
                ["git", "log", "--pretty=format:%H", f"{diff_base_sha}..{commit_sha}"],
                stdout=subprocess.PIPE,
                check=True,
                text=True,
            )
            hashes = result.stdout.strip().splitlines()
            self.logger.info(f"Found {len(hashes)} commit hashes for code changes.")

        # Start table
        table = "| RuleID | File | Author | Link |\n"
        table += "| ------ | ---- | ------ | ---- |\n"
        total_rows = 0
        for entry in report:
            if hashes and entry.get("Commit") not in hashes:
                continue
            rule_id = entry.get("RuleID", "")
            file = entry.get("File", "")
            author = entry.get("Author", "")
            link = entry.get("Link", "")

            # Markdown-safe link
            link_md = f"[Link]({link})" if link else ""

            # Escape pipe characters in data
            file = file.replace("|", "\\|")
            author = author.replace("|", "\\|")

            table += f"| {rule_id} | {file} | {author} | {link_md} |\n"
            total_rows += 1
        if total_rows == 0:
            return
        else:
            return table

    def format_trufflehog_report(self, report):
        scan_code_change = get_env_variable("SCAN_CODE_CHANGE", False)
        hashes = []

        if str(scan_code_change).lower() in ("1", "true", "yes"):
            self.logger.info("Fetching commit hashes for code changes.")
            target_branch = get_env_variable("CI_MERGE_REQUEST_TARGET_BRANCH_NAME")
            diff_base_sha = get_env_variable("CI_MERGE_REQUEST_DIFF_BASE_SHA")
            commit_sha = get_env_variable("CI_COMMIT_SHA")

            subprocess.run(
                ["git", "fetch", "origin", target_branch],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            result = subprocess.run(
                ["git", "log", "--pretty=format:%H", f"{diff_base_sha}..{commit_sha}"],
                stdout=subprocess.PIPE,
                check=True,
                text=True,
            )
            hashes = result.stdout.strip().splitlines()
            self.logger.info(f"Found {len(hashes)} commit hashes for code changes.")

        # Start markdown table
        table = "| RuleID | File | Author | Link |\n"
        table += "| ------ | ---- | ------ | ---- |\n"
        total_rows = 0

        for entry in report:
            metadata = entry.get("SourceMetadata", {}).get("Data", {}).get("Git", {})
            commit_hash = metadata.get("commit", "")
            file_path = metadata.get("file", "")
            email = metadata.get("email", "")

            # Skip if SCAN_CODE_CHANGE is enabled and commit not in range
            if hashes and commit_hash not in hashes:
                continue

            rule_id = entry.get("DetectorName", "")
            author_name = self.extract_name_from_email(email)
            link = self.create_gitlab_link(commit_hash, file_path)

            # Escape markdown special chars
            file_path = file_path.replace("|", "\\|")
            author_name = author_name.replace("|", "\\|")
            link_md = f"[Link]({link})" if link else ""

            table += f"| {rule_id} | {file_path} | {author_name} | {link_md} |\n"
            total_rows += 1

        return table if total_rows > 0 else None

    def extract_name_from_email(self, email: str) -> str:
        """Extracts the name part from a full email string."""
        match = re.match(r"(.+?)\s*<.*?>", email)
        return match.group(1) if match else email

    def create_gitlab_link(self, commit_hash: str, file_path: str) -> str:
        """Generates a GitLab-style link to a specific file at a commit."""
        repo_url = get_env_variable("CI_REPOSITORY_URL")
        if not repo_url or "git@" in repo_url:
            return ""  # unsupported format or missing
        # Convert to browser format if needed
        repo_url = repo_url.replace(".git", "").replace("https://", "https://")
        # Convert GitLab SSH to HTTPS if necessary
        if repo_url.startswith("git@gitlab.com:"):
            repo_url = repo_url.replace(
                "git@gitlab.com:", "https://gitlab.com/"
            ).replace(".git", "")

        return (
            f"{repo_url}/-/blob/{commit_hash}/{file_path}"
            if commit_hash and file_path
            else ""
        )
