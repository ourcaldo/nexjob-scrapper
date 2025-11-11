"""
Main entry point for the job scraper application.
"""

import logging
from src.config.settings import settings
from src.services.scraper_service import ScraperService


def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Main execution function."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Initializing Job Scraper Service...")
    
    try:
        scraper = ScraperService(settings)
        scraper.run_continuous()
    except KeyboardInterrupt:
        logger.info("Scraper stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
