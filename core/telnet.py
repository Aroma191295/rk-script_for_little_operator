import telnetlib
import time
import re

# Конфигурация для Telnet
CONFIG = {
    'telnet_timeout': 10,
    'prompt_patterns': [
        # Switch#  /  LTP-8X#  /  Switch(config)#  /  Switch(config-if)#
        b'[a-zA-Z0-9\\-]+(?:\\([^)]+\\))?[#>]',
        b'[a-zA-Z0-9\\-]+:\\~[#>]',
        b'Switch>',
    ],
}

# Как в expect: ловим login / User / Username / Password
LOGIN_PATTERNS = [
    b'[Ll]ogin',                          # ltp.exp: "login"
    b'[Uu]ser(?:name)?(?:\\s*[Nn]ame)?\\s*:',  # Username: / User Name:
    b'[Uu]ser\\s*:',                      # User:
    b'[Nn]ame\\s*:',
]
PASSWORD_PATTERNS = [
    b'[Pp]assword\\s*:',
]

# Для send_command — тот же смысл, уже строкой
PROMPT_RE = re.compile(
    r'[a-zA-Z0-9\-]+(?:\([^)]+\))?[#>]\s*$'
)


class TelnetClient:
    def __init__(
        self,
        ip,
        username,
        password,
        fallback_user=None,
        fallback_pass=None,
        debug=False,
    ):
        self.ip = ip
        self.username = username
        self.password = password
        self.fallback_user = fallback_user
        self.fallback_pass = fallback_pass
        self.debug = debug
        self.tn = None

    def _debug_print(self, label, data):
        if not self.debug:
            return
        if isinstance(data, bytes):
            text = data.decode('utf-8', errors='replace')
        else:
            text = str(data)
        print(f"\n[DEBUG telnet] {label} ({len(data) if data is not None else 0} bytes)", flush=True)
        print(repr(text), flush=True)
        print("---", flush=True)
        print(text, flush=True)

    def connect(self):
        try:
            self.tn = telnetlib.Telnet(self.ip, timeout=CONFIG['telnet_timeout'])
            if self.debug:
                print(f"[DEBUG telnet] connected to {self.ip}", flush=True)
            return True
        except Exception as e:
            print(f"Ошибка подключения к {self.ip}: {e}")
            return False

    def _write(self, text):
        # Как expect: send "...\r" — LTP/Eltex ждут CR, не только LF
        if self.debug:
            print(f"[DEBUG telnet] >>> {text!r} + CR", flush=True)
        self.tn.write(text.encode('ascii') + b'\r')

    def _attempt_login(self, user, pwd):
        """
        Логика как в ltp.exp / eltex_eth.exp:

            expect {
                "login"|"User"... { send user; exp_continue }
                "Password:"       { send pass }
            }
            expect -re {[#>]$}
        """
        try:
            timeout = CONFIG['telnet_timeout']
            got_password = False
            deadline = time.time() + timeout * 3

            while time.time() < deadline:
                # Как expect: сначала только login/User и Password (без #)
                patterns = LOGIN_PATTERNS + PASSWORD_PATTERNS
                idx, match, data = self.tn.expect(patterns, timeout=timeout)
                self._debug_print(
                    f"expect idx={idx} match={match.group(0) if match else None}",
                    data,
                )

                if idx == -1:
                    print("⚠️ Telnet: таймаут ожидания login/Password")
                    return False

                n_login = len(LOGIN_PATTERNS)

                # login / username → шлём user и продолжаем ждать (как exp_continue)
                if idx < n_login:
                    self._write(user)
                    continue

                # Password: → шлём пароль и ждём prompt отдельно
                self._write(pwd)
                got_password = True
                break

            if not got_password:
                print("⚠️ Telnet: Password: не получен")
                return False

            # Как expect -re {[#>]$} — только prompt, без "Last login:"
            idx, match, data = self.tn.expect(
                CONFIG['prompt_patterns'], timeout=timeout
            )
            self._debug_print(
                f"after password, idx={idx} match={match.group(0) if match else None}",
                data,
            )

            if idx == -1:
                print("⚠️ Telnet: после пароля нет prompt (#/>) — логин не удался?")
                return False

            return True

        except (telnetlib.EOF, EOFError) as e:
            self._debug_print("EOF during login", str(e))
            return False
        except Exception as e:
            print(f"⚠️ Telnet login error: {e}")
            return False

    def login(self):
        if self._attempt_login(self.username, self.password):
            return True

        if self.fallback_user and self.fallback_pass:
            print(
                f"⚠️  Основные учетные данные не подошли. "
                f"Пробуем резервные ({self.fallback_user})..."
            )
            self.disconnect()
            if self.connect() and self._attempt_login(
                self.fallback_user, self.fallback_pass
            ):
                return True
        return False

    def send_command(self, command, wait_for_prompt=True):
        """Отправка команды с ожиданием prompt и обработкой More."""
        try:
            if self.debug:
                print(f"\n[DEBUG telnet] >>> {command!r} + CR", flush=True)

            self.tn.write(command.encode('ascii') + b'\r')

            if not wait_for_prompt:
                return ""

            time.sleep(0.3)

            output = b""
            end_time = time.time() + 15

            while time.time() < end_time:
                chunk = self.tn.read_very_eager()

                if chunk:
                    self._debug_print("chunk", chunk)
                    output += chunk
                else:
                    time.sleep(0.5)
                    chunk2 = self.tn.read_very_eager()

                    if chunk2:
                        self._debug_print("chunk2", chunk2)
                        output += chunk2
                        continue

                    text = output.decode('utf-8', errors='ignore')

                    if PROMPT_RE.search(text):
                        break
                    elif 'more' in text.lower():
                        self.tn.write(b" ")
                        time.sleep(0.2)
                        continue
                    else:
                        continue

            final_output = output.decode('utf-8', errors='ignore')

            ansi_escape = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
            final_output = ansi_escape.sub('', final_output)
            final_output = re.sub(
                r'All: a, More:.*', '', final_output, flags=re.IGNORECASE
            )

            lines = final_output.splitlines()

            if lines:
                lines = lines[1:]

            if lines and re.search(r'[#>]\s*$', lines[-1].strip()):
                lines = lines[:-1]

            result = '\n'.join(lines).strip()
            if self.debug:
                print(f"[DEBUG telnet] <<< cleaned ({len(result)} chars)", flush=True)
                print(result or "<EMPTY>", flush=True)
            return result

        except Exception as e:
            print(f"Ошибка выполнения команды '{command}': {e}")
            return ""

    def clear_buffer(self):
        try:
            leftover = self.tn.read_very_eager()
            if leftover and self.debug:
                self._debug_print("clear_buffer discarded", leftover)
        except Exception:
            pass

    def interactive_mode(self):
        print(f"\n{'=' * 70}")
        print(f"💻 ПЕРЕДАЧА УПРАВЛЕНИЯ КОММУТАТОРОМ {self.ip}")
        print("ℹ️  Для прерывания используйте Ctrl+C")
        print(f"{'=' * 70}\n")
        try:
            self.tn.interact()
        except KeyboardInterrupt:
            print("\n\n⚠️  Выход из интерактивного режима")
        except Exception as e:
            print(f"Ошибка: {e}")

    def disconnect(self):
        if self.tn:
            try:
                self.tn.write(b'exit\r')
                self.tn.close()
            except Exception:
                pass
            self.tn = None
