import json
from platforms.platform import Platform
from utils.detect_ci import detect_ci
from utils.get_env_variable import get_env_variable


def handle_report(tool_name, report, logger):
    logger.info(f"{tool_name} scan completed successfully.")
    logger.info(f"{tool_name} report generated.")

    if get_env_variable("PR_COMMENT", "false").lower() in ("1", "true", "yes"):
        logger.info(f"Posting {tool_name} report to PR comment.")
        platform = Platform(detect_ci(), logger)
        platform.comment_on_merge_request(report,tool_name)

    elif get_env_variable("PRINT_REPORT", "false").lower() in ("1", "true", "yes"):
        logger.info(f"Printing {tool_name} report to log.")
        print(json.dumps(report, indent=2))

    else:
        logger.info("Skipping PR comment posting and print in log.")
