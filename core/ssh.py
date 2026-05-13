class SSHClient:
    """Заглушка для будущего SSH подключения через subprocess"""
    def __init__(self, ip, username, password=None):
        raise NotImplementedError("SSH модуль пока не реализован (требуются системные SSH-ключи)")
