import pytest
from unittest.mock import patch, MagicMock
import requests as real_requests

# ── scraper ──────────────────────────────────────────────────────────────────

def _mock_jina(text: str, status: int = 200):
    mock = MagicMock()
    mock.status_code = status
    mock.text = text
    mock.raise_for_status = MagicMock(
        side_effect=real_requests.HTTPError() if status >= 400 else None
    )
    return mock


@patch("app.scraper.requests.get")
def test_scraper_returns_content_for_github(mock_get):
    mock_get.return_value = _mock_jina("# cool-ml-repo\nA machine learning library for Python.")
    from app.scraper import fetch_content
    result = fetch_content("https://github.com/user/cool-ml-repo")
    assert result is not None
    assert "machine learning" in result


@patch("app.scraper.requests.get")
def test_scraper_truncates_at_max_chars(mock_get):
    long_text = "A" * 3000
    mock_get.return_value = _mock_jina(long_text)
    from app.scraper import fetch_content
    result = fetch_content("https://github.com/user/repo")
    assert len(result) == 1500


@patch("app.scraper.requests.get")
def test_scraper_returns_none_on_login_wall(mock_get):
    mock_get.return_value = _mock_jina("Sign in to LinkedIn to see this profile.")
    from app.scraper import fetch_content
    result = fetch_content("https://linkedin.com/in/vishal")
    assert result is None


@patch("app.scraper.requests.get")
def test_scraper_returns_none_on_empty_content(mock_get):
    mock_get.return_value = _mock_jina("   ")
    from app.scraper import fetch_content
    result = fetch_content("https://instagram.com/p/abc")
    assert result is None


@patch("app.scraper.requests.get")
def test_scraper_returns_none_on_content_too_short(mock_get):
    mock_get.return_value = _mock_jina("Hi")
    from app.scraper import fetch_content
    result = fetch_content("https://example.com")
    assert result is None


@patch("app.scraper.requests.get")
def test_scraper_returns_none_on_network_error(mock_get):
    mock_get.side_effect = real_requests.RequestException("timeout")
    from app.scraper import fetch_content
    result = fetch_content("https://github.com/user/repo")
    assert result is None


@patch("app.scraper.requests.get")
def test_scraper_prefixes_bare_url_with_https(mock_get):
    mock_get.return_value = _mock_jina("Some article content that is long enough to pass.")
    from app.scraper import fetch_content
    fetch_content("github.com/user/repo")
    called_url = mock_get.call_args[0][0]
    assert called_url == "https://r.jina.ai/https://github.com/user/repo"


@patch("app.scraper.requests.get")
def test_scraper_detects_join_now_as_blocked(mock_get):
    mock_get.return_value = _mock_jina("Join now to see this LinkedIn post and connect.")
    from app.scraper import fetch_content
    result = fetch_content("https://linkedin.com/posts/abc")
    assert result is None


# ── get_topic in link_handler ─────────────────────────────────────────────────

def _mock_groq_topic(topic: str):
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {
        "choices": [{"message": {"content": topic}}]
    }
    return mock


@patch("app.handlers.link_handler.http_requests.post")
@patch("app.scraper.requests.get")
def test_get_topic_returns_groq_summary_when_jina_works(mock_jina, mock_groq):
    mock_jina.return_value = _mock_jina("A fast machine learning library for Python developers.")
    mock_groq.return_value = _mock_groq_topic("Fast ML library for Python")
    from app.handlers.link_handler import get_topic
    topic = get_topic("https://github.com/user/repo", "github")
    assert topic == "Fast ML library for Python"


@patch("app.scraper.requests.get")
def test_get_topic_falls_back_when_jina_blocked(mock_jina):
    mock_jina.return_value = _mock_jina("Log in to LinkedIn to view this profile.")
    from app.handlers.link_handler import get_topic
    topic = get_topic("https://linkedin.com/in/vishal", "linkedin")
    assert topic == "LinkedIn profile or post"


@patch("app.scraper.requests.get")
def test_get_topic_falls_back_for_instagram(mock_jina):
    mock_jina.return_value = _mock_jina("Log in to see this photo.")
    from app.handlers.link_handler import get_topic
    topic = get_topic("https://instagram.com/p/abc", "instagram")
    assert topic == "Instagram post"


@patch("app.handlers.link_handler.http_requests.post")
@patch("app.scraper.requests.get")
def test_get_topic_falls_back_when_groq_fails(mock_jina, mock_groq):
    mock_jina.return_value = _mock_jina("A" * 200)
    mock_groq.side_effect = Exception("groq error")
    from app.handlers.link_handler import get_topic
    topic = get_topic("https://github.com/user/repo", "github")
    assert topic == "GitHub repository"


# ── handle_link with topic ────────────────────────────────────────────────────

@patch("app.handlers.link_handler._get_sheet")
@patch("app.handlers.link_handler.get_topic")
def test_handle_link_row_has_six_columns(mock_topic, mock_sheet):
    mock_topic.return_value = "Cool ML library for Python"
    mock_sheet.return_value = MagicMock()

    from app.handlers.link_handler import handle_link
    handle_link("https://github.com/user/cool-ml-repo")

    row = mock_sheet.return_value.append_row.call_args[0][0]
    assert len(row) == 6   # timestamp, url, type, domain, note, topic


@patch("app.handlers.link_handler._get_sheet")
@patch("app.handlers.link_handler.get_topic")
def test_handle_link_topic_in_column_f(mock_topic, mock_sheet):
    mock_topic.return_value = "Fast ML library for Python"
    mock_sheet.return_value = MagicMock()

    from app.handlers.link_handler import handle_link
    handle_link("https://github.com/user/repo")

    row = mock_sheet.return_value.append_row.call_args[0][0]
    assert row[5] == "Fast ML library for Python"   # column F (index 5)


@patch("app.handlers.link_handler._get_sheet")
@patch("app.handlers.link_handler.get_topic")
def test_handle_link_reply_includes_topic(mock_topic, mock_sheet):
    mock_topic.return_value = "React hooks tutorial"
    mock_sheet.return_value = MagicMock()

    from app.handlers.link_handler import handle_link
    reply = handle_link("https://medium.com/article/react-hooks")

    assert "React hooks tutorial" in reply
    assert "Topic:" in reply


@patch("app.handlers.link_handler._get_sheet")
@patch("app.handlers.link_handler.get_topic")
def test_handle_link_fallback_topic_saved_for_instagram(mock_topic, mock_sheet):
    mock_topic.return_value = "Instagram post"
    mock_sheet.return_value = MagicMock()

    from app.handlers.link_handler import handle_link
    handle_link("https://www.instagram.com/p/abc123")

    row = mock_sheet.return_value.append_row.call_args[0][0]
    assert row[5] == "Instagram post"
