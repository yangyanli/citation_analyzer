"""Tests for backend.core.config — name matching and cache utilities."""

from backend.core.config import is_same_person


class TestIsSamePerson:
    """Tests for the is_same_person self-citation detection."""

    def test_exact_match(self):
        assert is_same_person("Yangyan Li", "Yangyan Li") is True

    def test_case_insensitive(self):
        assert is_same_person("yangyan li", "Yangyan Li") is True

    def test_initial_match_first_name(self):
        """S2 often abbreviates first names: 'Yangyan Li' → 'Y. Li'."""
        assert is_same_person("Yangyan Li", "Y. Li") is True

    def test_initial_match_reverse(self):
        assert is_same_person("Y. Li", "Yangyan Li") is True

    def test_different_people_same_last_name(self):
        """Different first initial, same last name → not the same person."""
        assert is_same_person("Yangyan Li", "Jie Li") is False

    def test_completely_different(self):
        assert is_same_person("Yangyan Li", "John Smith") is False

    def test_empty_scholar_name(self):
        assert is_same_person("", "Yangyan Li") is False

    def test_empty_s2_name(self):
        assert is_same_person("Yangyan Li", "") is False

    def test_none_scholar_name(self):
        assert is_same_person(None, "Yangyan Li") is False

    def test_none_s2_name(self):
        assert is_same_person("Yangyan Li", None) is False

    def test_both_none(self):
        assert is_same_person(None, None) is False

    def test_single_word_names(self):
        """Handle edge case of single-token names."""
        assert is_same_person("Madonna", "Madonna") is True

    def test_single_word_different(self):
        assert is_same_person("Madonna", "Adele") is False
