"""Tests for verify_notable_claim — the 4-stage author verification pipeline."""

from unittest.mock import patch, MagicMock
import json
from backend.pipeline.phase_2_authors import verify_notable_claim


def _make_wiki_response(extract_text):
    """Create a mock Wikipedia API JSON response."""
    data = json.dumps(
        {
            "query": {
                "pages": {
                    "12345": {"pageid": 12345, "title": "Test", "extract": extract_text}
                }
            }
        }
    ).encode()
    mock = MagicMock()
    mock.__enter__.return_value = mock
    mock.__exit__.return_value = False
    mock.read.return_value = data
    return mock


def _make_html_response(html_text):
    """Create a mock HTTP response with HTML content."""
    mock = MagicMock()
    mock.__enter__.return_value = mock
    mock.__exit__.return_value = False
    mock.read.return_value = html_text.encode()
    return mock


class TestHomepageVerification:
    """Stage 1: Homepage verification."""

    @patch("urllib.request.urlopen")
    def test_homepage_contains_keyword_verifies(self, mock_urlopen):
        mock_urlopen.return_value = _make_html_response(
            "<p>He is an IEEE Fellow since 2015</p>"
        )
        ok, evidence, urls = verify_notable_claim(
            "Test Author", "IEEE Fellow (2015)", "https://example.com", ["ieee fellow"]
        )
        assert ok is True
        assert "[AI Verified]" in evidence
        assert "https://example.com" in urls

    @patch("requests.get")
    @patch("urllib.request.urlopen")
    def test_homepage_missing_keyword_falls_through(self, mock_urlopen, mock_requests):
        """Homepage doesn't contain the keyword — should NOT verify at stage 1."""
        # First call = homepage (no keyword), second call = Wikipedia (no page)
        wiki_response = _make_wiki_response("")
        homepage_response = _make_html_response("<p>Just a personal page</p>")
        mock_urlopen.side_effect = [homepage_response, wiki_response]
        # Google Scholar returns no match
        mock_resp = MagicMock()
        mock_resp.text = "No results"
        mock_requests.return_value = mock_resp

        ok, evidence, urls = verify_notable_claim(
            "Test Author",
            "IEEE Fellow (2015)",
            "https://example.com",
            ["ieee fellow"],
            "",
        )
        # Should fall through to later stages and ultimately fail
        assert ok is False
        assert len(urls) >= 2  # At least homepage + wikipedia

    @patch("urllib.request.urlopen")
    def test_homepage_timeout_falls_through(self, mock_urlopen):
        """Homepage times out — should gracefully continue to Wikipedia."""
        mock_urlopen.side_effect = [
            TimeoutError("Connection timed out"),  # homepage
            _make_wiki_response("This person is an IEEE Fellow."),  # wikipedia
        ]
        ok, evidence, urls = verify_notable_claim(
            "Test Author", "IEEE Fellow", "https://example.com", ["ieee fellow"]
        )
        assert ok is True
        assert "[AI Verified]" in evidence


class TestWikipediaVerification:
    """Stage 2: Wikipedia verification."""

    @patch("urllib.request.urlopen")
    def test_wikipedia_full_article_contains_keyword(self, mock_urlopen):
        """Full article (not just intro) should be searched."""
        mock_urlopen.return_value = _make_wiki_response(
            "Early life... Education... Career... He was named an IEEE Fellow in 2015."
        )
        ok, evidence, urls = verify_notable_claim(
            "Test Author",
            "IEEE Fellow (2015)",
            "",
            ["ieee fellow"],  # no homepage
        )
        assert ok is True
        assert "[AI Verified]" in evidence

    @patch("requests.get")
    @patch("urllib.request.urlopen")
    def test_wikipedia_no_page_falls_through(self, mock_urlopen, mock_requests):
        """Missing Wikipedia page (pageid=-1) — should fall through."""
        data = json.dumps({"query": {"pages": {"-1": {"missing": ""}}}}).encode()
        mock = MagicMock()
        mock.__enter__.return_value = mock
        mock.__exit__.return_value = False
        mock.read.return_value = data
        mock_urlopen.return_value = mock
        # Google Scholar returns no match
        mock_resp = MagicMock()
        mock_resp.text = "No results"
        mock_requests.return_value = mock_resp
        ok, evidence, urls = verify_notable_claim(
            "Unknown Person", "IEEE Fellow", "", ["ieee fellow"], ""
        )
        assert ok is False  # No Wikipedia, no other sources → reject


