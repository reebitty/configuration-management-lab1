import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from src.emulator import (
    execute_line,
    get_vfs_name,
    parse_args,
    parse_input,
    run_script,
)


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


class TestConfiguration(unittest.TestCase):
    """Тестирование конфигурации эмулятора для второго этапа."""

    def test_parse_args(self) -> None:
        """Тест разбора параметров командной строки."""
        args = parse_args(["--vfs", "data/vfs.csv", "--script", "s.txt"])
        self.assertEqual(args.vfs_path, "data/vfs.csv")
        self.assertEqual(args.script_path, "s.txt")

    def test_parse_args_default(self) -> None:
        """Тест значений параметров по умолчанию."""
        args = parse_args([])
        self.assertIsNone(args.vfs_path)
        self.assertIsNone(args.script_path)

    def test_get_vfs_name(self) -> None:
        """Тест получения имени VFS из пути."""
        self.assertEqual(get_vfs_name("data/vfs.csv"), "vfs")
        self.assertEqual(get_vfs_name(None), "my_virtual_vfs")

    def test_execute_line_error(self) -> None:
        """Тест определения ошибочной строки."""
        with redirect_stdout(io.StringIO()):
            self.assertFalse(execute_line("unknown"))
            self.assertTrue(execute_line("ls"))

    def test_run_script_skips_errors(self) -> None:
        """Тест пропуска ошибочных строк стартового скрипта."""
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", delete=False, encoding="utf-8"
        ) as file:
            file.write("unknown\ncd /home\n")
        output = io.StringIO()
        with redirect_stdout(output):
            run_script(file.name, "vfs> ")
        os.remove(file.name)
        text = output.getvalue()
        self.assertIn("vfs> unknown", text)
        self.assertIn("строка 1", text)
        self.assertIn("выполнен с ошибками (строки: 1)", text)
        self.assertIn("vfs> cd /home", text)

    def test_run_script_missing_file(self) -> None:
        """Тест сообщения об ошибке при отсутствии скрипта."""
        output = io.StringIO()
        with redirect_stdout(output):
            run_script("missing_script.txt", "vfs> ")
        self.assertIn("не удалось открыть", output.getvalue())


if __name__ == "__main__":
    unittest.main()
