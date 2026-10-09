import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from src.emulator import (
    Shell,
    VfsError,
    count_vfs,
    execute_line,
    format_size,
    get_vfs_name,
    load_vfs,
    parse_args,
    parse_input,
    run_script,
)

VFS_DIR = os.path.join(os.path.dirname(__file__), "..", "vfs")


def make_shell() -> Shell:
    """Создает эмулятор с VFS из трех уровней папок."""
    return Shell("vfs", load_vfs(os.path.join(VFS_DIR, "nested.csv")))


def run_line(shell: Shell, line: str) -> tuple[bool, str]:
    """Выполняет строку и возвращает результат и вывод."""
    output = io.StringIO()
    with redirect_stdout(output):
        result = execute_line(shell, line)
    return result, output.getvalue()


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
            self.assertFalse(execute_line(make_shell(), "unknown"))
            self.assertTrue(execute_line(make_shell(), "ls"))

    def test_run_script_skips_errors(self) -> None:
        """Тест пропуска ошибочных строк стартового скрипта."""
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", delete=False, encoding="utf-8"
        ) as file:
            file.write("unknown\ncd /home\n")
        output = io.StringIO()
        with redirect_stdout(output):
            run_script(file.name, make_shell())
        os.remove(file.name)
        text = output.getvalue()
        self.assertIn("vfs:/> unknown", text)
        self.assertIn("строка 1", text)
        self.assertIn("выполнен с ошибками (строки: 1)", text)
        self.assertIn("vfs:/> cd /home", text)

    def test_run_script_missing_file(self) -> None:
        """Тест сообщения об ошибке при отсутствии скрипта."""
        output = io.StringIO()
        with redirect_stdout(output):
            run_script("missing_script.txt", make_shell())
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


class TestCommands(unittest.TestCase):
    """Тестирование команд четвертого этапа."""

    def test_ls(self) -> None:
        """Тест вывода содержимого папки и ошибки для пути."""
        shell = make_shell()
        self.assertEqual(run_line(shell, "ls /home/user"),
                         (True, "docs  photo.bin\n"))
        self.assertFalse(run_line(shell, "ls /nope")[0])

    def test_ls_flags(self) -> None:
        """Тест ключей ls в любых комбинациях."""
        shell = make_shell()
        expected = run_line(shell, "ls -l -h -a /home")
        self.assertTrue(expected[0])
        self.assertIn("drwxr-xr-x 4.0K ..", expected[1])
        for line in ("ls -lha /home", "ls -hal /home", "ls -ahl /home"):
            self.assertEqual(run_line(shell, line), expected, line)
        self.assertEqual(run_line(shell, "ls -a /home"),
                         (True, ".  ..  user\n"))
        self.assertEqual(run_line(shell, "ls -la /home/user"),
                         (True, "drwxr-xr-x 4096 .\n"
                                "drwxr-xr-x 4096 ..\n"
                                "drwxr-xr-x 4096 docs\n"
                                "-rw-r--r--    8 photo.bin\n"))
        self.assertEqual(run_line(shell, "ls -lh /var"),
                         (True, "drwxr-xr-x 4.0K log\n"))

    def test_ls_invalid_flag(self) -> None:
        """Тест ошибки при неизвестном ключе ls."""
        result, output = run_line(make_shell(), "ls -lx")
        self.assertFalse(result)
        self.assertEqual(output, "ls: invalid option -- 'x'\n")

    def test_format_size(self) -> None:
        """Тест вывода размера в удобном для чтения виде."""
        self.assertEqual(format_size(500, True), "500")
        self.assertEqual(format_size(4096, False), "4096")
        self.assertEqual(format_size(4096, True), "4.0K")
        self.assertEqual(format_size(5 * 1024 * 1024, True), "5.0M")

    def test_cd(self) -> None:
        """Тест смены папки, перехода вверх и ошибок."""
        shell = make_shell()
        self.assertTrue(run_line(shell, "cd /home/user/docs")[0])
        self.assertEqual(shell.cwd, ["home", "user", "docs"])
        self.assertTrue(run_line(shell, "cd ../..")[0])
        self.assertEqual(shell.cwd, ["home"])
        self.assertFalse(run_line(shell, "cd /etc/hostname")[0])
        self.assertFalse(run_line(shell, "cd /nope")[0])
        self.assertTrue(run_line(shell, "cd")[0])
        self.assertEqual(shell.cwd, [])

    def test_uniq(self) -> None:
        """Тест удаления повторяющихся соседних строк."""
        result, output = run_line(make_shell(),
                                  "uniq /home/user/docs/file2.txt")
        self.assertTrue(result)
        self.assertEqual(output, "строка один\nстрока два\nстрока три\n")

    def test_uniq_errors(self) -> None:
        """Тест ошибок команды uniq."""
        shell = make_shell()
        self.assertFalse(run_line(shell, "uniq")[0])
        self.assertFalse(run_line(shell, "uniq /home")[0])
        self.assertFalse(run_line(shell, "uniq /nope")[0])

    def test_tree(self) -> None:
        """Тест вывода дерева папок и файлов."""
        result, output = run_line(make_shell(), "tree /var")
        self.assertTrue(result)
        self.assertEqual(output, "/var\n└── log\n    └── syslog\n"
                                 "\n1 directories, 1 files\n")
        self.assertFalse(run_line(make_shell(), "tree /etc/hostname")[0])

    def test_cal(self) -> None:
        """Тест календаря на месяц, на год и ошибок."""
        shell = make_shell()
        result, output = run_line(shell, "cal 2 2024")
        self.assertTrue(result)
        self.assertIn("February 2024", output)
        self.assertIn("29", output)
        self.assertTrue(run_line(shell, "cal 2026")[0])
        self.assertTrue(run_line(shell, "cal")[0])
        self.assertFalse(run_line(shell, "cal 13 2026")[0])
        self.assertFalse(run_line(shell, "cal abc")[0])
        self.assertFalse(run_line(shell, "cal 1 2 3")[0])


if __name__ == "__main__":
    unittest.main()
