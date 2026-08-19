import pytest

from scripts.release_guard import changed_version, extract_version, git_file


def test_extract_version_accepts_project_version():
    assert extract_version('[project]\nversion = "0.13.0rc1"\n') == "0.13.0rc1"


def test_extract_version_rejects_missing_or_unsafe_values():
    with pytest.raises(ValueError, match="project version"):
        extract_version('[project]\nname = "django-orbit"\n')

    with pytest.raises(ValueError, match="valid release version"):
        extract_version('[project]\nversion = "0.13.0/issue-injection"\n')


def test_changed_version_returns_new_version_only_when_project_version_changed():
    base = '[project]\nversion = "0.12.1"\n'
    same = '[project]\nversion = "0.12.1"\n# unrelated change\n'
    release = '[project]\nversion = "0.13.0"\n'

    assert changed_version(base, same) is None
    assert changed_version(base, release) == "0.13.0"


def test_git_file_rejects_untrusted_revision_input():
    with pytest.raises(ValueError, match="full lowercase SHA-1"):
        git_file("HEAD; touch unexpected-file", "pyproject.toml")
