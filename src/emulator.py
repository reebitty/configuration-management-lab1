import argparse
import os
import sys

DEFAULT_VFS_NAME = "my_virtual_vfs"


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
    """Точка входа: читает параметры, выполняет скрипт и запускает REPL."""
    args = parse_args(argv)
    print_debug_params(args)
    prompt = get_prompt(get_vfs_name(args.vfs_path))
    if args.script_path:
        run_script(args.script_path, prompt)
    repl(prompt)


if __name__ == "__main__":
    main()
