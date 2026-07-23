import re
import time

class ZTE320Diagnostic:
    def __init__(self, client):
        self.client = client
        self.ip = client.ip
        
        self.client.clear_buffer()
        self.client.send_command("terminal length 0", wait_for_prompt=True)
        time.sleep(0.5)
        self.client.clear_buffer()

    def _run_command(self, command, delay=1):
        self.client.clear_buffer()
        output = self.client.send_command(command, wait_for_prompt=True)
        time.sleep(delay)
        return output if output else ""

    def _clean_output(self, output):
        if not output:
            return ""
        
        lines = output.split('\n')
        clean_lines = []
        
        for line in lines:
            if '--More--' in line or 'CTRL+C' in line or line.strip().endswith('#'):
                continue
            if not line.strip() or set(line.strip()) <= {'-', '='}:
                continue
            
            clean_lines.append(line.rstrip())
            
        return '\n'.join(clean_lines)

    def get_onu_info(self, port):
        output = self._run_command(f"show gpon onu detail-info gpon-onu_{port}")
        return self._clean_output(output)

    def get_optical_power(self, port):
        output = self._run_command(f"show pon power attenuation gpon-onu_{port}")
        return self._clean_output(output)

    def get_mac_table(self, port):
        output = self._run_command(f"show mac-real-time gpon onu gpon-onu_{port}")
        cleaned = self._clean_output(output)
        
        mac_pattern = r'([0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4})'
        macs = re.findall(mac_pattern, cleaned)
        unique_macs = list(set(macs))
        
        return {
            'output': cleaned,
            'macs': unique_macs,
            'count': len(unique_macs)
        }

    def get_eth_status(self, port):
        output = self._run_command(f"show gpon remote-onu interface eth gpon-onu_{port}")
        return self._clean_output(output)

    def get_video_status(self, port):
        output = self._run_command(f"show gpon remote-onu interface video-ani gpon-onu_{port}")
        return self._clean_output(output)

    def analyze_port(self, port):
        print(f"\n{'='*70}")
        print(f"🔍 АНАЛИЗ GPON ONU {port} НА OLT {self.ip}")
        print(f"{'='*70}\n")
        
        print("📋 ИНФОРМАЦИЯ ОБ ONU (Статус, Сериал):")
        print(self.get_onu_info(port))
        print()
        
        print("📡 ОПТИЧЕСКАЯ МОЩНОСТЬ:")
        print(self.get_optical_power(port))
        print()
        
        print("🔌 СТАТУС ETHERNET-ПОРТОВ НА ONT:")
        print(self.get_eth_status(port))
        print()
        
        print("📺 СТАТУС VIDEO/RF ПОРТА:")
        print(self.get_video_status(port))
        print()
        
        print("🖧 MAC-АДРЕСА НА ONU:")
        mac_info = self.get_mac_table(port)
        if mac_info['count'] > 0:
            print(f"📊 Найдено MAC-адресов: {mac_info['count']}")
            for i, mac in enumerate(mac_info['macs'], 1):
                print(f"   {i:2}. {mac}")
        else:
            print("❌ MAC-адреса не найдены на ONU")
        print()

    def interactive_menu(self, port):
        while True:
            print(f"\n{'='*50}")
            print(f"Порт: {port} @ {self.ip}")
            print("1. Повторить диагностику")
            print("2. Информация о терминале")
            print("3. MAC на терминале")
            print("4. Статус медных портов")
            print("5. Уровень сигнала по оптики")
            print("6. Статус видео порта")
            print("9. Сырой CLI")
            print("0. Выход")
            print("="*50)

            choice = input("Выбор: ").strip()

            match choice:
                case "1":
                    self.analyze_port(port)

                case "2":
                    print(self.get_onu_info(port))
                    
                case "3":
                    mac_info = self.get_mac_table(port)
                    if mac_info['count'] > 0:
                        print(f"📊 Найдено MAC-адресов: {mac_info['count']}")
                        for i, mac in enumerate(mac_info['macs'], 1):
                            print(f"   {i:2}. {mac}")
                    else:
                        print("❌ MAC-адреса не найдены на ONU")

                case "4":
                    print(self.get_eth_status(port))

                case "5":
                    print(self.get_optical_power(port))

                case "6":
                    print(self.get_video_status(port))

                case "9":
                    self.client.interactive_mode()

                case "0":
                    break

                case _:
                    print("Неизвестный пункт")
