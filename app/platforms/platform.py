from utils.get_env_variable import get_env_variable
from platforms.gitlab import Gitlab


class Platform:
    def __init__(self, platform_name, logger):
        self.platform_name = platform_name
        self.logger = logger

    def comment_on_merge_request(self, report,tool_name):
        if self.platform_name == "gitlab":
            try:
                gitlab_url = get_env_variable("GITLAB_URL")
            except EnvironmentError:
                self.logger.info("GITLAB_URL is not set. Using https://gitlab.com.")
                gitlab_url = "https://gitlab.com"
            try:
                gitlab_token = get_env_variable("GITLAB_PRIVATE_TOKEN")
            except EnvironmentError:
                self.logger.error("GITLAB_PRIVATE_TOKEN is not set.")
                exit(2)
            gitlab = Gitlab(gitlab_url, gitlab_token, self.logger)
            gitlab.comment_on_merge_request(report,tool_name)

        else:
            raise NotImplementedError(f"Platform {self.platform_name} not supported.")
