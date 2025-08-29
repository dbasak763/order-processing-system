import json
import logging
from kafka import KafkaConsumer
from typing import Dict, Any, Callable
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class OrderEventConsumer:
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.consumer = None
        self.running = False
        self.event_handlers: Dict[str, Callable] = {}
        
    def register_handler(self, event_type: str, handler: Callable):
        """Register a handler for a specific event type"""
        self.event_handlers[event_type] = handler
        
    def start_consumer(self, topics: list[str]):
        """Start consuming messages from Kafka topics"""
        try:
            self.consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=self.bootstrap_servers,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                group_id='analytics-service',
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            
            self.running = True
            logger.info(f"Started consuming from topics: {topics}")
            
            for message in self.consumer:
                if not self.running:
                    break
                    
                try:
                    event_data = message.value
                    event_type = event_data.get('eventType', 'unknown')
                    
                    logger.info(f"Received event: {event_type} for order: {event_data.get('orderId')}")
                    
                    # Process event with registered handler
                    if event_type in self.event_handlers:
                        self.event_handlers[event_type](event_data)
                    else:
                        logger.warning(f"No handler registered for event type: {event_type}")
                        
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except Exception as e:
            logger.error(f"Error starting Kafka consumer: {e}")
            
    def stop_consumer(self):
        """Stop the Kafka consumer"""
        self.running = False
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer stopped")

class AnalyticsProcessor:
    def __init__(self, cassandra_session=None, redis_client=None):
        self.cassandra_session = cassandra_session
        self.redis_client = redis_client
        self.metrics_cache = {}
        
    def process_order_created(self, event_data: Dict[str, Any]):
        """Process order created events"""
        try:
            order_id = event_data.get('orderId')
            user_id = event_data.get('userId')
            total_amount = event_data.get('totalAmount', 0)
            timestamp = datetime.fromisoformat(event_data.get('timestamp'))
            
            # Update real-time metrics
            self._update_order_metrics(order_id, user_id, total_amount, timestamp)
            
            # Store in Cassandra for historical analysis
            if self.cassandra_session:
                self._store_order_event(event_data)
                
            # Update Redis cache for real-time dashboard
            if self.redis_client:
                self._update_realtime_cache(event_data)
                
            logger.info(f"Processed order created event for order: {order_id}")
            
        except Exception as e:
            logger.error(f"Error processing order created event: {e}")
            
    def process_order_status_changed(self, event_data: Dict[str, Any]):
        """Process order status change events"""
        try:
            order_id = event_data.get('orderId')
            old_status = event_data.get('oldStatus')
            new_status = event_data.get('newStatus')
            
            # Update status metrics
            self._update_status_metrics(old_status, new_status)
            
            # Store status change event
            if self.cassandra_session:
                self._store_status_change(event_data)
                
            logger.info(f"Processed status change for order {order_id}: {old_status} -> {new_status}")
            
        except Exception as e:
            logger.error(f"Error processing order status change: {e}")
            
    def process_order_cancelled(self, event_data: Dict[str, Any]):
        """Process order cancellation events"""
        try:
            order_id = event_data.get('orderId')
            reason = event_data.get('reason', 'No reason provided')
            
            # Update cancellation metrics
            self._update_cancellation_metrics(event_data)
            
            logger.info(f"Processed order cancellation for order: {order_id}, reason: {reason}")
            
        except Exception as e:
            logger.error(f"Error processing order cancellation: {e}")
            
    def _update_order_metrics(self, order_id: str, user_id: str, amount: float, timestamp: datetime):
        """Update order metrics in memory and cache"""
        hour_key = timestamp.strftime('%Y-%m-%d-%H')
        
        # Update hourly metrics
        if 'orders_per_hour' not in self.metrics_cache:
            self.metrics_cache['orders_per_hour'] = {}
        
        self.metrics_cache['orders_per_hour'][hour_key] = \
            self.metrics_cache['orders_per_hour'].get(hour_key, 0) + 1
            
        # Update revenue metrics
        self.metrics_cache['total_revenue'] = \
            self.metrics_cache.get('total_revenue', 0) + amount
            
        self.metrics_cache['total_orders'] = \
            self.metrics_cache.get('total_orders', 0) + 1
            
    def _update_status_metrics(self, old_status: str, new_status: str):
        """Update order status metrics"""
        if 'orders_by_status' not in self.metrics_cache:
            self.metrics_cache['orders_by_status'] = {}
            
        # Decrease old status count
        if old_status:
            self.metrics_cache['orders_by_status'][old_status] = \
                max(0, self.metrics_cache['orders_by_status'].get(old_status, 0) - 1)
                
        # Increase new status count
        self.metrics_cache['orders_by_status'][new_status] = \
            self.metrics_cache['orders_by_status'].get(new_status, 0) + 1
            
    def _update_cancellation_metrics(self, event_data: Dict[str, Any]):
        """Update cancellation metrics"""
        self.metrics_cache['cancelled_orders'] = \
            self.metrics_cache.get('cancelled_orders', 0) + 1
            
    def _store_order_event(self, event_data: Dict[str, Any]):
        """Store order event in Cassandra"""
        # Implementation for Cassandra storage
        pass
        
    def _store_status_change(self, event_data: Dict[str, Any]):
        """Store status change in Cassandra"""
        # Implementation for Cassandra storage
        pass
        
    def _update_realtime_cache(self, event_data: Dict[str, Any]):
        """Update Redis cache for real-time metrics"""
        if self.redis_client:
            try:
                # Store recent order for real-time display
                recent_orders_key = "recent_orders"
                self.redis_client.lpush(recent_orders_key, json.dumps(event_data))
                self.redis_client.ltrim(recent_orders_key, 0, 99)  # Keep last 100 orders
                
                # Update real-time counters
                self.redis_client.incr("total_orders_today")
                self.redis_client.incrbyfloat("revenue_today", event_data.get('totalAmount', 0))
                
            except Exception as e:
                logger.error(f"Error updating Redis cache: {e}")
                
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics from cache"""
        return self.metrics_cache.copy()
