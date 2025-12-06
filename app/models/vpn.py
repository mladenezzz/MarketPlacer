from app.models import db
from datetime import datetime
import uuid


class VPNUser(db.Model):
    """Модель пользователя VPN (VLESS/Reality)"""
    __tablename__ = 'vpn_users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(100), unique=True, nullable=False)  # email для Xray (user@mode)

    # Режим доступа: full, lan_only, proxy_only
    access_mode = db.Column(db.String(20), nullable=False, default='proxy_only')

    # Статистика
    traffic_up = db.Column(db.BigInteger, default=0)  # Исходящий трафик в байтах
    traffic_down = db.Column(db.BigInteger, default=0)  # Входящий трафик в байтах
    last_used_at = db.Column(db.DateTime)

    # Статус
    is_active = db.Column(db.Boolean, default=True)

    # Метаданные
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def get_access_mode_display(self):
        """Получить название режима на русском"""
        modes = {
            'full': 'Полный (LAN + Интернет)',
            'lan_only': 'Только LAN',
            'proxy_only': 'Только Интернет'
        }
        return modes.get(self.access_mode, 'Неизвестно')

    def get_traffic_display(self):
        """Получить трафик в читаемом формате"""
        total = self.traffic_up + self.traffic_down
        if total < 1024:
            return f"{total} B"
        elif total < 1024 * 1024:
            return f"{total / 1024:.1f} KB"
        elif total < 1024 * 1024 * 1024:
            return f"{total / (1024 * 1024):.1f} MB"
        else:
            return f"{total / (1024 * 1024 * 1024):.2f} GB"

    def generate_vless_link(self, server_ip, server_port=443, public_key=None, short_id="abcd1234"):
        """Генерация VLESS ссылки для клиента"""
        if not public_key:
            return None

        mode_names = {
            'full': 'Full',
            'lan_only': 'LAN',
            'proxy_only': 'Proxy'
        }
        name = f"VPS-{mode_names.get(self.access_mode, 'VPN')}"

        link = (
            f"vless://{self.uuid}@{server_ip}:{server_port}"
            f"?encryption=none&flow=xtls-rprx-vision&security=reality"
            f"&sni=www.microsoft.com&fp=chrome&pbk={public_key}"
            f"&sid={short_id}&type=tcp#{name}"
        )
        return link

    def __repr__(self):
        return f'<VPNUser {self.name} ({self.access_mode})>'
