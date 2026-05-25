#!/usr/bin/expect -f
# Использовать: ./zte320.sh <HOST> <USER_PORT>

# Проверяем количество аргументов
if {$argc < 2} {
    puts "Usage: $argv0 <HOST> <USER_PORT>"
    exit 1
}

set HOST [lindex $argv 0]
set USER_PORT "gpon-onu_[lindex $argv 1]"
set DELAY 1
set timeout 10

# Если нужно, можно захардкодить: set USER "admin"
set USER $env(USER)
set PASS $env(PASS)

spawn telnet $HOST

expect {
    "Username:" { send "$USER\r"; exp_continue }
    "Password:" { send "$PASS\r" }
    timeout { puts "Нет ответа по таймауту"; exit 1 }
}

expect -re {[#>]$}

# Список команд
set commands [list \
    "show gpon onu detail-info $USER_PORT" \
    "show pon power attenuation $USER_PORT" \
    "show mac-real-time gpon onu $USER_PORT" \
    "show gpon remote-onu interface eth $USER_PORT" \
    "show gpon remote-onu interface video-ani $USER_PORT" \
]

foreach cmd $commands {
    send "$cmd\r"
    expect -re {[#>]$}
    sleep $DELAY
}

interact