class TestVerificationURLStage:
    """Stage 3: LLM-provided verification URL."""

    @patch("urllib.request.urlopen")
    def test_verification_url_contains_keyword(self, mock_urlopen):
        wiki_response = _make_wiki_response("")  # empty Wikipedia
        verify_response = _make_html_response(
            "<p>IEEE Fellow Directory: Test Author</p>"
        )
        mock_urlopen.side_effect = [wiki_response, verify_response]

        ok, evidence, urls = verify_notable_claim(
            "Test Author",
            "IEEE Fellow",
            "",
            ["ieee fellow"],
            "https://ieee.org/fellows",
        )
        assert ok is True
        assert "[AI Verified]" in evidence

    @patch("urllib.request.urlopen")
    def test_compound_verification_url_sanitized(self, mock_urlopen):
        """LLM stuffs multiple URLs with semicolons — only first should be extracted."""
        wiki_response = _make_wiki_response("")
        verify_response = _make_html_response(
            "<p>IEEE Fellow: Test Author listed here</p>"
        )
        mock_urlopen.side_effect = [wiki_response, verify_response]

        ok, evidence, urls = verify_notable_claim(
            "Test Author",
            "IEEE Fellow",
            "",
            ["ieee fellow"],
            "https://ieee.org/fellows; https://other.org/page (search for Author)",
        )
        assert ok is True
        # The clean URL should be just the first one
        assert any("ieee.org/fellows" in u for u in urls)
        assert not any("other.org" in u for u in urls)

    @patch("urllib.request.urlopen")
    def test_hallucinated_url_404_falls_through(self, mock_urlopen):
        """LLM provides a URL that 404s — should fall through to Google Scholar."""
        wiki_response = _make_wiki_response("")
        mock_urlopen.side_effect = [
            wiki_response,  # Wikipedia: empty
            Exception("HTTP Error 404: Not Found"),  # Verification URL: 404
        ]
        # Google Scholar step uses requests, mock that separately
        with patch("requests.get") as mock_requests:
            mock_resp = MagicMock()
            mock_resp.text = "No results found"
            mock_requests.return_value = mock_resp
            ok, evidence, urls = verify_notable_claim(
                "Test Author",
                "IEEE Fellow",
                "",
                ["ieee fellow"],
                "https://ieee.org/fake-page.pdf",
            )
        assert ok is False  # All stages failed


class TestGoogleScholarFallback:
    """Stage 4: Google Scholar search."""

    @patch("requests.get")
    @patch("urllib.request.urlopen")
    def test_google_scholar_finds_keyword(self, mock_urlopen, mock_requests):
        """Google Scholar returns a page mentioning the fellowship."""
        wiki_response = _make_wiki_response("")
        mock_urlopen.return_value = wiki_response

        mock_resp = MagicMock()
        mock_resp.text = "<div>Nanning Zheng, IEEE Fellow, has contributed...</div>"
        mock_requests.return_value = mock_resp

        ok, evidence, urls = verify_notable_claim(
            "Nanning Zheng", "IEEE Fellow (2004)", "", ["ieee fellow"], ""
        )
        assert ok is True
        assert "[AI Verified]" in evidence
        assert any("scholar.google.com" in u for u in urls)

    @patch("requests.get")
    @patch("urllib.request.urlopen")
    def test_google_scholar_no_match_rejects(self, mock_urlopen, mock_requests):
        """Google Scholar returns no relevant results — should reject."""
        wiki_response = _make_wiki_response("")
        mock_urlopen.return_value = wiki_response

        mock_resp = MagicMock()
        mock_resp.text = "<div>No results found</div>"
        mock_requests.return_value = mock_resp

        ok, evidence, urls = verify_notable_claim(
            "Fake Person", "Turing Award winner", "", ["turing award"], ""
        )
        assert ok is False
        assert "Failed verification" in evidence


class TestEdgeCases:
    """Edge cases and pass-through logic."""

    def test_no_keywords_passes_through(self):
        """No verification_keywords → no verification needed, pass through."""
        ok, evidence, urls = verify_notable_claim(
            "Test Author", "Some evidence", "", []
        )
        assert ok is True
        assert evidence == "Some evidence"  # No badge added

    def test_keywords_not_in_evidence_passes_through(self):
        """Keywords don't appear in evidence text → claims_in_evidence is empty → pass through."""
        ok, evidence, urls = verify_notable_claim(
            "Test Author",
            "Some unrelated evidence",
            "",
            ["turing award"],  # "turing award" NOT in "Some unrelated evidence"
        )
        assert ok is True
        assert "[AI Verified]" not in evidence


