import logging
import time
import signal
import sys
from datetime import datetime
from datacollector.config import DataCollectorConfig
from datacollector.collectors.wildberries import WildberriesCollector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)

running = True


def signal_handler(sig, frame):
    global running
    logger.info("Shutting down gracefully...")
    running = False


def main():
    logger.info("Starting MarketPlacer DataCollector...")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # TODO: Load tokens from database
    wb_token = "test_token"

    wb_collector = WildberriesCollector(
        token=wb_token,
        database_uri=DataCollectorConfig.DATABASE_URI
    )

    last_collection = {}

    while running:
        try:
            current_time = time.time()

            # Collect Wildberries data
            if current_time - last_collection.get('wildberries', 0) >= DataCollectorConfig.WILDBERRIES_INTERVAL:
                logger.info("Collecting Wildberries data...")
                sales = wb_collector.collect_sales(days=1)
                orders = wb_collector.collect_orders(days=1)

                wb_collector.save_to_database(sales, 'wb_sales')
                wb_collector.save_to_database(orders, 'wb_orders')

                last_collection['wildberries'] = current_time

            time.sleep(60)

        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(60)

    logger.info("DataCollector stopped")


if __name__ == '__main__':
    main()
