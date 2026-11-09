
import os
from github import Github, Auth
from github import GithubException


class GitHubServiceError(Exception):
    """Raised when a GitHub operation fails."""


def get_github_client():
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise GitHubServiceError(
            "GitHub token is not configured on the backend."
        )

    try:
        return Github(auth=Auth.Token(token))
    except Exception as exc:
        raise GitHubServiceError(
            "Unable to initialize GitHub client."
        ) from exc


def get_authenticated_user():
    client = get_github_client()

    try:
        user = client.get_user()
        return {
            "login": user.login,
            "name": user.name,
            "avatar_url": user.avatar_url
        }
    except GithubException as exc:
        raise GitHubServiceError(
            f"GitHub authentication failed: HTTP {exc.status}"
        ) from exc
    finally:
        client.close()


def get_user_repositories():
    client = get_github_client()

    try:
        repositories = client.get_user().get_repos(
            type="owner",
            sort="updated"
        )

        return [
            {
                "id": repo.id,
                "name": repo.name,
                "full_name": repo.full_name,
                "private": repo.private,
                "default_branch": repo.default_branch,
                "html_url": repo.html_url
            }
            for repo in repositories
        ]
    except GithubException as exc:
        raise GitHubServiceError(
            f"Unable to fetch repositories: HTTP {exc.status}"
        ) from exc
    finally:
        client.close()


def get_repository_branches(owner, repo_name):
    client = get_github_client()

    try:
        repository = client.get_repo(f"{owner}/{repo_name}")

        return [
            {
                "name": branch.name,
                "protected": branch.protected
            }
            for branch in repository.get_branches()
        ]
    except GithubException as exc:
        raise GitHubServiceError(
            f"Unable to fetch branches: HTTP {exc.status}"
        ) from exc
    finally:
        client.close()


def trigger_github_workflow(owner, repo_name, branch="main"):
    client = get_github_client()

    try:
        repository = client.get_repo(f"{owner}/{repo_name}")
        workflow = repository.get_workflow("ci.yml")

        triggered = workflow.create_dispatch(ref=branch)

        return {
            "triggered": bool(triggered),
            "repository": repository.full_name,
            "workflow": workflow.name,
            "branch": branch
        }

    except GithubException as exc:
        raise GitHubServiceError(
            f"Unable to trigger workflow: HTTP {exc.status}"
        ) from exc

    finally:
        client.close()


def get_github_workflow_runs(owner, repo_name, branch=None):
    client = get_github_client()

    try:
        repository = client.get_repo(f"{owner}/{repo_name}")
        workflow = repository.get_workflow("ci.yml")

        if branch:
            runs = workflow.get_runs(branch=branch)
        else:
            runs = workflow.get_runs()

        result = []

        for run in runs[:20]:
            result.append({
                "id": run.id,
                "name": run.name,
                "branch": run.head_branch,
                "event": run.event,
                "status": run.status,
                "conclusion": run.conclusion,
                "url": run.html_url,
                "created_at": run.created_at.isoformat()
            })

        return result

    except GithubException as exc:
        raise GitHubServiceError(
            f"Unable to fetch workflow runs: HTTP {exc.status}"
        ) from exc

    finally:
        client.close()
