import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from src.emulator import (
    VfsError,
    count_vfs,
    execute_line,
    get_vfs_name,
    load_vfs,
    parse_args,
    parse_input,
    run_script,
)

VFS_DIR = os.path.join(os.path.dirname(__file__), "..", "vfs")


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


class TestVfs(unittest.TestCase):
    """Тестирование загрузки VFS для третьего этапа."""

    def load_text(self, text: str) -> dict:
        """Загружает VFS из временного CSV-файла с заданным текстом."""
        with tempfile.NamedTemporaryFile(
            "w", suffix=".csv", delete=False, encoding="utf-8"
        ) as file:
            file.write(text)
        try:
            return load_vfs(file.name)
        finally:
            os.remove(file.name)

    def test_load_without_path(self) -> None:
        """Тест пустой VFS при отсутствии пути."""
        self.assertEqual(load_vfs(None), {})

    def test_load_minimal(self) -> None:
        """Тест загрузки минимальной VFS."""
        vfs = load_vfs(os.path.join(VFS_DIR, "minimal.csv"))
        self.assertEqual(count_vfs(vfs), (0, 0))

    def test_load_nested(self) -> None:
        """Тест загрузки VFS с несколькими уровнями вложенности."""
        vfs = load_vfs(os.path.join(VFS_DIR, "nested.csv"))
        self.assertEqual(count_vfs(vfs), (6, 5))
        docs = vfs["home"]["user"]["docs"]
        self.assertEqual(docs["file1.txt"].decode("utf-8"),
                         "Привет из файла номер один!\n")

    def test_load_binary(self) -> None:
        """Тест декодирования двоичных данных из base64."""
        vfs = load_vfs(os.path.join(VFS_DIR, "files.csv"))
        self.assertEqual(vfs["image.bin"], bytes(range(16)))
        self.assertEqual(vfs["empty.txt"], b"")

    def test_load_missing_file(self) -> None:
        """Тест ошибки при отсутствии файла VFS."""
        with self.assertRaises(VfsError):
            load_vfs("missing.csv")

    def test_load_bad_header(self) -> None:
        """Тест ошибки при неверном заголовке CSV."""
        with self.assertRaises(VfsError):
            self.load_text("name,kind\n/a,dir\n")

    def test_load_bad_base64(self) -> None:
        """Тест ошибки при содержимом не в формате base64."""
        with self.assertRaises(VfsError):
            load_vfs(os.path.join(VFS_DIR, "bad.csv"))

    def test_load_bad_type(self) -> None:
        """Тест ошибки при неизвестном типе элемента."""
        with self.assertRaises(VfsError):
            self.load_text("path,type,content\n/a,link,\n")

    def test_load_file_as_dir(self) -> None:
        """Тест ошибки, когда файл используется как папка."""
        with self.assertRaises(VfsError):
            self.load_text("path,type,content\n/a,file,\n/a/b,dir,\n")


if __name__ == "__main__":
    unittest.main()
