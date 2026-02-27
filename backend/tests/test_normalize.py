"""Tests for utils/normalize.py — storage, RAM and description normalization."""

from utils.normalize import normalize_description_units, normalize_ram, normalize_storage


class TestNormalizeStorage:
    """Tests for normalize_storage()."""

    def test_gb_uppercase(self):
        assert normalize_storage("512GB") == "512 Go"

    def test_go_lowercase(self):
        assert normalize_storage("512go") == "512 Go"

    def test_go_mixed_case(self):
        assert normalize_storage("512Go") == "512 Go"

    def test_digits_only(self):
        assert normalize_storage("512") == "512 Go"

    def test_with_space(self):
        assert normalize_storage("512 Go") == "512 Go"

    def test_tb_uppercase(self):
        assert normalize_storage("1TB") == "1 To"

    def test_to_lowercase(self):
        assert normalize_storage("1to") == "1 To"

    def test_to_with_space(self):
        assert normalize_storage("1 To") == "1 To"

    def test_none_returns_none(self):
        assert normalize_storage(None) is None

    def test_empty_string_returns_none(self):
        assert normalize_storage("") is None

    def test_whitespace_only_returns_none(self):
        assert normalize_storage("   ") is None

    def test_leading_trailing_spaces(self):
        assert normalize_storage("  256 GB  ") == "256 Go"

    def test_gb_lowercase(self):
        assert normalize_storage("128gb") == "128 Go"

    def test_non_matching_value_preserved(self):
        assert normalize_storage("N/A") == "N/A"

    def test_decimal_value(self):
        assert normalize_storage("1.5TB") == "1.5 To"


class TestNormalizeRam:
    """Tests for normalize_ram()."""

    def test_digits_only(self):
        assert normalize_ram("4") == "4 Go"

    def test_go_suffix(self):
        assert normalize_ram("4Go") == "4 Go"

    def test_gb_suffix(self):
        assert normalize_ram("4GB") == "4 Go"

    def test_go_with_space(self):
        assert normalize_ram("8 go") == "8 Go"

    def test_gb_uppercase(self):
        assert normalize_ram("16GB") == "16 Go"

    def test_none_returns_none(self):
        assert normalize_ram(None) is None

    def test_empty_string_returns_none(self):
        assert normalize_ram("") is None

    def test_whitespace_only_returns_none(self):
        assert normalize_ram("   ") is None

    def test_leading_trailing_spaces(self):
        assert normalize_ram("  8 GB  ") == "8 Go"

    def test_non_matching_value_preserved(self):
        assert normalize_ram("N/A") == "N/A"

    def test_tb_treated_as_go_for_ram(self):
        """RAM values with TB/To should still normalize to Go."""
        assert normalize_ram("4TB") == "4 Go"


class TestNormalizeDescriptionUnits:
    """Tests for normalize_description_units()."""

    def test_gb_uppercase(self):
        assert normalize_description_units("Apple iPhone 15 128GB Black") == "Apple iPhone 15 128Go Black"

    def test_gb_mixed_case(self):
        assert normalize_description_units("Xiaomi 8/256Gb Black") == "Xiaomi 8/256Go Black"

    def test_gb_lowercase(self):
        assert normalize_description_units("Samsung 128gb Blue") == "Samsung 128Go Blue"

    def test_tb_uppercase(self):
        assert normalize_description_units("Samsung 1TB Storage") == "Samsung 1To Storage"

    def test_ram_storage_combo(self):
        assert normalize_description_units("Google Pixel 9a 5G DS 8/128GB Iris") == "Google Pixel 9a 5G DS 8/128Go Iris"

    def test_no_unit_unchanged(self):
        assert normalize_description_units("Apple iPhone 15 Black") == "Apple iPhone 15 Black"

    def test_go_already_normalized(self):
        assert normalize_description_units("Apple iPhone 15 128Go Black") == "Apple iPhone 15 128Go Black"

    def test_space_between_number_and_unit(self):
        assert normalize_description_units("Hotwav 4/128 Gb Grey") == "Hotwav 4/128Go Grey"

    def test_multiple_units(self):
        assert normalize_description_units("Phone 8GB 256GB") == "Phone 8Go 256Go"
