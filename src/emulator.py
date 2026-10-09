import argparse
import base64
import binascii
import calendar
import csv
import datetime
import os
import sys
from dataclasses import dataclass, field

DEFAULT_VFS_NAME = "my_virtual_vfs"
VFS_HEADER = ["path", "type", "content"]
MAX_CAL_ARGS = 2
LS_FLAGS = "lha"
DIR_MODE, FILE_MODE = "drwxr-xr-x", "-rw-r--r--"
DIR_SIZE = 4096
KILOBYTE = 1024
SIZE_UNITS = "KMGT"
MIN_MONTH, MAX_MONTH = 1, 12
MIN_YEAR, MAX_YEAR = 1, 9999


class VfsError(Exception):
    """Ошибка загрузки виртуальной файловой системы."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разбирает параметры командной строки эмулятора."""
    parser = argparse.ArgumentParser(description="Эмулятор оболочки ОС")
    parser.add_argument(
        "--vfs",
        dest="vfs_path",
        default=None,
        help="путь к физическому расположению VFS",
    )
    parser.add_argument(
        "--script",
        dest="script_path",
        default=None,
        help="путь к стартовому скрипту",
    )
    return parser.parse_args(argv)


def print_debug_params(args: argparse.Namespace) -> None:
    """Выводит отладочную информацию обо всех заданных параметрах."""
    print("[DEBUG] Параметры запуска эмулятора:")
    print(f"[DEBUG]   Путь к VFS: {args.vfs_path or 'не задан'}")
    print(f"[DEBUG]   Стартовый скрипт: {args.script_path or 'не задан'}")


def get_vfs_name(vfs_path: str | None) -> str:
    """Возвращает имя VFS по пути к ее физическому расположению."""
    if not vfs_path:
        return DEFAULT_VFS_NAME
    return os.path.splitext(os.path.basename(vfs_path))[0]


def split_path(path: str) -> list[str]:
    """Разбивает путь VFS на имена элементов."""
    return [part for part in path.split("/") if part]


def get_vfs_dir(root: dict, parts: list[str], number: int) -> dict:
    """Возвращает папку VFS по частям пути, создавая недостающие."""
    node = root
    for part in parts:
        node = node.setdefault(part, {})
        if not isinstance(node, dict):
            raise VfsError(f"строка {number}: '{part}' является файлом")
    return node


def decode_content(content: str, number: int) -> bytes:
    """Декодирует содержимое файла из формата base64."""
    try:
        return base64.b64decode(content, validate=True)
    except (binascii.Error, ValueError) as error:
        raise VfsError(
            f"строка {number}: содержимое файла не в формате base64"
        ) from error


def add_file(root: dict, parts: list[str], content: str,
             number: int) -> None:
    """Добавляет файл в VFS."""
    if not parts:
        raise VfsError(f"строка {number}: у файла не указано имя")
    parent = get_vfs_dir(root, parts[:-1], number)
    if parts[-1] in parent:
        raise VfsError(f"строка {number}: элемент уже существует")
    parent[parts[-1]] = decode_content(content, number)


def add_vfs_row(root: dict, row: list[str], number: int) -> None:
    """Добавляет в VFS элемент, описанный строкой CSV."""
    if len(row) != len(VFS_HEADER):
        raise VfsError(f"строка {number}: ожидается 3 столбца")
    path, node_type, content = row
    if not path.startswith("/"):
        raise VfsError(f"строка {number}: путь должен начинаться с '/'")
    if node_type == "dir":
        get_vfs_dir(root, split_path(path), number)
    elif node_type == "file":
        add_file(root, split_path(path), content, number)
    else:
        raise VfsError(f"строка {number}: неизвестный тип '{node_type}'")


