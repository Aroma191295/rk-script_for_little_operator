import telnetlib
import time
import re

# Конфигурация для Telnet
CONFIG = {
    'telnet_timeout': 10,
    'prompt_patterns': [
        b'[a-zA-Z0-9\\-]+[#>]',
        b'[a-zA-Z0-9\\-]+:\\~[#>]', 
        b'Switch>'
    ],
}

class TelnetClient:
    def __init__(self, ip, username, password, fallback_user=None, fallback_pass=None):
        self.ip = ip
        self.username = username
        self.password = password
        self.fallback_user = fallback_user
        self.fallback_pass = fallback_pass
        self.tn = None
        
    def connect(self):
        try:
            self.tn = telnetlib.Telnet(self.ip, timeout=CONFIG['telnet_timeout'])
            return True
        except Exception as e:
            print(f"Ошибка подключения к {self.ip}: {e}")
            return False

    def _attempt_login(self, user, pwd):
        try:
            login_patterns = [b'[Ll]ogin:', b'[Uu]ser:', b'[Nn]ame:', b'[Pp]assword:']
            all_patterns = login_patterns + CONFIG['prompt_patterns']
            
            result = self.tn.expect(all_patterns, timeout=CONFIG['telnet_timeout'])
            index = result[0]
            
            if index >= len(login_patterns):
                return True
                
            if index < len(login_patterns):
                if b'password' in all_patterns[index].lower():
                    self.tn.write(pwd.encode('ascii') + b'\n')
                else:
                    self.tn.write(user.encode('ascii') + b'\n')
                    self.tn.expect([b'[Pp]assword:'], timeout=CONFIG['telnet_timeout'])
                    self.tn.write(pwd.encode('ascii') + b'\n')
                
                check_patterns = CONFIG['prompt_patterns'] + [b'[Ll]ogin:', b'[Uu]ser:', b'[Nn]ame:']
                res = self.tn.expect(check_patterns, timeout=CONFIG['telnet_timeout'])
                
                if res[0] < len(CONFIG['prompt_patterns']):
                    return True
                else:
                    return False
            return False
        except (telnetlib.EOF, telnetlib.TIMEOUT):
            return False
        except Exception as e:
            return False

    def login(self):
        if self._attempt_login(self.username, self.password):
            return True
            
        if self.fallback_user and self.fallback_pass:
            print(f"⚠️  Основные учетные данные не подошли. Пробуем резервные ({self.fallback_user})...")
            if self._attempt_login(self.fallback_user, self.fallback_pass):
                return True
                
            print("⚠️  Требуется переподключение для резервной попытки...")
            self.disconnect()
            if self.connect():
                if self._attempt_login(self.fallback_user, self.fallback_pass):
                    return True
        return False

    def send_command(self, command, wait_for_prompt=True):
        """Отправка команды с умной обработкой постраничного вывода (More)"""
        try:
            self.tn.write(command.encode('ascii') + b'\n')
            
            if not wait_for_prompt:
                return ""
            
            time.sleep(0.3) # Ждем начала ответа от коммутатора
            
            output = b""
            end_time = time.time() + 15 # Максимальное время на команду 15 секунд
            
            while time.time() < end_time:
                # read_very_eager() мгновенно читает то, что есть в буфере, не зависая
                chunk = self.tn.read_very_eager()
                
                if chunk:
                    output += chunk
                else:
                    # Если буфер пуст, даем коммутатору полсекунды на раздумье
                    time.sleep(0.5)
                    chunk2 = self.tn.read_very_eager()
                    
                    if chunk2:
                        output += chunk2
                        continue # Данные пришли, продолжаем читать
                    
                    # Буфер пуст даже после паузы. Анализируем то, что накопили:
                    # Переводим накопленное в обычный текст (игнорируя ошибки)
                    text = output.decode('ascii', errors='ignore')
                    
                    # 1. Если в конце текста есть приглашение (например, Switch#)
                    if re.search(r'[a-zA-Z0-9\-]+[#>]\s*$', text):
                        break # Команда завершена, выходим из цикла!
                        
                    # 2. Если видим слово more (в любом регистре, цвета нам не помешают)
                    elif 'more' in text.lower():
                        self.tn.write(b" ") # Нажимаем Пробел
                        time.sleep(0.2)     # Ждем, пока страница прорисуется
                        continue
                        
                    # 3. Ни приглашения, ни слова More — значит зависло (таймаут)
                    else:
                        break 
                        
            # --- ФИНАЛЬНАЯ ОЧИСТКА ВЫВОДА ---
            final_output = output.decode('ascii', errors='ignore')
            
            # 1. Удаляем невидимые коды цветов ANSI (которые создавали проблемы)
            ansi_escape = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
            final_output = ansi_escape.sub('', final_output)
            
            # 2. Удаляем саму строчку с "More", чтобы она не портила красивый вывод
            final_output = re.sub(r'All: a, More:.*', '', final_output, flags=re.IGNORECASE)
            
            lines = final_output.splitlines()
            
            # 3. Отрезаем первую строку (эхо отправленной команды)
            if len(lines) > 0:
                lines = lines[1:]
                
            # 4. Отрезаем последнюю строку (само приглашение ввода)
            if len(lines) > 0:
                if re.search(r'[#>]\s*$', lines[-1].strip()):
                    lines = lines[:-1]
            
            # Склеиваем обратно в красивый текст
            return '\n'.join(lines).strip()
            
        except Exception as e:
            print(f"Ошибка выполнения команды '{command}': {e}")
            return ""
        
    def clear_buffer(self):
        try:
            self.tn.read_very_eager()
        except:
            pass
            
    def interactive_mode(self):
        print(f"\n{'='*70}")
        print(f"💻 ПЕРЕДАЧА УПРАВЛЕНИЯ КОММУТАТОРОМ {self.ip}")
        print("ℹ️  Для выхода используйте Ctrl+] затем quit")
        print(f"{'='*70}\n")
        try:
            self.tn.interact()
        except KeyboardInterrupt:
            print("\n\n⚠️  Выход из интерактивного режима")
        except Exception as e:
            print(f"Ошибка: {e}")
            
    def disconnect(self):
        if self.tn:
            try:
                self.tn.write(b'exit\n')
                self.tn.close()
            except:
                pass
            self.tn = None
