import pytest

from app import cli


def test_create_admin_rejects_mismatched_passwords(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    answers = iter(["First-Password-1", "Second-Password-2"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": next(answers))

    exit_code = cli.main(["create-admin", "--email", "a@company.ru", "--full-name", "Админ"])

    assert exit_code == 1
    assert "не совпадают" in capsys.readouterr().err
