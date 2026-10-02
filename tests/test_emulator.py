import unittest
from src.emulator import parse_input


class TestEmulator(unittest.TestCase):
    """Тестирование парсера для первого этапа."""

    def test_parse_input_simple(self) -> None:
        """Тест базового разделения команды и аргументов."""
        result = parse_input("ls -la")
        self.assertEqual(result, ["ls", "-la"])

    def test_parse_input_spaces(self) -> None:
        """Тест обработки лишних пробелов по краям."""
        result = parse_input("   exit   ")
        self.assertEqual(result, ["exit"])


if __name__ == "__main__":
    unittest.main()
