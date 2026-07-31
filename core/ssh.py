import os
import pty
import re
import select
import shlex
import subprocess
import sys
import tempfile
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
PASSWORD_RE = re.compile(
    r'(?i)(?:password|passphrase|пароль)\s*:?\s*$',
    re.MULTILINE,
)
AUTH_FAIL_RE = re.compile(
    r'(?i)(permission denied|authentication failed|login incorrect|'
    r'too many authentication failures)',
)
PROMPT_RE = re.compile(
    r'(?:' + '|'.join(CONFIG['prompt_patterns']) + r')\s*$',
    re.MULTILINE,
)


class SSHClient:
    def __init__(
        self,
        ip,
        username,
        password,
        fallback_user=None,
        fallback_pass=None,
        enable_password=None,
        debug=False,
    ):
        self.ip = ip
        self.username = username
        self.password = password
        self.fallback_user = fallback_user
        self.fallback_pass = fallback_pass
        self.enable_password = enable_password or password
        self.debug = debug
        self.proc = None
        self.master_fd = None
        self._askpass_path = None

    def _cleanup_askpass(self):
        if self._askpass_path and os.path.exists(self._askpass_path):
            try:
                os.unlink(self._askpass_path)
            except OSError:
                pass
        self._askpass_path = None

    def _create_askpass(self, password):
        """Временный askpass: OpenSSH надёжно забирает пароль отсюда, не из PTY."""
        self._cleanup_askpass()
        fd, path = tempfile.mkstemp(prefix='rk_ssh_askpass_', suffix='.sh')
        try:
            script = (
                "#!/bin/sh\n"
                f"printf '%s\\n' {shlex.quote(password)}\n"
            )
            os.write(fd, script.encode('utf-8'))
        finally:
            os.close(fd)
        os.chmod(path, 0o700)
        self._askpass_path = path
        return path

    def _ssh_env(self, password):
        env = os.environ.copy()
        for key in ('SSH_ASKPASS', 'SSH_ASKPASS_REQUIRE', 'SSH_AUTH_SOCK'):
            env.pop(key, None)

        askpass = self._create_askpass(password)
        env['SSH_ASKPASS'] = askpass
        # OpenSSH 8.4+: принудительно взять пароль из askpass
        env['SSH_ASKPASS_REQUIRE'] = 'force'
        # Нужен для старых OpenSSH, иначе askpass может не вызваться
        env.setdefault('DISPLAY', ':0')
        return env

    def connect(self):
        try:
            if not self.password:
                print("❌ Пароль SSH пустой — проверьте PASS_SSH в .env")
                return False

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
                '-o', 'IdentitiesOnly=yes',
                '-o', 'IdentityAgent=none',
                '-o', 'NumberOfPasswordPrompts=1',
                f'{self.username}@{self.ip}',
            ]

            if self.debug:
                print(
                    f"[DEBUG] SSH auth: user={self.username!r}, "
                    f"pass_len={len(self.password)}",
                    flush=True,
                )

            self.proc = subprocess.Popen(
                cmd,
                stdin=slave,
                stdout=slave,
                stderr=slave,
                close_fds=True,
                preexec_fn=os.setsid,
                env=self._ssh_env(self.password),
            )
            os.close(slave)
            return True
        except Exception as e:
            print(f"Ошибка подключения к {self.ip}: {e}")
            self._cleanup_askpass()
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
        """Ждём hostkey/prompt/ошибку. Пароль SSH отдаёт askpass."""
        try:
            if user != self.username or pwd != self.password:
                self.disconnect()
                self.username = user
                self.password = pwd
                if not self.connect():
                    return False

            timeout = CONFIG['ssh_timeout']
            end_time = time.time() + timeout
            buffer = ''
            password_sent = False

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

                if AUTH_FAIL_RE.search(clean):
                    return False

                # Fallback: если askpass не сработал и промпт пришёл в PTY
                if not password_sent and PASSWORD_RE.search(clean):
                    self._write(pwd)
                    password_sent = True
                    buffer = ''
                    continue

                if PROMPT_RE.search(clean):
                    return True

                if not self._process_alive():
                    return False

            return False
        except Exception:
            return False

    def login(self):
        if not self.password:
            print("❌ Пароль SSH пустой — проверьте PASS_SSH в .env")
            return False

        if self._attempt_login(self.username, self.password):
            return True

        if self.fallback_user and self.fallback_pass:
            print(
                f"⚠️  Основные учетные данные не подошли. "
                f"Пробуем резервные ({self.fallback_user})..."
            )
            if self._attempt_login(self.fallback_user, self.fallback_pass):
                return True
        return False

    def enter_enable(self):
        """Вход в привилегированный режим (C-Data / ZTE610 и др.)."""
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
                self._write(self.enable_password)
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
                        self._write(self.enable_password)
                        output = b''
                        continue

                    else:
                        continue

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

        self._cleanup_askpass()
