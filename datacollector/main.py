import logging
import time
import signal
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datacollector.config import DataCollectorConfig
from datacollector.collectors.wildberries import WildberriesCollector
from app.models import Token

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)

running = True
collectors = {}


def signal_handler(sig, frame):
    global running
    logger.info("Shutting down gracefully...")
    running = False


def initialize_collectors():
    """Initialize collectors for all tokens"""
    logger.info("Initializing collectors for all tokens...")

    engine = create_engine(DataCollectorConfig.DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        tokens = session.query(Token).filter_by(marketplace='wildberries').all()
        logger.info(f"Found {len(tokens)} Wildberries tokens")

        for token in tokens:
            logger.info(f"Creating collector for token {token.id} ({token.name})")
            collector = WildberriesCollector(
                token_id=token.id,
                token=token.token,
                database_uri=DataCollectorConfig.DATABASE_URI
            )
            collectors[token.id] = collector

            logger.info(f"Starting initial collection for token {token.id}")
            collector.collect_all()

    except Exception as e:
        logger.error(f"Error initializing collectors: {e}")
    finally:
        session.close()

    logger.info("Initialization complete")


def update_all_collectors():
    """Update data for all collectors"""
    logger.info(f"Updating data for {len(collectors)} collectors...")

    for token_id, collector in collectors.items():
        try:
            collector.update_data()
        except Exception as e:
            logger.error(f"Error updating token {token_id}: {e}")

    logger.info("Update complete")


def main():
    logger.info("Starting MarketPlacer DataCollector...")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    initialize_collectors()

    last_update = time.time()
    update_interval = 600

    while running:
        try:
            current_time = time.time()

            if current_time - last_update >= update_interval:
                update_all_collectors()
                last_update = current_time

            time.sleep(60)

        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(60)

    logger.info("DataCollector stopped")


if __name__ == '__main__':
    main()
