"""
Сервис для управления VPS через SSH
"""
import paramiko
import json
from io import StringIO


class VPSService:
    """Сервис для подключения к VPS и управления Xray"""

    def __init__(self, host, port, username, password=None, private_key=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.private_key = private_key
        self.client = None

    def connect(self):
        """Установить SSH соединение"""
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs = {
            'hostname': self.host,
            'port': self.port,
            'username': self.username,
        }

        if self.private_key:
            # Используем приватный ключ (поддержка разных типов ключей)
            key_file = StringIO(self.private_key)
            try:
                pkey = paramiko.Ed25519Key.from_private_key(key_file)
            except Exception:
                key_file.seek(0)
                try:
                    pkey = paramiko.RSAKey.from_private_key(key_file)
                except Exception:
                    key_file.seek(0)
                    pkey = paramiko.ECDSAKey.from_private_key(key_file)
            connect_kwargs['pkey'] = pkey
        elif self.password:
            # Используем пароль
            connect_kwargs['password'] = self.password

        self.client.connect(**connect_kwargs)

    def disconnect(self):
        """Закрыть SSH соединение"""
        if self.client:
            self.client.close()
            self.client = None

    def execute(self, command):
        """Выполнить команду на VPS"""
        if not self.client:
            self.connect()

        stdin, stdout, stderr = self.client.exec_command(command)
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')

        return {
            'exit_code': exit_code,
            'output': output,
            'error': error
        }

    def write_file(self, path, content):
        """Записать файл на VPS"""
        if not self.client:
            self.connect()

        sftp = self.client.open_sftp()
        with sftp.file(path, 'w') as f:
            f.write(content)
        sftp.close()

    def read_file(self, path):
        """Прочитать файл с VPS"""
        if not self.client:
            self.connect()

        sftp = self.client.open_sftp()
        with sftp.file(path, 'r') as f:
            content = f.read().decode('utf-8')
        sftp.close()
        return content

    def update_xray_config(self, config_dict):
        """Обновить конфигурацию Xray"""
        config_path = '/usr/local/etc/xray/config.json'
        config_json = json.dumps(config_dict, indent=2, ensure_ascii=False)

        # Записываем конфиг во временный файл и перемещаем с sudo
        tmp_path = '/tmp/xray_config.json'
        self.write_file(tmp_path, config_json)

        # Перемещаем с sudo
        result = self.execute(f'sudo mv {tmp_path} {config_path}')
        if result['exit_code'] != 0:
            raise Exception(f"Ошибка записи конфига: {result['error']}")

        # Перезапускаем Xray
        result = self.execute('sudo systemctl restart xray')

        if result['exit_code'] != 0:
            raise Exception(f"Ошибка перезапуска Xray: {result['error']}")

        # Проверяем статус
        status = self.execute('sudo systemctl is-active xray')
        if status['output'].strip() != 'active':
            raise Exception("Xray не запустился после обновления конфига")

        return True

    def get_xray_config(self):
        """Прочитать текущий конфиг Xray"""
        config_path = '/usr/local/etc/xray/config.json'
        try:
            content = self.read_file(config_path)
            return json.loads(content)
        except Exception:
            return None

    def get_xray_status(self):
        """Получить статус Xray"""
        result = self.execute('systemctl is-active xray')
        is_active = result['output'].strip() == 'active'

        # Получаем uptime и версию
        info = {}
        if is_active:
            version_result = self.execute('xray version | head -1')
            info['version'] = version_result['output'].strip()

            # Проверяем порт
            port_result = self.execute('ss -tlnp | grep 443')
            info['listening'] = '443' in port_result['output']

        return {
            'is_active': is_active,
            'info': info
        }

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


def generate_xray_config(users, private_key, short_id="abcd1234"):
    """
    Генерация конфигурации Xray на основе списка пользователей

    Args:
        users: список объектов VPNUser
        private_key: приватный ключ Reality
        short_id: короткий ID для Reality
    """
    # Формируем список клиентов
    clients = []
    for user in users:
        if user.is_active:
            clients.append({
                "id": user.uuid,
                "email": user.email,
                "flow": "xtls-rprx-vision"
            })

    # Формируем правила маршрутизации
    routing_rules = []

    # Блокируем LAN для пользователей с режимом proxy_only
    proxy_only_users = [u.email for u in users if u.is_active and u.access_mode == 'proxy_only']
    if proxy_only_users:
        routing_rules.append({
            "type": "field",
            "user": proxy_only_users,
            "ip": ["10.0.0.0/8", "192.168.0.0/16"],
            "outboundTag": "block"
        })

    config = {
        "log": {
            "loglevel": "warning"
        },
        "inbounds": [{
            "port": 443,
            "protocol": "vless",
            "tag": "vless-in",
            "settings": {
                "clients": clients,
                "decryption": "none"
            },
            "streamSettings": {
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "dest": "www.microsoft.com:443",
                    "serverNames": ["www.microsoft.com", "microsoft.com"],
                    "privateKey": private_key,
                    "shortIds": [short_id, ""]
                }
            },
            "sniffing": {
                "enabled": True,
                "destOverride": ["http", "tls"]
            }
        }],
        "outbounds": [
            {"tag": "direct", "protocol": "freedom"},
            {"tag": "block", "protocol": "blackhole"}
        ]
    }

    # Добавляем routing только если есть правила
    if routing_rules:
        config["routing"] = {"rules": routing_rules}

    return config
