import re

class EltexDiagnostic:
    def __init__(self, client):
        self.client = client
        self.ip = client.ip

# Получение MAC-таблицы (опционально для конкретного порта)        
    def get_mac_table(self, port=None):
        self.client.clear_buffer()
        
        command = f"show mac address-table interface {port}"
        output = self.client.send_command(command)
        #print(f"\n[DEBUG MAC] \n{output}\n[END DEBUG]\n")
        
        mac_patterns = [
            r'([0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4})',
            r'([0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})',
        ]
        
        macs = []
        for pattern in mac_patterns:
            macs.extend(re.findall(pattern, output))
        
        return {
            'output': output,
            'macs': list(set(macs)),
            'count': len(set(macs))
        }

# Получение статуса порта        
    def get_port_status(self, port):
        self.client.clear_buffer()
        
        commands = [
            f"show interface status {port}",
        ]
        for cmd in commands:
            output = self.client.send_command(cmd, wait_for_prompt=True)
            if output and ("up" in output.lower() or "down" in output.lower()):
                lines = output.split('\n')
                relevant_lines = []
                for line in lines:
                    if port in line or 'status' in line.lower() or 'up' in line.lower() or 'down' in line.lower():
                        relevant_lines.append(line)
                if relevant_lines:
                    return '\n'.join(relevant_lines[:10])
                return output[:500]
        return "Информация о порте не найдена"

# Получение конфигурации порта        
    def get_port_description(self, port):
        self.client.clear_buffer()
        
        commands = [
            f"show running-config interface {port}",
        ]
        
        for cmd in commands:
            output = self.client.send_command(cmd, wait_for_prompt=True)
            print(f"\n[DEBUG] \n{output}\n[END DEBUG]\n")
            if output and ("interface" in output.lower() or port in output.lower()):
                lines = output.split('\n')
                for line in lines:
                    if 'interface' in line.lower():
                        return line.strip()
                return output[:300]
        return "Описание порта не найдено"

# Получение ошибок с порта        
    def get_port_errors(self, port):
        self.client.clear_buffer()
        command = f"show interfaces counters {port}"
        output = self.client.send_command(command)
        
        #print(f"\n[DEBUG] \n{output}\n[END DEBUG]\n")
        
        if not output:
            return "Не удалось получить счетчики"
            
        lines = output.split('\n')
        analyzed_errors = []
        keywords = ['error', 'collision', 'deferred', 'late', 'excessive', 'oversize']
        
        for line in lines:
            line_lower = line.lower()
            if any(kw in line_lower for kw in keywords):
                match = re.search(r':\s*(\d+)\s*$', line)
                if match:
                    value = int(match.group(1))
                    if value > 0:
                        analyzed_errors.append(f"⚠️  {line.strip()}")
                    else:
                        analyzed_errors.append(f"✅ {line.strip()}")        
        if analyzed_errors:
            return "\n".join(analyzed_errors)
        return "Счетчики ошибок не найдены в выводе"

# Вывод
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
            print("📋 Список MAC-адресов (первые 10):")
            for i, mac in enumerate(mac_info['macs'][:10], 1):
                print(f"   {i:2}. {mac}")
            if mac_info['count'] > 10:
                print(f"   ... и еще {mac_info['count'] - 10} адресов")
        else:
            print("❌ MAC-адреса не найдены на порту")
        results['mac_count'] = mac_info['count']
        print() 
        
        return results
