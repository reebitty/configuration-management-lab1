import argparse
import base64
import binascii
import csv
import os
import sys

DEFAULT_VFS_NAME = "my_virtual_vfs"
VFS_HEADER = ["path", "type", "content"]


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


def get_prompt(vfs_name: str = DEFAULT_VFS_NAME) -> str:
    """Формирует приглашение к вводу на основе имени VFS."""
    return f"{vfs_name}> "


def parse_input(user_input: str) -> list[str]:
    """Разделяет ввод на токены и раскрывает переменные окружения ОС."""
    expanded_input = os.path.expandvars(user_input)
    return expanded_input.strip().split()


def execute_command(command: str, args: list[str]) -> bool:
    """Выполняет команду. Возвращает False, если произошла ошибка."""
    if command == "exit":
        if args:
            print("exit: too many arguments")
            return False
        sys.exit(0)
    if command in ("ls", "cd"):
        args_str = " ".join(args) if args else "нет аргументов"
        print(f"[Заглушка] Вызвана команда: {command}")
        print(f"Переданные аргументы: {args_str}")
        return True
    print(f"{command}: command not found")
    return False


def execute_line(line: str) -> bool:
    """Разбирает и выполняет строку. Возвращает False при ошибке."""
    tokens = parse_input(line)
    if not tokens:
        return True
    return execute_command(tokens[0], tokens[1:])


def print_script_result(errors: list[int]) -> None:
    """Выводит итоговое сообщение о выполнении стартового скрипта."""
    if errors:
        numbers = ", ".join(str(number) for number in errors)
        print(f"Ошибка: стартовый скрипт выполнен с ошибками "
              f"(строки: {numbers})")
    else:
        print("Стартовый скрипт выполнен без ошибок")


def run_script(script_path: str, prompt: str) -> None:
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
            print(f"{prompt}{line}")
            if not execute_line(line):
                errors.append(number)
                print(f"Ошибка в стартовом скрипте (строка {number}): "
                      f"'{line}' пропущена")
    finally:
        print_script_result(errors)


def repl(prompt: str) -> None:
    """Главный цикл эмулятора (REPL)."""
    while True:
        try:
            user_input = input(prompt)
            execute_line(user_input)
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
    prompt = get_prompt(get_vfs_name(args.vfs_path))
    if args.script_path:
        run_script(args.script_path, prompt)
    repl(prompt)


if __name__ == "__main__":
    main()
