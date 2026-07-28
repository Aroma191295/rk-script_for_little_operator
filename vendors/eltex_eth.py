import re
import time

MAC_PATTERNS = (
    r"([0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4})",
    r"([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})",
)

ERROR_KEYWORDS = (
    "error", "collision", "deferred", "late",
    "excessive", "oversize", "crc",
)

LINK_STATE_HINTS = {
    "nc":  ("🔌", "not connected — нет линка"),
    "err": ("🔴", "error-disabled — заглушен системой"),
    "adm": ("🔒", "admin.shutdown — выключен администратором"),
}


class EltexEthDiagnostic:
    def __init__(self, client):
        self.client = client
        self.ip = client.ip

    def _cmd(self, command):
        self.client.clear_buffer()
        return self.client.send_command(command, wait_for_prompt=True) or ""

    def _confirm(self, prompt):
        answer = input(f"{prompt} (yes/no): ").strip().lower()
        return answer == "yes"

    def _print_macs(self, mac_info, limit=5):
        macs = mac_info["macs"]
        if not macs:
            print("MAC-адреса не найдены на порту")
            return
        print(f"Найдено MAC: {len(macs)}")
        for i, mac in enumerate(macs[:limit], 1):
            print(f"  {i}. {mac}")
        if len(macs) > limit:
            print(f"  ... и ещё {len(macs) - limit}")

    def reload_port(self, port, delay=3):
        try:
            for cmd in ("configure terminal", f"interface {port}", "shutdown"):
                self._cmd(cmd)
            print(f"⏳ Порт {port} выключен, ждём {delay} сек...")
            time.sleep(delay)
        finally:
            for cmd in ("no shutdown", "end"):
                self._cmd(cmd)
            print(f"✅ Порт {port} снова включён")

        return self.get_port_status(port)

    def history_port(self, port):
        try:
            self._cmd("terminal datadump")
            output = self._cmd(f"show logging | include {port}")
        finally:
            self._cmd("no terminal datadump")
        return output.strip() or f"Логи по порту {port} не найдены"

    def get_mac_table(self, port):
        output = self._cmd(f"show mac address-table interface {port}")
        macs = []
        for pattern in MAC_PATTERNS:
            macs.extend(re.findall(pattern, output))
        unique = list(dict.fromkeys(macs))
        return {"output": output, "macs": unique, "count": len(unique)}

    def get_port_status(self, port):
        output = self._cmd(f"show interfaces status {port}").strip()
        if not output:
            return f"{port}: нет ответа от устройства"

        port_lower = port.lower()
        port_line = next(
            (line for line in output.splitlines()
            if line.strip().lower().startswith(port_lower)),
            None,
        )
        if not port_line:
            return f"{port}: статус не распознан\n{output}"

        down = re.search(r"Down\s*\((nc|adm|err)\)", port_line, re.IGNORECASE)
        if down:
            code = down.group(1).lower()
            return f"{port}: Down ({code}) — {LINK_STATE_HINTS[code]}"

        if re.search(r"\bUp\b", port_line, re.IGNORECASE):
            return f"✅{port}: Up — линк есть"

        return f"{port}: статус не распознан\n{port_line}"

    def get_port_config(self, port):
        output = self._cmd(f"show running-config interface {port}").strip()
        return output or "Конфигурация порта не найдена"

    def get_port_errors(self, port):
        output = self._cmd(f"show interfaces counters {port}")
        if not output:
            return "Не удалось получить счётчики"

        found = []
        for line in output.splitlines():
            line_lower = line.lower()
            if not any(kw in line_lower for kw in ERROR_KEYWORDS):
                continue
            match = re.search(r":\s*(\d+)\s*$", line)
            if not match:
                continue
            value = int(match.group(1))
            if value > 0:
                found.append(f"⚠ {line.strip()}")

        return "\n".join(found) if found else "Ненулевых ошибок нет"

    def analyze_port(self, port):
        print(f"\n{'=' * 70}")
        print(f"Анализ порта {port} на {self.ip}")
        print(f"{'=' * 70}\n")

        print("Статус:")
        status = self.get_port_status(port)
        print(status, end="\n\n")

        print("Конфигурация:")
        config = self.get_port_config(port)
        print(config, end="\n\n")

        print("Ошибки:")
        errors = self.get_port_errors(port)
        print(errors, end="\n\n")

        print("MAC:")
        mac_info = self.get_mac_table(port)
        self._print_macs(mac_info)
        print()

        return {
            "status": status,
            "config": config,
            "errors": errors,
            "mac_count": mac_info["count"],
        }

    def interactive_menu(self, port):
        actions = {
            "1": lambda: self.analyze_port(port),
            "2": lambda: print(self.get_port_status(port)),
            "3": lambda: print(self.get_port_config(port)),
            "4": lambda: self._print_macs(self.get_mac_table(port)),
            "5": lambda: print(self.get_port_errors(port)),
            "6": lambda: print(self.history_port(port)),
            "7": self._reload_with_confirm,
            "9": self.client.interactive_mode,
        }

        while True:
            print(f"\n{'=' * 50}")
            print(f"Порт: {self.ip} {port}")
            print("1. 🔁 Повторить диагностику")
            print("2. 📊 Статус порта")
            print("3. 📝 Конфигурация порта")
            print("4. 🖧 MAC на порту")
            print("5. ⚠️ Ошибки порта")
            print("6. 📜 Логи порта")
            print("7. 🔌 Перезагрузить порт")
            print("9. 💻 Консоль")
            print("0. 🚪 Выход")
            print("=" * 50)

            choice = input("Выбор: ").strip()
            if choice == "0":
                break
            if choice == "7":
                actions["7"](port)
                continue
            action = actions.get(choice)
            if action:
                action()
            else:
                print("🤷 Неизвестный пункт")

    def _reload_with_confirm(self, port):
        if self._confirm(f"Дёргаем {port}?"):
            print(self.reload_port(port))
        else:
            print("🚫 Отменено")