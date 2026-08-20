from scripts.check_pr_description import validate_description


def test_accepts_real_markdown_line_breaks():
    assert validate_description("## Summary\n\n- A readable change\n") == []


def test_rejects_literal_escaped_newlines():
    errors = validate_description(r"## Summary\n- An unreadable change")

    assert len(errors) == 1
    assert "literal \\n" in errors[0]


def test_rejects_empty_description():
    assert validate_description("  \n") == [
        "The pull request description must not be empty."
    ]
