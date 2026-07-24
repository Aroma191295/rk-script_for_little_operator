# Общая загрузка .env для скриптов quick_script/
# Использование:
#   set script_dir [file dirname [file normalize [info script]]]
#   source [file join $script_dir "dotenv.tcl"]
#   init_dotenv $script_dir
#   set USER [dotenv_require USER]
#   set PASS [dotenv_require PASS]

proc load_dotenv {path} {
    if {![file exists $path]} {
        return 0
    }
    set fh [open $path r]
    while {[gets $fh line] >= 0} {
        set line [string trim $line]
        if {$line eq "" || [string match "#*" $line]} {
            continue
        }
        if {[regexp {^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$} $line -> key value]} {
            set value [string trim $value]
            if {[regexp {^"(.*)"$} $value -> inner]} {
                set value $inner
            } elseif {[regexp {^'(.*)'$} $value -> inner]} {
                set value $inner
            }
            set ::dotenv($key) $value
        }
    }
    close $fh
    return 1
}

proc dotenv_get {key} {
    if {[info exists ::dotenv($key)] && $::dotenv($key) ne ""} {
        return $::dotenv($key)
    }
    return ""
}

proc dotenv_require {key} {
    set value [dotenv_get $key]
    if {$value eq ""} {
        puts "Error: в .env не задан $key ($::env_file)"
        exit 1
    }
    return $value
}

# script_dir — каталог вызывающего .exp (quick_script/)
# Ищет ../.env, затем ~/.env
proc init_dotenv {script_dir} {
    set ::env_file [file normalize [file join $script_dir ".." ".env"]]
    set home_env [file join $::env(HOME) ".env"]

    if {![load_dotenv $::env_file]} {
        if {![load_dotenv $home_env]} {
            puts "Error: .env не найден ($::env_file или $home_env)"
            exit 1
        }
        set ::env_file $home_env
    }
}
