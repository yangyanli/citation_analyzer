import pytest
from unittest.mock import patch
from backend.core.cli import setup_parser, prompt_model_selection, wrap_text


def test_setup_parser_valid_args():
    parser = setup_parser()
    args = parser.parse_args(["--user_id", "test_user", "--estimate_only"])
    assert args.user_id == "test_user"
    assert args.estimate_only is True
    assert args.paper is None
    assert args.start_phase == 0
    assert args.total_citations_to_add == "all"


def test_setup_parser_mutually_exclusive():
    parser = setup_parser()
    with pytest.raises(SystemExit):
        # Should exit if both user_id and paper are provided
        parser.parse_args(["--user_id", "test_user", "--paper", "test_paper"])

    with pytest.raises(SystemExit):
        # Should exit if neither user_id nor paper are provided
        parser.parse_args(["--estimate_only"])


def test_setup_parser_phase_isolation():
    parser = setup_parser()
    args = parser.parse_args(["--user_id", "test_user", "--wipe_phase", "3", "--run_only_phase", "3"])
    assert args.wipe_phase == 3
    assert args.run_only_phase == 3

    with pytest.raises(SystemExit):
        # Wiping phase 1 should be rejected by choices
        parser.parse_args(["--user_id", "test_user", "--wipe_phase", "1"])


def test_setup_parser_all_flags():
    parser = setup_parser()
    args = parser.parse_args(
        [
            "--paper",
            "Attention Is All You Need",
            "--delete",
            "--reset-db",
            "--resolve_arxiv",
            "--group_id",
            "5",
            "--total_citations_to_add",
            "100",
            "--model",
            "gemini-1.5-pro",
            "--domain",
            "Deep Learning",
            "--start_phase",
            "2",
            "--non-interactive",
            "--generate_criteria_only",
            "--config",
            "conf.json",
        ]
    )
    assert args.paper == "Attention Is All You Need"
    assert args.delete is True
    assert getattr(args, "reset_db", False) is True
    assert args.resolve_arxiv is True
    assert args.group_id == 5
    assert args.total_citations_to_add == "100"
    assert args.model == "gemini-1.5-pro"
    assert args.domain == "Deep Learning"
    assert args.start_phase == 2
    assert getattr(args, "non_interactive", False) is True
    assert args.generate_criteria_only is True
    assert args.config == "conf.json"


@patch("builtins.input", return_value="0")
def test_prompt_model_selection_abort(mock_input):
    assert prompt_model_selection("gemini-2.5-flash") is None


@patch("builtins.input", return_value="")
def test_prompt_model_selection_default(mock_input):
    assert prompt_model_selection("gemini-2.5-flash") == "gemini-2.5-flash"


@patch("builtins.input", return_value="1")
def test_prompt_model_selection_index(mock_input):
    from backend.core.cost import MODEL_PRICING

    first_model = list(MODEL_PRICING.keys())[0]
    assert prompt_model_selection("default") == first_model


def test_wrap_text():
    text = "This is a very long text that needs to be wrapped properly at the given width so it doesn't overflow."
    lines = wrap_text(text, width=20)
    assert len(lines) > 1
    assert "This is a very long" in lines[0] or "This is a very" in lines[0]

    short_text = "Short text."
    assert wrap_text(short_text, width=50) == ["Short text."]
