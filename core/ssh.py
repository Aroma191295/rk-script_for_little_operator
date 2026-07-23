import os
import pty
import re
import select
import subprocess
import sys
import time


# Конфигурация для SSH (аналогично telnet)
CONFIG = {
    'ssh_timeout': 10,
    'prompt_patterns': [
        r'[a-zA-Z0-9\-]+[#>]',
        r'[a-zA-Z0-9\-]+:\~[#>]',
        r'Switch>',
    ],
}

ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
HOSTKEY_RE = re.compile(
    r'Are you sure you want to continue connecting',
    re.IGNORECASE,
)
PASSWORD_RE = re.compile(r'(?i)password\s*:?\s*$', re.MULTILINE)
PROMPT_RE = re.compile(
    r'(?:' + '|'.join(CONFIG['prompt_patterns']) + r')\s*$',
    re.MULTILINE,
)


class SSHClient:
    def __init__(self, ip, username, password, fallback_user=None, fallback_pass=None, debug=False):
        self.ip = ip
        self.username = username
        self.password = password
        self.fallback_user = fallback_user
        self.fallback_pass = fallback_pass
        self.debug = debug
        self.proc = None
        self.master_fd = None

    def connect(self):
        try:
            master, slave = pty.openpty()
            self.master_fd = master

            cmd = [
                'ssh',
                '-tt',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'LogLevel=ERROR',
                '-o', 'PreferredAuthentications=password,keyboard-interactive',
                '-o', 'PubkeyAuthentication=no',
                f'{self.username}@{self.ip}',
            ]

            self.proc = subprocess.Popen(
                cmd,
                stdin=slave,
                stdout=slave,
                stderr=slave,
                close_fds=True,
                preexec_fn=os.setsid,
            )
            os.close(slave)
            return True
        except Exception as e:
            print(f"Ошибка подключения к {self.ip}: {e}")
            return False

    def _debug_print(self, text):
        if not self.debug or not text:
            return
        sys.stdout.write(ANSI_ESCAPE.sub('', text))
        sys.stdout.flush()

    def _read_available(self, timeout=0.5):
        if self.master_fd is None:
            return b''

        output = b''
        end_time = time.time() + timeout

        while time.time() < end_time:
            ready, _, _ = select.select([self.master_fd], [], [], 0.1)
            if not ready:
                if output:
                    break
                continue

            try:
                chunk = os.read(self.master_fd, 4096)
            except OSError:
                break

            if not chunk:
                break
            output += chunk

        return output

    def _write(self, text):
        """Пишем в PTY как expect: строки завершаем \\r."""
        if self.master_fd is None:
            return
        if text.endswith('\n') and not text.endswith('\r\n'):
            text = text[:-1] + '\r'
        elif not text.endswith('\r'):
            text = text + '\r'
        os.write(self.master_fd, text.encode('utf-8', errors='ignore'))

    def _clean(self, text):
        return ANSI_ESCAPE.sub('', text)

    def _process_alive(self):
        return self.proc is not None and self.proc.poll() is None

    def _attempt_login(self, user, pwd):
        """Аналог telnet._attempt_login: ждём password/hostkey/prompt."""
        try:
            # При смене пользователя нужно перезапустить ssh-сессию
            if user != self.username:
                self.disconnect()
                self.username = user
                if not self.connect():
                    return False

            timeout = CONFIG['ssh_timeout']
            end_time = time.time() + timeout
            buffer = ''

            while time.time() < end_time:
                chunk = self._read_available(timeout=0.5)
                if chunk:
                    decoded = chunk.decode('utf-8', errors='ignore')
                    self._debug_print(decoded)
                    buffer += decoded

                clean = self._clean(buffer)

                if HOSTKEY_RE.search(clean):
                    self._write('yes')
                    buffer = ''
                    continue

                if PASSWORD_RE.search(clean):
                    self._write(pwd)
                    # После пароля ждём промпт (или снова login-ошибку)
                    matched = self._wait_for_prompt_or_password(timeout)
                    return matched

                if PROMPT_RE.search(clean):
                    return True

                if not self._process_alive():
                    return False

            return False
        except Exception:
            return False

    def _wait_for_prompt_or_password(self, timeout=None):
        timeout = timeout or CONFIG['ssh_timeout']
        end_time = time.time() + timeout
        buffer = ''

        while time.time() < end_time:
            chunk = self._read_available(timeout=0.5)
            if chunk:
                decoded = chunk.decode('utf-8', errors='ignore')
                self._debug_print(decoded)
                buffer += decoded

            clean = self._clean(buffer)

            if PROMPT_RE.search(clean):
                return True

            # Снова password / login failure — значит учётные данные не подошли
            if PASSWORD_RE.search(clean) or re.search(
                r'(?i)(permission denied|authentication failed|login incorrect)',
                clean,
            ):
                return False

            if not self._process_alive():
                return False

        return False

    def login(self):
        if self._attempt_login(self.username, self.password):
            return True

        if self.fallback_user and self.fallback_pass:
            print(
                f"⚠️  Основные учетные данные не подошли. "
                f"Пробуем резервные ({self.fallback_user})..."
            )
            if self._attempt_login(self.fallback_user, self.fallback_pass):
                return True

            print("⚠️  Требуется переподключение для резервной попытки...")
            self.disconnect()
            self.username = self.fallback_user
            if self.connect():
                if self._attempt_login(self.fallback_user, self.fallback_pass):
                    return True
        return False

    def enter_enable(self):
        """Вход в привилегированный режим (нужен для C-Data OLT)."""
        self._write('enable')
        time.sleep(0.3)

        timeout = CONFIG['ssh_timeout']
        end_time = time.time() + timeout
        buffer = ''

        while time.time() < end_time:
            chunk = self._read_available(timeout=0.5)
            if chunk:
                decoded = chunk.decode('utf-8', errors='ignore')
                self._debug_print(decoded)
                buffer += decoded

            clean = self._clean(buffer)

            if PASSWORD_RE.search(clean):
                self._write(self.password)
                buffer = ''
                continue

            if PROMPT_RE.search(clean):
                return True

            if not self._process_alive():
                return False

        return False

    def send_command(self, command, wait_for_prompt=True):
        """Отправка команды с умной обработкой постраничного вывода (More) — как в telnet."""
        try:
            if self.debug:
                print(f"\n[DEBUG] >>> {command}", flush=True)

            self._write(command)

            if not wait_for_prompt:
                return ''

            time.sleep(0.3)  # Ждём начала ответа от коммутатора

            output = b''
            end_time = time.time() + 15  # Максимальное время на команду 15 секунд

            while time.time() < end_time:
                chunk = self._read_available(timeout=0.1)

                if chunk:
                    self._debug_print(chunk.decode('utf-8', errors='ignore'))
                    output += chunk
                else:
                    # Если буфер пуст, даём устройству полсекунды на раздумье
                    time.sleep(0.5)
                    chunk2 = self._read_available(timeout=0.1)

                    if chunk2:
                        self._debug_print(chunk2.decode('utf-8', errors='ignore'))
                        output += chunk2
                        continue

                    # Буфер пуст даже после паузы. Анализируем накопленное:
                    text = self._clean(output.decode('utf-8', errors='ignore'))

                    # 1. Приглашение в конце (например Switch#)
                    if re.search(r'[a-zA-Z0-9\-]+[#>]\s*$', text):
                        break

                    # 2. Постраничный вывод More
                    elif 'more' in text.lower():
                        os.write(self.master_fd, b' ')
                        time.sleep(0.2)
                        continue

                    # 3. Внезапный Password: (например после enable)
                    elif PASSWORD_RE.search(text):
                        self._write(self.password)
                        output = b''
                        continue

                    # 4. Ни приглашения, ни More — зависло
                    else:
                        break

            # --- ФИНАЛЬНАЯ ОЧИСТКА ВЫВОДА ---
            final_output = self._clean(output.decode('utf-8', errors='ignore'))

            # Удаляем строчки с "More"
            final_output = re.sub(
                r'All: a, More:.*', '', final_output, flags=re.IGNORECASE
            )

            lines = final_output.splitlines()

            # Отрезаем первую строку (эхо команды)
            if lines:
                lines = lines[1:]

            # Отрезаем последнюю строку (приглашение)
            if lines and re.search(r'[#>]\s*$', lines[-1].strip()):
                lines = lines[:-1]

            if self.debug:
                print(f"\n[DEBUG] <<< end ({len(output)} bytes)", flush=True)

            return '\n'.join(lines).strip()

        except Exception as e:
            print(f"Ошибка выполнения команды '{command}': {e}")
            return ''

    def clear_buffer(self):
        if self.master_fd is None:
            return
        try:
            while True:
                ready, _, _ = select.select([self.master_fd], [], [], 0)
                if not ready:
                    break
                if not os.read(self.master_fd, 4096):
                    break
        except Exception:
            pass

    def interactive_mode(self):
        print(f"\n{'='*70}")
        print(f"💻 ПЕРЕДАЧА УПРАВЛЕНИЯ КОММУТАТОРОМ {self.ip}")
        print("ℹ️  Для прерывания используйте Ctrl+C")
        print(f"{'='*70}\n")

        import termios
        import tty

        old_tty = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())
            while self._process_alive():
                ready, _, _ = select.select(
                    [sys.stdin, self.master_fd], [], [], 0.1
                )
                if sys.stdin in ready:
                    data = os.read(sys.stdin.fileno(), 1024)
                    if not data:
                        break
                    os.write(self.master_fd, data)
                if self.master_fd in ready:
                    data = os.read(self.master_fd, 4096)
                    if not data:
                        break
                    os.write(sys.stdout.fileno(), data)
        except KeyboardInterrupt:
            print("\n\n⚠️  Выход из интерактивного режима")
        except Exception as e:
            print(f"Ошибка: {e}")
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)

    def disconnect(self):
        if self.master_fd is not None:
            try:
                self._write('exit')
                time.sleep(0.2)
            except Exception:
                pass

        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=3)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None

        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None
