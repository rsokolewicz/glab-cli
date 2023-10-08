import os
import subprocess
import sys

import requests
from InquirerPy import inquirer

# Constants
ENV_VAR_NAME = "GITLAB_PERSONAL_ACCESS_TOKEN"


def validate_git_repo() -> None:
    is_git_repo = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    if is_git_repo.returncode != 0:
        print("Error: The current directory is not a Git repository.")
        sys.exit(1)

    remote_url = subprocess.getoutput("git config --get remote.origin.url")
    if "gitlab.com" not in remote_url:
        print("Error: The current Git repository is not hosted on GitLab.")
        sys.exit(1)


def get_personal_access_token() -> str:
    token = os.environ.get(ENV_VAR_NAME)

    if not token:
        print(f"Warning: Environment variable {ENV_VAR_NAME} not found.")
        print(
            f"Please set the {ENV_VAR_NAME} environment variable with your GitLab personal access token."
        )
        sys.exit(1)
    return token


def get_gitlab_project_id(token: str) -> str:
    remote_url = subprocess.getoutput("git config --get remote.origin.url")
    project_path = remote_url.split(":")[-1].replace(".git", "").replace("/", "%2F")

    headers = {"Private-Token": token}
    response = requests.get(
        f"https://gitlab.com/api/v4/projects/{project_path}", headers=headers
    )
    if response.status_code == 401:
        raise PermissionError(
            "Unauthorized access. Please check your GitLab personal access token."
        )

    return response.json()["id"]


def fetch_open_merge_requests(token: str) -> list[dict]:
    headers = {"Private-Token": token}
    project_id = get_gitlab_project_id(token)
    response = requests.get(
        f"https://gitlab.com/api/v4/projects/{project_id}/merge_requests?state=opened&per_page=50",
        headers=headers,
    )

    return response.json()


def display_merge_requests_and_select(mrs: dict) -> dict:
    choices = [
        {
            "name": f"!{mr['iid']} | {mr['author']['name']} | {mr['title']}",
            "value": mr,
        }
        for mr in mrs
    ]

    answer = inquirer.fuzzy(
        message="Select a merge request (start typing to search):",
        choices=choices,
    ).execute()
    return answer


def checkout_branch(branch_name: str) -> None:
    subprocess.run(["git", "checkout", branch_name], check=True)


def main() -> None:
    validate_git_repo()
    token = get_personal_access_token()
    mrs = fetch_open_merge_requests(token)
    selected_mr = display_merge_requests_and_select(mrs)
    checkout_branch(selected_mr["source_branch"])


if __name__ == "__main__":
    main()
