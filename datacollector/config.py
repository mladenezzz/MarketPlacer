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