def load_vfs(vfs_path: str | None) -> dict:
    """Загружает VFS из CSV-файла в память. Без пути VFS пустая."""
    root: dict = {}
    if not vfs_path:
        return root
    try:
        with open(vfs_path, encoding="utf-8-sig", newline="") as file:
            rows = list(csv.reader(file))
    except OSError as error:
        raise VfsError(
            f"не удалось открыть файл '{vfs_path}': {error.strerror}"
        ) from error
    except csv.Error as error:
        raise VfsError(f"ошибка чтения CSV: {error}") from error

    if not rows or rows[0] != VFS_HEADER:
        raise VfsError("неверный формат: ожидается заголовок "
                       "path,type,content")
    for number, row in enumerate(rows[1:], start=2):
        add_vfs_row(root, row, number)
    return root


def count_vfs(node: dict) -> tuple[int, int]:
    """Подсчитывает количество папок и файлов в VFS."""
    dirs, files = 0, 0
    for child in node.values():
        if isinstance(child, dict):
            child_dirs, child_files = count_vfs(child)
            dirs += child_dirs + 1
            files += child_files
        else:
            files += 1
    return dirs, files


@dataclass
class Shell:
    """Состояние эмулятора: имя VFS, сама VFS и текущая папка."""

    name: str
    vfs: dict
    cwd: list[str] = field(default_factory=list)


def get_prompt(vfs_name: str = DEFAULT_VFS_NAME, cwd: str = "/") -> str:
    """Формирует приглашение к вводу на основе имени VFS и текущей папки."""
    return f"{vfs_name}:{cwd}> "


def format_path(parts: list[str]) -> str:
    """Преобразует список имен в путь VFS."""
    return "/" + "/".join(parts)


def resolve_path(cwd: list[str], path: str) -> list[str]:
    """Возвращает абсолютный путь с учетом '.', '..' и текущей папки."""
    parts = [] if path.startswith("/") else list(cwd)
    for part in split_path(path):
        if part == "..":
            if parts:
                parts.pop()
        elif part != ".":
            parts.append(part)
    return parts


def find_node(root: dict, parts: list[str]) -> dict | bytes | None:
    """Ищет элемент VFS по пути. Возвращает None, если его нет."""
    node: dict | bytes = root
    for part in parts:
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def get_dir(shell: Shell, command: str, path: str) -> dict | None:
    """Возвращает папку по пути или выводит ошибку и возвращает None."""
    node = find_node(shell.vfs, resolve_path(shell.cwd, path))
    if node is None:
        print(f"{command}: {path}: No such file or directory")
        return None
    if not isinstance(node, dict):
        print(f"{command}: {path}: Not a directory")
        return None
    return node


def get_file(shell: Shell, command: str, path: str) -> bytes | None:
    """Возвращает содержимое файла или выводит ошибку и возвращает None."""
    node = find_node(shell.vfs, resolve_path(shell.cwd, path))
    if node is None:
        print(f"{command}: {path}: No such file or directory")
        return None
    if isinstance(node, dict):
        print(f"{command}: {path}: Is a directory")
        return None
    return node


def check_max_args(command: str, args: list[str], limit: int) -> bool:
    """Проверяет, что аргументов не больше допустимого."""
    if len(args) > limit:
        print(f"{command}: too many arguments")
        return False
    return True


def cmd_exit(shell: Shell, args: list[str]) -> bool:
    """Команда exit: завершает работу эмулятора."""
    if not check_max_args("exit", args, 0):
        return False
    sys.exit(0)


def parse_ls_args(args: list[str]) -> tuple[set[str], list[str]] | None:
    """Разделяет аргументы ls на ключи и пути. При ошибке возвращает None."""
    flags: set[str] = set()
    paths = []
    for arg in args:
        if arg.startswith("-") and arg != "-":
            for flag in arg[1:]:
                if flag not in LS_FLAGS:
                    print(f"ls: invalid option -- '{flag}'")
                    return None
                flags.add(flag)
        else:
            paths.append(arg)
    return flags, paths


def format_size(size: int, human: bool) -> str:
    """Возвращает размер в байтах или в удобном виде (1.0K, 2.5M)."""
    if not human or size < KILOBYTE:
        return str(size)
    value = float(size)
    unit = ""
    for unit in SIZE_UNITS:
        value /= KILOBYTE
        if value < KILOBYTE:
            break
    return f"{value:.1f}{unit}"