class TestFlexibleKeywordMatching:
    """Tests for word-level keyword matching (Fix 1)."""

    @patch("urllib.request.urlopen")
    def test_fellow_of_the_ieee_matches_ieee_fellow(self, mock_urlopen):
        """'Fellow of the IEEE' should match keyword 'ieee fellow'."""
        mock_urlopen.return_value = _make_html_response(
            "<p>He was elected Fellow of the IEEE in 2010.</p>"
        )
        ok, evidence, urls = verify_notable_claim(
            "Test Author", "IEEE Fellow", "https://example.com", ["ieee fellow"]
        )
        assert ok is True
        assert "[AI Verified]" in evidence

    @patch("urllib.request.urlopen")
    def test_best_paper_at_cvpr_matches_best_paper(self, mock_urlopen):
        """'Best Paper Award at CVPR 2018' should match keyword 'best paper'."""
        mock_urlopen.return_value = _make_html_response(
            "<p>Received the Best Paper Award at CVPR 2018.</p>"
        )
        ok, evidence, urls = verify_notable_claim(
            "Test Author",
            "best paper award winner",
            "https://example.com",
            ["best paper"],
        )
        assert ok is True
        assert "[AI Verified]" in evidence

    @patch("urllib.request.urlopen")
    def test_acm_fellow_class_matches_acm_fellow(self, mock_urlopen):
        """'ACM Fellow Class of 2015' should match keyword 'acm fellow'."""
        mock_urlopen.return_value = _make_html_response(
            "<p>Named ACM Fellow, Class of 2015 for contributions to graphics.</p>"
        )
        ok, evidence, urls = verify_notable_claim(
            "Test Author", "ACM Fellow", "https://example.com", ["acm fellow"]
        )
        assert ok is True
        assert "[AI Verified]" in evidence


class TestAbbreviatedNameHelpers:
    """Tests for _is_abbreviated_name and _get_surname helpers."""

    def test_abbreviated_names_detected(self):
        from backend.pipeline.phase_2_authors import _is_abbreviated_name
        assert _is_abbreviated_name("H. Seidel") is True
        assert _is_abbreviated_name("F. Porikli") is True
        assert _is_abbreviated_name("M. Shah") is True
        assert _is_abbreviated_name("C. Bregler") is True
        assert _is_abbreviated_name("S. S. Sastry") is True

    def test_full_names_not_abbreviated(self):
        from backend.pipeline.phase_2_authors import _is_abbreviated_name
        assert _is_abbreviated_name("Hans-Peter Seidel") is False
        assert _is_abbreviated_name("Kaiming He") is False
        assert _is_abbreviated_name("Takeo Kanade") is False

    def test_surname_extraction(self):
        from backend.pipeline.phase_2_authors import _get_surname
        assert _get_surname("H. Seidel") == "Seidel"
        assert _get_surname("F. Porikli") == "Porikli"
        assert _get_surname("S. S. Sastry") == "Sastry"
        assert _get_surname("Kaiming He") == "He"


class TestAbbreviatedNameWikipediaFallback:
    """Tests for Wikipedia opensearch fallback when abbreviated name has no page."""

    @patch("urllib.request.urlopen")
    def test_abbreviated_name_triggers_opensearch(self, mock_urlopen):
        """'H. Seidel' should trigger opensearch and find 'Hans-Peter Seidel'."""
        # First call: exact name lookup returns no page
        no_page = json.dumps({"query": {"pages": {"-1": {"missing": ""}}}}).encode()
        no_page_mock = MagicMock()
        no_page_mock.__enter__ = MagicMock(return_value=no_page_mock)
        no_page_mock.__exit__ = MagicMock(return_value=False)
        no_page_mock.read.return_value = no_page

        # Second call: opensearch returns candidates
        opensearch = json.dumps([
            "Seidel",
            ["Hans-Peter Seidel", "Seidel triangle", "Seidel matrix"],
        ]).encode()
        opensearch_mock = MagicMock()
        opensearch_mock.__enter__ = MagicMock(return_value=opensearch_mock)
        opensearch_mock.__exit__ = MagicMock(return_value=False)
        opensearch_mock.read.return_value = opensearch

        # Third call: full article for 'Hans-Peter Seidel'
        wiki_mock = _make_wiki_response(
            "Hans-Peter Seidel is a German computer scientist. "
            "He is an ACM Fellow and IEEE Fellow."
        )

        mock_urlopen.side_effect = [no_page_mock, opensearch_mock, wiki_mock]

        ok, evidence, urls = verify_notable_claim(
            "H. Seidel", "ACM Fellow", "", ["acm fellow"]
        )
        assert ok is True
        assert "[AI Verified]" in evidence
