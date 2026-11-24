import pytest

from backend import github_service


class FakeClient:
    def __init__(self, user=None, repositories=None, repository=None):
        self.user = user
        self.repositories = repositories or []
        self.repository = repository
        self.closed = False

    def get_user(self):
        return self.user

    def get_repo(self, name):
        return self.repository

    def close(self):
        self.closed = True


def test_missing_github_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with pytest.raises(
        github_service.GitHubServiceError,
        match="token is not configured"
    ):
        github_service.get_github_client()


def test_get_authenticated_user(monkeypatch):
    user = type("User", (), {
        "login": "test-user",
        "name": "Test User",
        "avatar_url": "https://example.com/avatar.png"
    })()

    client = FakeClient(user=user)

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setattr(github_service.Auth, "Token", lambda token: token)
    monkeypatch.setattr(
        github_service,
        "Github",
        lambda auth: client
    )

    result = github_service.get_authenticated_user()

    assert result == {
        "login": "test-user",
        "name": "Test User",
        "avatar_url": "https://example.com/avatar.png"
    }
    assert client.closed is True


def test_get_user_repositories(monkeypatch):
    repo = type("Repository", (), {
        "id": 123,
        "name": "Model-Setu",
        "full_name": "test-user/Model-Setu",
        "private": False,
        "default_branch": "main",
        "html_url": "https://github.com/test-user/Model-Setu"
    })()

    user = type("User", (), {
        "get_repos": lambda self, **kwargs: [repo]
    })()

    client = FakeClient(user=user)

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setattr(github_service.Auth, "Token", lambda token: token)
    monkeypatch.setattr(github_service, "Github", lambda auth: client)

    result = github_service.get_user_repositories()

    assert len(result) == 1
    assert result[0]["full_name"] == "test-user/Model-Setu"
    assert result[0]["default_branch"] == "main"
    assert client.closed is True


def test_get_repository_branches(monkeypatch):
    branches = [
        type("Branch", (), {"name": "main", "protected": True})(),
        type("Branch", (), {"name": "develop", "protected": False})()
    ]

    repository = type("Repository", (), {
        "get_branches": lambda self: branches
    })()

    client = FakeClient(repository=repository)

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setattr(github_service.Auth, "Token", lambda token: token)
    monkeypatch.setattr(github_service, "Github", lambda auth: client)

    result = github_service.get_repository_branches(
        "test-user",
        "Model-Setu"
    )

    assert result == [
        {"name": "main", "protected": True},
        {"name": "develop", "protected": False}
    ]
    assert client.closed is True


def test_trigger_github_workflow(monkeypatch):
    workflow = type("Workflow", (), {
        "name": "CI",
        "create_dispatch": lambda self, ref: True
    })()

    repository = type("Repository", (), {
        "full_name": "test-user/Model-Setu",
        "get_workflow": lambda self, name: workflow
    })()

    client = FakeClient(repository=repository)

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setattr(github_service.Auth, "Token", lambda token: token)
    monkeypatch.setattr(github_service, "Github", lambda auth: client)

    result = github_service.trigger_github_workflow(
        "test-user",
        "Model-Setu",
        "main"
    )

    assert result == {
        "triggered": True,
        "repository": "test-user/Model-Setu",
        "workflow": "CI",
        "branch": "main"
    }
    assert client.closed is True


def test_get_github_workflow_runs(monkeypatch):
    from datetime import datetime

    run = type("Run", (), {
        "id": 456,
        "name": "CI",
        "head_branch": "main",
        "event": "push",
        "status": "completed",
        "conclusion": "success",
        "html_url": "https://github.com/test-user/Model-Setu/actions/runs/456",
        "created_at": datetime(2026, 11, 24, 10, 0, 0)
    })()

    workflow = type("Workflow", (), {
        "get_runs": lambda self, **kwargs: [run]
    })()

    repository = type("Repository", (), {
        "get_workflow": lambda self, name: workflow
    })()

    client = FakeClient(repository=repository)

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setattr(github_service.Auth, "Token", lambda token: token)
    monkeypatch.setattr(github_service, "Github", lambda auth: client)

    result = github_service.get_github_workflow_runs(
        "test-user",
        "Model-Setu",
        "main"
    )

    assert len(result) == 1
    assert result[0]["id"] == 456
    assert result[0]["branch"] == "main"
    assert result[0]["conclusion"] == "success"
    assert result[0]["created_at"] == "2026-11-24T10:00:00"
    assert client.closed is True
