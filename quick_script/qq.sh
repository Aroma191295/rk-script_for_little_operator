#!/usr/bin/expect

################## Инструкция ######################################

# Использовать:

# qq 10.0.0.1 - подключение под собой telnet
# qq-ssh 10.0.0.1 - подключение под собой ssh
# qq 10.0.0.1 admin - подключение под админом telnet
# qq-ssh 10.0.0.1 admin - подключение под админом ssh

# Создать alias:

# cat >> ~/.bash_aliases << EOF
# alias qq='<расположение файла>/qq.sh telnet'
# alias qq-ssh='<расположение файла>/qq.sh ssh'
# EOF

# chmod 700 <расположение файла>/qq.sh - дать права на выполнение

# source ./.bashrc - перечитать фаил с alias

# Можно заменить переменные PASS и PASS_SSH на необходимые вам.
# PASS - это ваш пароль от Active Directory
# PASS_SSH - пароль от админа

####################################################################

# Установка аргументов
set timeout 10
set protocol [lindex $argv 0]
set ip [lindex $argv 1]

if {[llength $argv] >= 3} {
    set user [lindex $argv 2]
} else {
    set user $env(USER)   
}

if {$user != "admin"} {
    set pass $env(PASS)
    # set pass "Ваш пароль"
} else {
    set pass $env(PASS_SSH)
    # set pass "Админ пароль"
}

# Проверка протокола
if {$protocol != "ssh" && $protocol != "telnet"} {
    puts "Error: Protocol must be 'ssh' or 'telnet'"
    exit 1
}

if {$protocol == "ssh"} {
    # SSH
    spawn ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $user@$ip
    
    expect {
        # Проверка на доступность
        timeout { puts "Timeout"; exit 1 }
        eof { puts "Connection closed"; exit 1 }
        "Connection refused" { puts "Connection refused"; exit 1 }
        
        # Подтверждение нового хоста
        "Are you sure you want to continue connecting (yes/no)?" {
            send "yes\r"
            exp_continue
        }
        
        # Запрос пароля
        "password:" {
            send "$pass\r"
            exp_continue
        }
                
        -re {[a-zA-Z0-9\-]+[#>]} {
            interact
            exit 0
        }
    }
    
} elseif {$protocol == "telnet"} {
    # Telnet
    spawn telnet $ip
    
    expect {
        # Проверка на доступность
        timeout {puts "Telnet Timeout"; exit 1}
        eof {puts "Telnet Connection closed"; exit 1}
        "Connection refused" {puts "Telnet Connection refused"; exit 1}
        
        # Ввод логина и пароля
        -re ".*:.*" {
            set buf $expect_out(buffer)
            if {[regexp -nocase "name|login|user" $buf]} {
                send "$user\r"
                exp_continue
            } elseif {[regexp -nocase "pass" $buf]} {
                send "$pass\r"
                exp_continue
            } else {
                send "\r"
                exp_continue
            }
        }
        
        -re {[a-zA-Z0-9\-]+[#>]} {
            interact
            exit 0
        }
    }
}
