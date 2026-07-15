import getpass
import os
import sys

ENV_VARS = (
    ("USER", "Логин Telnet (USER)", False),
    ("PASS", "Пароль Telnet (PASS)", True),
    ("USER_SSH", "Логин SSH (USER_SSH)", False),
    ("PASS_SSH", "Пароль SSH (PASS_SSH)", True),
)


def _prompt(label: str, secret: bool = False) -> str:
    while True:
        if secret:
            value = getpass.getpass(f"{label}: ").strip()
        else:
            value = input(f"{label}: ").strip()
        if value:
            return value
        print("⚠️ Значение не может быть пустым, попробуйте ещё раз. Ctrl+C для отмены.")


def env_path(script_dir: str | None = None) -> str:
    if script_dir is None:
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(script_dir, ".env")


def ensure_env_file(script_dir: str | None = None) -> str:
    path = env_path(script_dir)
    if os.path.exists(path):
        return path

    print("📄 Файл .env не найден. Создаём его в корне проекта. Ctrl+C для отмены.")

    values = {}
    for key, label, secret in ENV_VARS:
        values[key] = _prompt(label, secret=secret)

    try:
        with open(path, "w", encoding="utf-8") as f:
            for key, _, _ in ENV_VARS:
                f.write(f'{key}="{values[key]}"\n')
        print(f"\n✅ Файл .env создан: {path}\n")
    except OSError as e:
        print(f"❌ Не удалось создать .env: {e}")
        sys.exit(1)

    return path


if __name__ == "__main__":
    ensure_env_file()
