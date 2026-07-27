import re
import time

# set commands [list \
#     "show interface ont $USER_PORT state" \
#     "show interface ont $USER_PORT ports" \
#     "show mac interface ont $USER_PORT" \
#     "show interface ont $USER_PORT connections" \
#     "show interface ont $USER_PORT laser" \
# ]


class EltexLTPDiagnostic:
    def __init__(self, client):
        self.client = client
        self.ip = client.ip

    def get_mac_table(self, port=None):
        self.client.clear_buffer()

        command = f"show mac interface ont {port}"
        output = self.client.send_command(command, wait_for_prompt=True)

        mac_patterns = [
            r'([0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4})',
            r'([0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})',
        ]

        macs = []
        for pattern in mac_patterns:
            macs.extend(re.findall(pattern, output))

        unique_macs = list(set(macs))

        return {
            'output': output,
            'macs': unique_macs,
            'count': len(unique_macs)
        }

    def get_onu_status(self, port):
        self.client.clear_buffer()

        output = self.client.send_command(f"show interface ont {port} state", wait_for_prompt=True)

        if not output:
            return "Информация о порте не найдена (пустой ответ или ошибка вывода)"

        lines = output.split('\n')
        port_line_index = -1
        port_line = None

        for i, line in enumerate(lines):
            stripped_line = line.strip().lower()
            port_lower = port.lower()

            if stripped_line.startswith(port_lower):
                rest_of_line = stripped_line[len(port_lower):]
                if not rest_of_line or rest_of_line[0].isspace():
                    port_line_index = i
                    port_line = line
                    break

        if port_line_index == -1:
            for line in lines:
                if "invalid" in line.lower() or "error" in line.lower() or "not found" in line.lower():
                    return f"❌ Ошибка устройства: {line.strip()}"
            return (f"⚠️ Строка с указанным портом не найдена в выводе.\n"
                    f"⚠️ Возможно, порт указан неверно. Требуется полное имя (например, gi1/0/1), у вас указано: {port}")

        relevant_lines = [port_line]

        for i in range(port_line_index - 1, -1, -1):
            prev_line = lines[i]

            if not prev_line.strip() or '#' in prev_line or '>' in prev_line:
                break

            relevant_lines.insert(0, prev_line)

        return '\n'.join(relevant_lines)

    def get_port_description(self, port):
        self.client.clear_buffer()

        command = f"show running-config interface {port}"
        output = self.client.send_command(command, wait_for_prompt=True)

        if output and ("interface" in output.lower() or port.lower() in output.lower()):
            return output.strip()
        return "Описание порта не найдено"

    def get_port_errors(self, port):
        self.client.clear_buffer()
        command = f"show interfaces counters {port}"
        output = self.client.send_command(command, wait_for_prompt=True)

        if not output:
            return "Не удалось получить счетчики"

        lines = output.split('\n')
        analyzed_errors = []
        keywords = ['error', 'collision', 'deferred', 'late', 'excessive', 'oversize', 'crc']

        for line in lines:
            line_lower = line.lower()
            if any(kw in line_lower for kw in keywords):
                match = re.search(r':\s*(\d+)\s*$', line)
                if match:
                    value = int(match.group(1))
                    if value > 0:
                        analyzed_errors.append(f"🔴 {line.strip()}")
                    else:
                        analyzed_errors.append(f"✅ {line.strip()}")
        if analyzed_errors:
            return "\n".join(analyzed_errors)
        return "Счетчики ошибок не найдены в выводе"

    def analyze_port(self, port):
        print(f"\n{'='*70}")
        print(f"🔍 АНАЛИЗ ПОРТА {port} НА КОММУТАТОРЕ {self.ip}")
        print(f"{'='*70}\n")

        results = {}

        print("📊 СТАТУС ПОРТА:")
        status = self.get_port_status(port)
        print(status)
        results['status'] = status
        print()

        print("📝 КОНФИГУРАЦИЯ ПОРТА:")
        desc = self.get_port_description(port)
        print(desc)
        results['description'] = desc
        print()

        print("⚠️ ОШИБКИ ИНТЕРФЕЙСА (Counters):")
        errors_info = self.get_port_errors(port)
        print(errors_info)
        results['errors'] = errors_info
        print()

        print("🖧 MAC-АДРЕСА НА ПОРТУ:")
        mac_info = self.get_mac_table(port)
        if mac_info['count'] > 0:
            print(f"📊 Найдено MAC-адресов: {mac_info['count']}")
            print("📋 Список MAC-адресов (первые 5):")
            for i, mac in enumerate(mac_info['macs'][:5], 1):
                print(f"   {i:2}. {mac}")
            if mac_info['count'] > 5:
                print(f"   ... и еще {mac_info['count'] - 5} адресов")
        else:
            print("❌ MAC-адреса не найдены на порту")
        results['mac_count'] = mac_info['count']
        print()

        return results

    def interactive_menu(self, port):
        while True:
            print(f"\n{'='*50}")
            print(f"Порт: {port} @ {self.ip}")
#     "show interface ont $USER_PORT state" \
#     "show interface ont $USER_PORT ports" \
#     "show mac interface ont $USER_PORT" \
#     "show interface ont $USER_PORT connections" \
#     "show interface ont $USER_PORT laser" \

            print("1. Повторить диагностику")
            print("2. state")
            print("3. ports")
            print("4. mac")
            print("5. connections")
            print("6. laser")
            print("7. Перезагрузить терминал")
            print("9. Консоль")
            print("0. Выход")
            print("="*50)

            choice = input("Выбор: ").strip()

            match choice:
                case "1":
                    self.analyze_port(port)

                case "2":
                    print(self.get_port_status(port))

                case "3":
                    print(self.get_port_description(port))

                case "4":
                    mac_info = self.get_mac_table(port)
                    if mac_info['count'] > 0:
                        print(f"📊 Найдено MAC-адресов: {mac_info['count']}")
                        print("📋 Список MAC-адресов (первые 5):")
                        for i, mac in enumerate(mac_info['macs'][:5], 1):
                            print(f"   {i:2}. {mac}")
                    else:
                        print("❌ MAC-адреса не найдены на порту")

                case "5":
                    print(self.get_port_errors(port))

                case "6":
                    print(self.history_port(port))

                case "7":
                    confirm = input(f"⚠️ Дергаем {port}? (yes/no): ").strip().lower()
                    if confirm == "y":
                        full = input('Введите полностью "yes" для подтверждения: ').strip().lower()
                        if full == "yes":
                            print(self.reload_port(port))
                        else:
                            print("Команда отменена")
                    elif confirm == "yes":
                        print(self.reload_port(port))
                    else:
                        print("Команда отменена")

                case "9":
                    self.client.interactive_mode()

                case "0":
                    break

                case _:
                    print("Неизвестный пункт")
