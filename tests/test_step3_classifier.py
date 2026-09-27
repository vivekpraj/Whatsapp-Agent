import pytest
from app.classifier import classify, extract_url


# --- Link detection ---

def test_https_url_classified_as_link():
    assert classify("https://github.com/user/repo") == "link"

def test_http_url_classified_as_link():
    assert classify("http://example.com") == "link"

def test_url_in_sentence_classified_as_link():
    assert classify("Check this out https://linkedin.com/in/vishal") == "link"

def test_instagram_url_classified_as_link():
    assert classify("https://www.instagram.com/p/abc123") == "link"

def test_bare_domain_classified_as_link():
    assert classify("github.com/user/cool-repo") == "link"


# --- Reminder detection ---

def test_remind_me_classified_as_reminder():
    assert classify("Remind me at 6pm to call John") == "reminder"

def test_reminder_word_classified():
    assert classify("Set a reminder for 9am Monday") == "reminder"

def test_tomorrow_classified_as_reminder():
    assert classify("tomorrow morning send report") == "reminder"

def test_tonight_classified_as_reminder():
    assert classify("tonight at 8pm watch the game") == "reminder"

def test_in_x_hours_classified_as_reminder():
    assert classify("remind me in 2 hours to check the oven") == "reminder"

def test_in_x_minutes_classified_as_reminder():
    assert classify("alert me in 30 minutes") == "reminder"

def test_day_of_week_classified_as_reminder():
    assert classify("remind me on Friday to submit the report") == "reminder"


# --- Question / fallback ---

def test_plain_question_classified_as_question():
    assert classify("What is the capital of France?") == "question"

def test_greeting_classified_as_question():
    assert classify("Hello, how are you?") == "question"

def test_random_text_classified_as_question():
    assert classify("Tell me a joke") == "question"


# --- Link priority over reminder ---

def test_url_with_reminder_words_classified_as_link():
    assert classify("Remind me to check https://github.com/user/repo") == "link"


# --- extract_url helper ---

def test_extract_url_returns_url():
    url = extract_url("Save this https://github.com/cool/repo for later")
    assert url == "https://github.com/cool/repo"

def test_extract_url_returns_none_when_no_url():
    assert extract_url("Just a plain message") is None
