from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging
from .models import OrderMetrics, ProductMetrics, UserMetrics, RealtimeStats
from .kafka_consumer import AnalyticsProcessor
from .database import DatabaseConnections

logger = logging.getLogger(__name__)

app = FastAPI(title="Order Analytics API", version="1.0.0")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
db_connections = DatabaseConnections()
analytics_processor = AnalyticsProcessor()
websocket_connections: List[WebSocket] = []

@app.on_event("startup")
async def startup_event():
    """Initialize database connections on startup"""
    db_connections.connect_redis()
    db_connections.connect_cassandra()
    analytics_processor.redis_client = db_connections.redis_client
    analytics_processor.cassandra_session = db_connections.cassandra_session

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown"""
    db_connections.close_connections()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "redis": db_connections.redis_client is not None,
            "cassandra": db_connections.cassandra_session is not None
        }
    }

@app.get("/metrics/orders", response_model=OrderMetrics)
async def get_order_metrics():
    """Get overall order metrics"""
    try:
        metrics = analytics_processor.get_current_metrics()
        
        total_orders = metrics.get('total_orders', 0)
        total_revenue = metrics.get('total_revenue', 0.0)
        orders_by_status = metrics.get('orders_by_status', {})
        orders_per_hour = metrics.get('orders_per_hour', {})
        
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0.0
        
        return OrderMetrics(
            total_orders=total_orders,
            total_revenue=total_revenue,
            orders_by_status=orders_by_status,
            avg_order_value=avg_order_value,
            orders_per_hour=orders_per_hour
        )
    except Exception as e:
        logger.error(f"Error getting order metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve order metrics")

@app.get("/metrics/realtime", response_model=RealtimeStats)
async def get_realtime_stats():
    """Get real-time statistics"""
    try:
        # Calculate orders per minute from recent data
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Get recent orders from Redis
        recent_orders = []
        if db_connections.redis_client:
            recent_orders_data = db_connections.redis_client.lrange("recent_orders", 0, 99)
            recent_orders = [json.loads(order) for order in recent_orders_data[:10]]
        
        # Calculate real-time metrics
        orders_per_minute = len([o for o in recent_orders 
                               if datetime.fromisoformat(o.get('timestamp', '')) > minute_ago])
        
        revenue_per_minute = sum([float(o.get('totalAmount', 0)) for o in recent_orders 
                                if datetime.fromisoformat(o.get('timestamp', '')) > minute_ago])
        
        # Mock top products (in real implementation, query from Cassandra)
        top_products = [
            ProductMetrics(
                product_id="1",
                product_name="Wireless Headphones",
                total_quantity_sold=150,
                total_revenue=14999.50,
                order_count=75
            ),
            ProductMetrics(
                product_id="2", 
                product_name="Phone Case",
                total_quantity_sold=200,
                total_revenue=3999.00,
                order_count=100
            )
        ]
        
        return RealtimeStats(
            current_orders_per_minute=float(orders_per_minute),
            revenue_per_minute=revenue_per_minute,
            active_users=25,  # Mock data
            top_products=top_products,
            recent_orders=recent_orders
        )
        
    except Exception as e:
        logger.error(f"Error getting realtime stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve realtime stats")

@app.get("/metrics/revenue/hourly")
async def get_hourly_revenue(hours: int = 24):
    """Get hourly revenue data"""
    try:
        metrics = analytics_processor.get_current_metrics()
        orders_per_hour = metrics.get('orders_per_hour', {})
        
        # Generate hourly data for the last N hours
        now = datetime.now()
        hourly_data = []
        
        for i in range(hours):
            hour = now - timedelta(hours=i)
            hour_key = hour.strftime('%Y-%m-%d-%H')
            order_count = orders_per_hour.get(hour_key, 0)
            
            hourly_data.append({
                "hour": hour.strftime('%H:00'),
                "orders": order_count,
                "revenue": order_count * 99.99  # Mock average order value
            })
            
        return {"data": list(reversed(hourly_data))}
        
    except Exception as e:
        logger.error(f"Error getting hourly revenue: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve hourly revenue")

@app.get("/metrics/products/top")
async def get_top_products(limit: int = 10):
    """Get top performing products"""
    try:
        # In real implementation, query from Cassandra
        top_products = [
            {
                "product_id": "1",
                "product_name": "Wireless Headphones",
                "total_quantity_sold": 150,
                "total_revenue": 14999.50,
                "order_count": 75
            },
            {
                "product_id": "2",
                "product_name": "Phone Case", 
                "total_quantity_sold": 200,
                "total_revenue": 3999.00,
                "order_count": 100
            },
            {
                "product_id": "3",
                "product_name": "Laptop Stand",
                "total_quantity_sold": 80,
                "total_revenue": 7999.20,
                "order_count": 40
            }
        ]
        
        return {"products": top_products[:limit]}
        
    except Exception as e:
        logger.error(f"Error getting top products: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve top products")

@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        while True:
            # Send real-time updates every 5 seconds
            await asyncio.sleep(5)
            
            # Get current metrics
            realtime_stats = await get_realtime_stats()
            
            # Send to client
            await websocket.send_text(realtime_stats.json())
            
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

async def broadcast_update(data: Dict[str, Any]):
    """Broadcast updates to all connected WebSocket clients"""
    if websocket_connections:
        message = json.dumps(data)
        for websocket in websocket_connections.copy():
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error sending WebSocket message: {e}")
                websocket_connections.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8091)
