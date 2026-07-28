import re
import time

MAC_PATTERNS = (
    r"([0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4})",
    r"([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})",
)


class ZTE320Diagnostic:
    def __init__(self, client):
        self.client = client
        self.ip = client.ip

        # Как в expect: без пейджинга --More--
        self._cmd("terminal length 0")

    def _onu(self, port):
        """1/1/1:1 → gpon-onu_1/1/1:1"""
        port = port.strip()
        if port.lower().startswith("gpon-onu_"):
            return port
        return f"gpon-onu_{port}"

    def _cmd(self, command, delay=0.5):
        self.client.clear_buffer()
        output = self.client.send_command(command, wait_for_prompt=True) or ""
        if delay:
            time.sleep(delay)
        return self._clean_output(output)

    def _clean_output(self, output):
        if not output:
            return ""
        lines = []
        for line in output.splitlines():
            stripped = line.strip()
            if not stripped or set(stripped) <= {"-", "="}:
                continue
            if "--More--" in line or "CTRL+C" in line:
                continue
            if stripped.endswith("#") or stripped.endswith(">"):
                continue
            lines.append(line.rstrip())
        return "\n".join(lines)

    def _confirm(self, prompt):
        return input(f"{prompt} (yes/no): ").strip().lower() == "yes"

    def _print_macs(self, mac_info, limit=5):
        macs = mac_info["macs"]
        if not macs:
            print("👻 MAC-адреса не найдены на ONU")
            return
        print(f"🖧 Найдено MAC: {len(macs)}")
        for i, mac in enumerate(macs[:limit], 1):
            print(f"  {i}. {mac}")
        if len(macs) > limit:
            print(f"  … и ещё {len(macs) - limit}")

    def get_onu_info(self, port):
        onu = self._onu(port)
        output = self._cmd(f"show gpon onu detail-info {onu}")
        return output or f"📭 {onu}: нет ответа (detail-info)"

    def get_optical_power(self, port):
        onu = self._onu(port)
        output = self._cmd(f"show pon power attenuation {onu}")
        return output or f"📭 {onu}: нет ответа (optical)"

    def get_mac_table(self, port):
        onu = self._onu(port)
        output = self._cmd(f"show mac-real-time gpon onu {onu}")
        macs = []
        for pattern in MAC_PATTERNS:
            macs.extend(re.findall(pattern, output))
        unique = list(dict.fromkeys(macs))
        return {"output": output, "macs": unique, "count": len(unique)}

    def get_eth_status(self, port):
        onu = self._onu(port)
        output = self._cmd(f"show gpon remote-onu interface eth {onu}")
        return output or f"📭 {onu}: нет ответа (eth)"

    def get_video_status(self, port):
        onu = self._onu(port)
        output = self._cmd(f"show gpon remote-onu interface video-ani {onu}")
        return output or f"📭 {onu}: нет ответа (video)"

    def analyze_port(self, port):
        print(f"\n{'=' * 70}")
        print(f"🔍 Анализ ONU {port} на ZTE {self.ip}")
        print(f"{'=' * 70}\n")

        print("📋 Info (статус, сериал):")
        info = self.get_onu_info(port)
        print(info, end="\n\n")

        print("📡 Оптика:")
        optical = self.get_optical_power(port)
        print(optical, end="\n\n")

        print("🔌 Ethernet на ONU:")
        eth = self.get_eth_status(port)
        print(eth, end="\n\n")

        print("📺 Video/RF:")
        video = self.get_video_status(port)
        print(video, end="\n\n")

        print("🖧 MAC:")
        mac_info = self.get_mac_table(port)
        if mac_info["output"]:
            print(mac_info["output"])
        self._print_macs(mac_info)
        print()

        return {
            "info": info,
            "optical": optical,
            "eth": eth,
            "video": video,
            "mac_count": mac_info["count"],
        }

    def interactive_menu(self, port):
        def show_mac():
            info = self.get_mac_table(port)
            if info["output"]:
                print(info["output"])
            self._print_macs(info)

        actions = {
            "1": lambda: self.analyze_port(port),
            "2": lambda: print(self.get_onu_info(port)),
            "3": show_mac,
            "4": lambda: print(self.get_eth_status(port)),
            "5": lambda: print(self.get_optical_power(port)),
            "6": lambda: print(self.get_video_status(port)),
            "9": self.client.interactive_mode,
        }

        while True:
            print(f"\n{'=' * 50}")
            print(f"📌 ONU: {self.ip} {port}")
            print("1. 🔁 Полная диагностика")
            print("2. 📋 Информация о терминале")
            print("3. 🖧 MAC")
            print("4. 🔌 Медные порты")
            print("5. 📡 Оптика")
            print("6. 📺 Video/RF")
            print("9. 💻 Консоль")
            print("0. 🚪 Выход")
            print("=" * 50)

            choice = input("Выбор: ").strip()
            if choice == "0":
                break
            action = actions.get(choice)
            if action:
                action()
            else:
                print("🤷 Неизвестный пункт")