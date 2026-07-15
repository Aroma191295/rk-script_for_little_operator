import re
import time


class CDataDiagnostic:
    """Диагностика абонентских ONT на OLT C-Data (GPON)."""

    DEFAULT_GPON_INTERFACE = "0/0"
    DEFAULT_ETH_PORT = "1"

    def __init__(self, client, debug=False):
        self.client = client
        self.debug = debug or getattr(client, "debug", False)
        self.ip = client.ip
        self.gpon_interface = self.DEFAULT_GPON_INTERFACE

        self._enter_operational_context()

    def _enter_operational_context(self):
        if self.debug:
            print(
                f"\n[DEBUG] C-Data: вход в interface gpon {self.gpon_interface}",
                flush=True,
            )

        self.client.clear_buffer()
        if hasattr(self.client, "enter_enable"):
            self.client.enter_enable()
        self.client.send_command("config", wait_for_prompt=True)
        time.sleep(0.3)
        self.client.send_command(
            f"interface gpon {self.gpon_interface}",
            wait_for_prompt=True,
        )
        time.sleep(0.3)
        self.client.clear_buffer()

    def _parse_port(self, port):
        """
        Разбор формата порта:
          1/1           -> gpon 0/0, tree=1, ont=1
          0/0:1/1       -> gpon 0/0, tree=1, ont=1
        """
        port = port.strip()
        gpon_interface = self.DEFAULT_GPON_INTERFACE

        if ":" in port:
            gpon_part, ont_part = port.split(":", 1)
            gpon_interface = gpon_part.strip()
            tree, ont_id = ont_part.split("/", 1)
        else:
            tree, ont_id = port.split("/", 1)

        if gpon_interface != self.gpon_interface:
            self.gpon_interface = gpon_interface
            self._enter_operational_context()

        return tree.strip(), ont_id.strip()

    def _run_command(self, command, delay=0.5):
        self.client.clear_buffer()
        output = self.client.send_command(command, wait_for_prompt=True)
        time.sleep(delay)

        # Если SSH уже стримил ответ — не дублируем. Иначе печатаем разово.
        if self.debug and output and not getattr(self.client, "debug", False):
            print(f"[DEBUG] C-Data raw ({len(output)} chars):", flush=True)
            print(output, flush=True)

        return output if output else ""

    def _clean_output(self, output):
        if not output:
            return ""

        lines = output.split("\n")
        clean_lines = []

        for line in lines:
            stripped = line.strip()
            if not stripped or set(stripped) <= {"-", "="}:
                continue
            if stripped.endswith("#") or stripped.endswith(">"):
                continue
            lower = stripped.lower()
            if any(
                marker in lower
                for marker in (
                    "invalid",
                    "error",
                    "unknown command",
                    "incomplete command",
                    "ambiguous command",
                    "% ",
                )
            ):
                if self.debug:
                    print(f"[DEBUG] ⚠ ответ устройства: {stripped}", flush=True)
                return f"❌ Ошибка устройства: {stripped}"
            clean_lines.append(line.rstrip())

        return "\n".join(clean_lines)

    def get_ont_info(self, port):
        tree, ont_id = self._parse_port(port)
        output = self._run_command(f"show ont info {tree} {ont_id}")
        cleaned = self._clean_output(output)
        if cleaned:
            return cleaned
        return "Информация об ONT не найдена (пустой ответ)"

    def get_eth_port_state(self, port):
        tree, ont_id = self._parse_port(port)
        output = self._run_command(
            f"show ont port state {tree} {ont_id} eth all"
        )
        cleaned = self._clean_output(output)
        if cleaned:
            return cleaned
        return "Статус Ethernet-портов ONT не найден"

    def get_optical_info(self, port):
        tree, ont_id = self._parse_port(port)
        output = self._run_command(f"show ont optical-info {tree} {ont_id}")
        if not output or "optical-info" not in output.lower():
            output = self._run_command(f"show ont  optical-info {tree} {ont_id}")
        cleaned = self._clean_output(output)
        if cleaned:
            return cleaned
        return "Оптическая информация не найдена"

    def get_mac_table(self, port, eth_port=None):
        tree, ont_id = self._parse_port(port)
        eth = eth_port or self.DEFAULT_ETH_PORT
        output = self._run_command(
            f"show ont port learned-mac {tree} {ont_id} eth {eth}"
        )
        cleaned = self._clean_output(output)

        mac_patterns = [
            r"([0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4})",
            r"([0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:"
            r"[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})",
        ]

        macs = []
        for pattern in mac_patterns:
            macs.extend(re.findall(pattern, cleaned))

        unique_macs = list(set(macs))

        return {
            "output": cleaned,
            "macs": unique_macs,
            "count": len(unique_macs),
        }

    def analyze_port(self, port):
        print(f"\n{'='*70}")
        print(f"🔍 АНАЛИЗ ONT {port} НА OLT C-DATA {self.ip}")
        print(f"{'='*70}\n")

        results = {}

        print("📋 ИНФОРМАЦИЯ ОБ ONT:")
        info = self.get_ont_info(port)
        print(info)
        results["ont_info"] = info
        print()

        print("📡 ОПТИЧЕСКАЯ ИНФОРМАЦИЯ:")
        optical = self.get_optical_info(port)
        print(optical)
        results["optical"] = optical
        print()

        print("🔌 СТАТУС ETHERNET-ПОРТОВ НА ONT:")
        eth_state = self.get_eth_port_state(port)
        print(eth_state)
        results["eth_state"] = eth_state
        print()

        print("🖧 MAC-АДРЕСА НА ONT (eth 1):")
        mac_info = self.get_mac_table(port)
        if mac_info["count"] > 0:
            print(f"📊 Найдено MAC-адресов: {mac_info['count']}")
            print("📋 Список MAC-адресов (первые 5):")
            for i, mac in enumerate(mac_info["macs"][:5], 1):
                print(f"   {i:2}. {mac}")
            if mac_info["count"] > 5:
                print(f"   ... и еще {mac_info['count'] - 5} адресов")
        else:
            print("❌ MAC-адреса не найдены на ONT")
        results["mac_count"] = mac_info["count"]
        print()

        return results
