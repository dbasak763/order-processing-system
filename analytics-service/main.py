import asyncio
import logging
import threading
from app.kafka_consumer import OrderEventConsumer, AnalyticsProcessor
from app.database import DatabaseConnections
from app.api import app
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self):
        self.db_connections = DatabaseConnections()
        self.analytics_processor = None
        self.kafka_consumer = None
        self.consumer_thread = None
        
    def start(self):
        """Start the analytics service"""
        logger.info("Starting Analytics Service...")
        
        # Initialize database connections
        redis_client = self.db_connections.connect_redis()
        cassandra_session = self.db_connections.connect_cassandra()
        
        # Initialize analytics processor
        self.analytics_processor = AnalyticsProcessor(
            cassandra_session=cassandra_session,
            redis_client=redis_client
        )
        
        # Initialize Kafka consumer
        self.kafka_consumer = OrderEventConsumer()
        
        # Register event handlers
        self.kafka_consumer.register_handler(
            "OrderCreatedEvent", 
            self.analytics_processor.process_order_created
        )
        self.kafka_consumer.register_handler(
            "OrderStatusChangedEvent", 
            self.analytics_processor.process_order_status_changed
        )
        self.kafka_consumer.register_handler(
            "OrderCancelledEvent", 
            self.analytics_processor.process_order_cancelled
        )
        
        # Start Kafka consumer in separate thread
        self.consumer_thread = threading.Thread(
            target=self.kafka_consumer.start_consumer,
            args=[["order-events", "order-analytics"]],
            daemon=True
        )
        self.consumer_thread.start()
        
        logger.info("Analytics Service started successfully")
        
    def stop(self):
        """Stop the analytics service"""
        logger.info("Stopping Analytics Service...")
        
        if self.kafka_consumer:
            self.kafka_consumer.stop_consumer()
            
        if self.consumer_thread:
            self.consumer_thread.join(timeout=5)
            
        self.db_connections.close_connections()
        
        logger.info("Analytics Service stopped")

def main():
    """Main entry point"""
    analytics_service = AnalyticsService()
    
    try:
        # Start analytics service
        analytics_service.start()
        
        # Start FastAPI server
        logger.info("Starting FastAPI server on port 8091...")
        uvicorn.run(
            "app.api:app",
            host="0.0.0.0",
            port=8091,
            reload=False,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Error running analytics service: {e}")
    finally:
        analytics_service.stop()

if __name__ == "__main__":
    main()
