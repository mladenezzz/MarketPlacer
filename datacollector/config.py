import os

class DataCollectorConfig:
    """Configuration for DataCollector"""

    # Database connection
    DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://marketplacer_user:MarketPlacer2024!Secure@192.168.0.44:5432/marketplacer'

    # Collection intervals (in seconds)
    WILDBERRIES_INTERVAL = 3600  # 1 hour
    OZON_INTERVAL = 3600  # 1 hour

    # API rate limits
    WILDBERRIES_RATE_LIMIT = 60  # 1 request per minute
    OZON_RATE_LIMIT = 60  # 1 request per minute

    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = '/var/log/marketplacer/datacollector.log'

    # VPS settings for VLESS/Reality
    VPS_HOST = os.environ.get('VPS_HOST') or '185.171.80.56'
    VPS_SSH_PORT = int(os.environ.get('VPS_SSH_PORT') or 2211)
    VPS_SSH_USER = os.environ.get('VPS_SSH_USER') or 'mike'
    VPS_SSH_PASSWORD = os.environ.get('VPS_SSH_PASSWORD') or 'Lvl12311party'
    VPS_SSH_KEY = os.environ.get('VPS_SSH_KEY') or '''-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACB+iK9iY9rlWigQTMd5Y/gOIU/ZBGTw5yyHlqMEYLwbggAAAKD7A495+wOP
eQAAAAtzc2gtZWQyNTUxOQAAACB+iK9iY9rlWigQTMd5Y/gOIU/ZBGTw5yyHlqMEYLwbgg
AAAEAnjn+NxubPPUm1azQrj4KCcCXAMJPPCGlH7LFn2exc+n6Ir2Jj2uVaKBBMx3lj+A4h
T9kEZPDnLIeWowRgvBuCAAAAF212ZXJldGVsbmlrb3ZAZ21haWwuY29tAQIDBAUG
-----END OPENSSH PRIVATE KEY-----'''