def list_entries(shell: Shell, node: dict, parts: list[str],
                 show_all: bool) -> list[tuple[str, dict | bytes]]:
    """Возвращает элементы папки для ls (с ключом -a также '.' и '..')."""
    entries = [(name, node[name]) for name in sorted(node)
               if show_all or not name.startswith(".")]
    if show_all:
        parent = find_node(shell.vfs, parts[:-1])
        entries = [(".", node), ("..", parent)] + entries
    return entries


def print_ls(entries: list[tuple[str, dict | bytes]],
             flags: set[str]) -> None:
    """Выводит элементы в кратком или подробном (-l) формате."""
    if "l" not in flags:
        if entries:
            print("  ".join(name for name, _ in entries))
        return
    sizes = [
        format_size(DIR_SIZE if isinstance(item, dict) else len(item),
                    "h" in flags)
        for _, item in entries
    ]
    width = max((len(size) for size in sizes), default=0)
    for (name, item), size in zip(entries, sizes):
        mode = DIR_MODE if isinstance(item, dict) else FILE_MODE
        print(f"{mode} {size:>{width}} {name}")


def cmd_ls(shell: Shell, args: list[str]) -> bool:
    """Команда ls [-l] [-h] [-a] [путь]: выводит содержимое папки."""
    parsed = parse_ls_args(args)
    if parsed is None:
        return False
    flags, paths = parsed
    if not check_max_args("ls", paths, 1):
        return False
    path = paths[0] if paths else "."
    parts = resolve_path(shell.cwd, path)
    node = find_node(shell.vfs, parts)
    if node is None:
        print(f"ls: cannot access '{path}': No such file or directory")
        return False
    if isinstance(node, dict):
        entries = list_entries(shell, node, parts, "a" in flags)
    else:
        entries = [(path, node)]
    print_ls(entries, flags)
    return True


def cmd_cd(shell: Shell, args: list[str]) -> bool:
    """Команда cd: меняет текущую папку (без аргументов — корень)."""
    if not check_max_args("cd", args, 1):
        return False
    path = args[0] if args else "/"
    if get_dir(shell, "cd", path) is None:
        return False
    shell.cwd = resolve_path(shell.cwd, path)
    return True


def cmd_uniq(shell: Shell, args: list[str]) -> bool:
    """Команда uniq: выводит файл без повторяющихся соседних строк."""
    if not args:
        print("uniq: missing file operand")
        return False
    if not check_max_args("uniq", args, 1):
        return False
    content = get_file(shell, "uniq", args[0])
    if content is None:
        return False
    previous = None
    for line in content.decode("utf-8", errors="replace").splitlines():
        if line != previous:
            print(line)
        previous = line
    return True


def print_tree(node: dict, prefix: str) -> None:
    """Рекурсивно выводит содержимое папки в виде дерева."""
    names = sorted(node)
    for name in names:
        is_last = name == names[-1]
        print(f"{prefix}{'└── ' if is_last else '├── '}{name}")
        if isinstance(node[name], dict):
            print_tree(node[name], prefix + ("    " if is_last else "│   "))


def cmd_tree(shell: Shell, args: list[str]) -> bool:
    """Команда tree: выводит дерево папок и файлов."""
    if not check_max_args("tree", args, 1):
        return False
    path = args[0] if args else "."
    node = get_dir(shell, "tree", path)
    if node is None:
        return False
    print(path)
    print_tree(node, "")
    dirs, files = count_vfs(node)
    print(f"\n{dirs} directories, {files} files")
    return True


