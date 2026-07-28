import re
import time

MAC_PATTERNS = (
    r"([0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4})",
    r"([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})",
)


class EltexLTPDiagnostic:
    def __init__(self, client):
        self.client = client
        self.ip = client.ip

    def _cmd(self, command):
        self.client.clear_buffer()
        return self.client.send_command(command, wait_for_prompt=True) or ""

    def _confirm(self, prompt):
        return input(f"{prompt} (yes/no): ").strip().lower() == "yes"

    def _print_macs(self, mac_info, limit=5):
        macs = mac_info["macs"]
        if not macs:
            print("👻 MAC-адреса не найдены на ONT")
            return
        print(f"🖧 Найдено MAC: {len(macs)}")
        for i, mac in enumerate(macs[:limit], 1):
            print(f"  {i}. {mac}")
        if len(macs) > limit:
            print(f"  … и ещё {len(macs) - limit}")

    def get_ont_state(self, port):
        output = self._cmd(f"show interface ont {port} state").strip()
        return output 
    # or f"📭 {port}: нет ответа (state)"

    def get_ont_ports(self, port):
        output = self._cmd(f"show interface ont {port} ports").strip()
        return output or f"📭 {port}: нет ответа (ports)"

    def get_mac_table(self, port):
        output = self._cmd(f"show mac interface ont {port}")
        macs = []
        for pattern in MAC_PATTERNS:
            macs.extend(re.findall(pattern, output))
        unique = list(dict.fromkeys(macs))
        return {"output": output, "macs": unique, "count": len(unique)}

    def get_ont_connections(self, port):
        output = self._cmd(f"show interface ont {port} connections").strip()
        return output or f"📭 {port}: нет ответа (connections)"

    def get_ont_laser(self, port):
        output = self._cmd(f"show interface ont {port} laser").strip()
        return output or f"📭 {port}: нет ответа (laser)"

    def reload_ont(self, port, delay=30):
        try:
            for cmd in (
                "configure terminal",
                f"interface ont {port}",
                "reboot",
            ):
                self._cmd(cmd)
            print(f"⏳ ONT {port}: reboot, ждём {delay} сек...")
            time.sleep(delay)
        finally:
            self._cmd("end")
            print(f"✅ Команда reboot отправлена для {port}")

        return self.get_ont_state(port)

    def analyze_port(self, port):
        print(f"\n{'=' * 70}")
        print(f"🔍 Анализ ONT {port} на LTP {self.ip}")
        print(f"{'=' * 70}\n")

        print("📊 State:")
        state = self.get_ont_state(port)
        print(state, end="\n\n")

        print("🔌 Ports:")
        ports = self.get_ont_ports(port)
        print(ports, end="\n\n")

        print("🖧 MAC:")
        mac_info = self.get_mac_table(port)
        if mac_info["output"].strip():
            print(mac_info["output"])
        self._print_macs(mac_info)
        print()

        print("🔗 Connections:")
        connections = self.get_ont_connections(port)
        print(connections, end="\n\n")

        print("📡 Laser:")
        laser = self.get_ont_laser(port)
        print(laser, end="\n\n")

        return {
            "state": state,
            "ports": ports,
            "mac_count": mac_info["count"],
            "connections": connections,
            "laser": laser,
        }

    def interactive_menu(self, port):
        actions = {
            "1": lambda: self.analyze_port(port),
            "2": lambda: print(self.get_ont_state(port)),
            "3": lambda: print(self.get_ont_ports(port)),
            "4": lambda: (
                print(self.get_mac_table(port)["output"] or "пусто"),
                self._print_macs(self.get_mac_table(port)),
            ),
            "5": lambda: print(self.get_ont_connections(port)),
            "6": lambda: print(self.get_ont_laser(port)),
            "7": self._reload_with_confirm,
            "9": self.client.interactive_mode,
        }

        while True:
            print(f"\n{'=' * 50}")
            print(f"📌 ONT: {self.ip} {port}")
            print("1. 🔁 Полная диагностика")
            print("2. 📊 state")
            print("3. 🔌 ports")
            print("4. 🖧 mac")
            print("5. 🔗 connections")
            print("6. 📡 laser")
            print("7. ♻️  Перезагрузить ONT")
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
        if self._confirm(f"⚠️ Перезагружаем ONT {port}?"):
            print(self.reload_ont(port))
        else:
            print("🚫 Отменено")