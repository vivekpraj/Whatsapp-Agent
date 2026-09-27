import pytest
from unittest.mock import patch, MagicMock
from app.handlers.link_handler import (
    classify_link_type,
    extract_domain,
    extract_note,
    handle_link,
)


# --- classify_link_type ---

def test_github_domain():
    assert classify_link_type("github.com") == "github"

def test_linkedin_domain():
    assert classify_link_type("linkedin.com") == "linkedin"

def test_instagram_domain():
    assert classify_link_type("instagram.com") == "instagram"

def test_medium_domain():
    assert classify_link_type("medium.com") == "article"

def test_youtube_domain():
    assert classify_link_type("youtube.com") == "article"

def test_unknown_domain_returns_other():
    assert classify_link_type("somerandomblog.io") == "other"

def test_subdomain_github():
    assert classify_link_type("gist.github.com") == "github"


# --- extract_domain ---

def test_extract_domain_from_https_url():
    assert extract_domain("https://github.com/user/repo") == "github.com"

def test_extract_domain_strips_www():
    assert extract_domain("https://www.instagram.com/p/abc") == "instagram.com"

def test_extract_domain_bare():
    assert extract_domain("github.com/user/repo") == "github.com"

def test_extract_domain_linkedin():
    assert extract_domain("https://www.linkedin.com/in/vishal") == "linkedin.com"


# --- extract_note ---

def test_extract_note_returns_surrounding_text():
    note = extract_note("Check this https://github.com/cool/repo great project", "https://github.com/cool/repo")
    assert note == "Check this  great project".strip() or "Check this" in note

def test_extract_note_empty_when_only_url():
    note = extract_note("https://github.com/user/repo", "https://github.com/user/repo")
    assert note == ""


# --- handle_link (Google Sheets mocked) ---

@patch("app.handlers.link_handler.get_topic")
@patch("app.handlers.link_handler._get_sheet")
def test_handle_link_github_saves_and_replies(mock_get_sheet, mock_topic):
    mock_sheet = MagicMock()
    mock_get_sheet.return_value = mock_sheet
    mock_topic.return_value = "Cool ML repo"

    reply = handle_link("https://github.com/user/cool-ml-repo")

    assert mock_sheet.append_row.called
    row = mock_sheet.append_row.call_args[0][0]

    assert row[1] == "https://github.com/user/cool-ml-repo"   # URL
    assert row[2] == "github"                                   # type
    assert row[3] == "github.com"                               # domain
    assert "Github" in reply or "github" in reply.lower()


@patch("app.handlers.link_handler.get_topic")
@patch("app.handlers.link_handler._get_sheet")
def test_handle_link_instagram_saves_correctly(mock_get_sheet, mock_topic):
    mock_sheet = MagicMock()
    mock_get_sheet.return_value = mock_sheet
    mock_topic.return_value = "Instagram post"

    reply = handle_link("https://www.instagram.com/p/abc123")

    row = mock_sheet.append_row.call_args[0][0]
    assert row[2] == "instagram"
    assert "Instagram" in reply or "instagram" in reply.lower()


@patch("app.handlers.link_handler.get_topic")
@patch("app.handlers.link_handler._get_sheet")
def test_handle_link_with_note(mock_get_sheet, mock_topic):
    mock_sheet = MagicMock()
    mock_get_sheet.return_value = mock_sheet
    mock_topic.return_value = "Some topic"

    handle_link("cool ML repo https://github.com/user/repo")

    row = mock_sheet.append_row.call_args[0][0]
    assert "cool ML repo" in row[4]    # note column


@patch("app.handlers.link_handler.get_topic")
@patch("app.handlers.link_handler._get_sheet")
def test_handle_link_unknown_domain_type_other(mock_get_sheet, mock_topic):
    mock_sheet = MagicMock()
    mock_get_sheet.return_value = mock_sheet
    mock_topic.return_value = "Web link"

    handle_link("https://randomsite.xyz/article/123")

    row = mock_sheet.append_row.call_args[0][0]
    assert row[2] == "other"


def test_handle_link_no_url_returns_error():
    reply = handle_link("just a plain message no link")
    assert "Could not find" in reply


@patch("app.handlers.link_handler.get_topic")
@patch("app.handlers.link_handler._get_sheet")
def test_handle_link_row_has_six_columns(mock_get_sheet, mock_topic):
    mock_sheet = MagicMock()
    mock_get_sheet.return_value = mock_sheet
    mock_topic.return_value = "LinkedIn profile or post"

    from app.handlers.link_handler import handle_link
    handle_link("https://linkedin.com/in/vishal")

    row = mock_sheet.append_row.call_args[0][0]
    assert len(row) == 6    # timestamp, url, type, domain, note, topic