def cmd_cal(shell: Shell, args: list[str]) -> bool:
    """Команда cal: календарь на месяц ([месяц] год) или на год (год)."""
    if not check_max_args("cal", args, MAX_CAL_ARGS):
        return False
    try:
        numbers = [int(arg) for arg in args]
    except ValueError:
        print("cal: arguments must be numbers")
        return False
    today = datetime.date.today()
    *month, year = numbers or [today.month, today.year]
    if not MIN_YEAR <= year <= MAX_YEAR:
        print(f"cal: year {year} not in range {MIN_YEAR}..{MAX_YEAR}")
        return False
    text_calendar = calendar.TextCalendar(calendar.SUNDAY)
    if not month:
        print(text_calendar.formatyear(year))
        return True
    if not MIN_MONTH <= month[0] <= MAX_MONTH:
        print(f"cal: {month[0]} is not a month number "
              f"({MIN_MONTH}..{MAX_MONTH})")
        return False
    print(text_calendar.formatmonth(year, month[0]))
    return True


COMMANDS = {
    "exit": cmd_exit,
    "ls": cmd_ls,
    "cd": cmd_cd,
    "uniq": cmd_uniq,
    "tree": cmd_tree,
    "cal": cmd_cal,
}


def parse_input(user_input: str) -> list[str]:
    """Разделяет ввод на токены и раскрывает переменные окружения ОС."""
    expanded_input = os.path.expandvars(user_input)
    return expanded_input.strip().split()


def execute_command(shell: Shell, command: str, args: list[str]) -> bool:
    """Выполняет команду. Возвращает False, если произошла ошибка."""
    handler = COMMANDS.get(command)
    if handler is None:
        print(f"{command}: command not found")
        return False
    return handler(shell, args)


def execute_line(shell: Shell, line: str) -> bool:
    """Разбирает и выполняет строку. Возвращает False при ошибке."""
    tokens = parse_input(line)
    if not tokens:
        return True
    return execute_command(shell, tokens[0], tokens[1:])


def make_prompt(shell: Shell) -> str:
    """Формирует приглашение к вводу для текущего состояния эмулятора."""
    return get_prompt(shell.name, format_path(shell.cwd))


def print_script_result(errors: list[int]) -> None:
    """Выводит итоговое сообщение о выполнении стартового скрипта."""
    if errors:
        numbers = ", ".join(str(number) for number in errors)
        print(f"Ошибка: стартовый скрипт выполнен с ошибками "
              f"(строки: {numbers})")
    else:
        print("Стартовый скрипт выполнен без ошибок")


def run_script(script_path: str, shell: Shell) -> None:
    """Выполняет команды стартового скрипта, пропуская ошибочные строки."""
    try:
        with open(script_path, encoding="utf-8-sig") as file:
            lines = file.readlines()
    except OSError as error:
        print(f"Ошибка: не удалось открыть стартовый скрипт "
              f"'{script_path}': {error.strerror}")
        return

    errors: list[int] = []
    try:
        for number, line in enumerate(lines, start=1):
            line = line.strip()
            if not line:
                continue
            print(f"{make_prompt(shell)}{line}")
            if not execute_line(shell, line):
                errors.append(number)
                print(f"Ошибка в стартовом скрипте (строка {number}): "
                      f"'{line}' пропущена")
    finally:
        print_script_result(errors)


def repl(shell: Shell) -> None:
    """Главный цикл эмулятора (REPL)."""
    while True:
        try:
            user_input = input(make_prompt(shell))
            execute_line(shell, user_input)
        except (KeyboardInterrupt, EOFError):
            print("\nexit")
            sys.exit(0)


def main(argv: list[str] | None = None) -> None:
    """Точка входа: читает параметры, загружает VFS и запускает REPL."""
    args = parse_args(argv)
    print_debug_params(args)
    try:
        vfs = load_vfs(args.vfs_path)
    except VfsError as error:
        print(f"Ошибка загрузки VFS: {error}")
        sys.exit(1)
    dirs, files = count_vfs(vfs)
    print(f"[DEBUG] VFS загружена: папок {dirs}, файлов {files}")
    shell = Shell(get_vfs_name(args.vfs_path), vfs)
    if args.script_path:
        run_script(args.script_path, shell)
    repl(shell)


if __name__ == "__main__":
    main()
