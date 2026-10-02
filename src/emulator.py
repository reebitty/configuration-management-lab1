import os
import sys


def get_prompt() -> str:
    """Формирует приглашение к вводу на основе имени VFS."""
    vfs_name = "my_virtual_vfs"
    return f"{vfs_name}> "


def parse_input(user_input: str) -> list[str]:
    """Разделяет ввод на токены и раскрывает переменные окружения ОС."""
    expanded_input = os.path.expandvars(user_input)
    return expanded_input.strip().split()


def main() -> None:
    """Главный цикл эмулятора (REPL)."""
    while True:
        try:
            prompt = get_prompt()
            user_input = input(prompt)

            if not user_input.strip():
                continue

            tokens = parse_input(user_input)
            if not tokens:
                continue

            command = tokens[0]
            args = tokens[1:]

            if command == "exit":
                if args:
                    print("exit: too many arguments")
                else:
                    sys.exit(0)
            elif command in ("ls", "cd"):
                args_str = " ".join(args) if args else "нет аргументов"
                print(f"[Заглушка] Вызвана команда: {command}")
                print(f"Переданные аргументы: {args_str}")
            else:
                print(f"{command}: command not found")

        except (KeyboardInterrupt, EOFError):
            print("\nexit")
            sys.exit(0)


if __name__ == "__main__":
    main()
