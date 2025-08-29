# Order Processing System - Testing Guide

## ✅ Implementation Status

The core order processing system is **COMPLETE** and ready for testing! Here's what has been implemented:

### 🏗️ Backend Components
- ✅ Spring Boot 3.x application with Java 17
- ✅ Complete JPA entity model (User, Product, Order, OrderItem)
- ✅ Repository layer with advanced queries and pagination
- ✅ Service layer with comprehensive business logic
- ✅ REST controllers with full CRUD operations
- ✅ Global exception handling and validation
- ✅ Security configuration with Basic Auth
- ✅ Redis caching integration
- ✅ Flyway database migrations with sample data

### 🐳 Infrastructure
- ✅ Docker Compose configuration for PostgreSQL, Redis, pgAdmin
- ✅ Database initialization scripts
- ✅ Maven configuration with all dependencies

### 🧪 Testing Setup
- ✅ Test configuration and basic test structure
- ✅ Shell scripts for automated startup and testing
- ✅ Maven wrapper for consistent builds

## 🚀 How to Test the System

### Step 1: Start Docker
First, make sure Docker Desktop is running on your Mac:
1. Open Docker Desktop application
2. Wait for it to start (you'll see the whale icon in the menu bar)
3. Verify with: `docker --version`

### Step 2: Start Infrastructure Services
```bash
cd /Users/diwakar/CascadeProjects/order-processing-system

# Start PostgreSQL, Redis, and pgAdmin
./scripts/start-infrastructure.sh
```

This will start:
- **PostgreSQL** on port 5432 (database)
- **Redis** on port 6379 (caching)
- **pgAdmin** on port 8081 (database management UI)

### Step 3: Start the Order Service
```bash
# Start the Spring Boot application
./scripts/start-order-service.sh
```

The service will be available at: `http://localhost:8090/api`

### Step 4: Test the API
```bash
# Run comprehensive API tests
./scripts/test-api.sh
```

## 🔍 Manual Testing

### Authentication
All API endpoints require Basic Authentication:
- **Username**: `admin`
- **Password**: `admin123`

### Key Test Scenarios

#### 1. Health Check
```bash
curl -u admin:admin123 http://localhost:8090/actuator/health
```

#### 2. View Sample Data
```bash
# Get all users
curl -u admin:admin123 "http://localhost:8090/api/users"

# Get all products
curl -u admin:admin123 "http://localhost:8090/api/products"

# Get all orders
curl -u admin:admin123 "http://localhost:8090/api/orders"
```

#### 3. Create a New Order
```bash
curl -u admin:admin123 -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "550e8400-e29b-41d4-a716-446655440001",
    "items": [
      {
        "productId": "660e8400-e29b-41d4-a716-446655440001",
        "quantity": 2
      }
    ],
    "taxAmount": 8.00,
    "shippingAmount": 9.99,
    "notes": "Test order from manual testing"
  }' \
  http://localhost:8090/api/orders
```

#### 4. Update Order Status
```bash
# First, get an order ID from the previous step or existing orders
ORDER_ID="<order-id-from-response>"

# Update order status to SHIPPED
curl -u admin:admin123 -X PUT \
  "http://localhost:8090/api/orders/${ORDER_ID}/status?status=SHIPPED"
```

#### 5. Test Analytics
```bash
# Get total revenue
curl -u admin:admin123 "http://localhost:8090/api/orders/analytics/revenue"

# Get order count by status
curl -u admin:admin123 "http://localhost:8090/api/orders/analytics/count/PENDING"
```

## 🎯 What to Verify

### ✅ Core Functionality
- [ ] Application starts without errors
- [ ] Database connection works
- [ ] Redis caching works
- [ ] Sample data is loaded correctly
- [ ] All API endpoints respond correctly
- [ ] Authentication works
- [ ] Order creation works with stock validation
- [ ] Order status updates work
- [ ] Order cancellation restores stock
- [ ] Analytics endpoints return correct data

### ✅ Data Validation
- [ ] Invalid order data is rejected with proper error messages
- [ ] Stock validation prevents overselling
- [ ] User and product validation works
- [ ] Pagination and filtering work correctly

### ✅ Error Handling
- [ ] 404 errors for non-existent resources
- [ ] 400 errors for invalid data
- [ ] 401 errors for missing authentication
- [ ] Proper error response format

## 🗄️ Database Access

### pgAdmin Web Interface
- **URL**: http://localhost:8081
- **Email**: `admin@orderapp.com`
- **Password**: `admin123`

To connect to the database in pgAdmin:
1. Right-click "Servers" → "Create" → "Server"
2. **Name**: Order DB
3. **Host**: `order-postgres` (container name)
4. **Port**: `5432`
5. **Database**: `orderdb`
6. **Username**: `orderuser`
7. **Password**: `orderpass`

### Sample Data Included
- **3 Users**: John Doe, Jane Smith, Bob Johnson
- **5 Products**: iPhone 14, MacBook Pro, AirPods Pro, iPad Air, Apple Watch
- **2 Sample Orders**: With different statuses and items

## 🐛 Troubleshooting

### Common Issues

1. **Docker not running**
   ```bash
   # Start Docker Desktop and verify
   docker --version
   ```

2. **Port conflicts**
   ```bash
   # Check what's using the ports
   lsof -i :8090  # Order service
   lsof -i :5432  # PostgreSQL
   lsof -i :6379  # Redis
   ```

3. **Database connection issues**
   ```bash
   # Check container status
   docker ps
   # Check PostgreSQL logs
   docker logs order-postgres
   ```

4. **Application startup issues**
   ```bash
   # Check Java version
   java -version  # Should be 17+
   # Clean build
   cd order-service && ./mvnw clean compile
   ```

## 📊 Expected Test Results

When everything is working correctly, you should see:

1. **Infrastructure starts successfully** with all containers running
2. **Order service starts** and connects to PostgreSQL and Redis
3. **API tests pass** with proper responses for all endpoints
4. **Sample data is accessible** through the API
5. **New orders can be created** with proper validation
6. **Analytics return correct values** based on sample data

## 🎉 Success Criteria

The basic order processing system is working correctly when:
- ✅ All services start without errors
- ✅ API endpoints respond with expected data
- ✅ Order creation, updates, and cancellation work
- ✅ Stock management functions correctly
- ✅ Analytics provide meaningful insights
- ✅ Error handling works as expected

## 🔄 Next Steps After Testing

Once the basic system is validated:

1. **Add Kafka Integration** - Event-driven architecture for order events
2. **Implement Stream Processing** - Real-time analytics with Apache Flink
3. **Add Cassandra** - Time-series data storage for analytics
4. **Build Python Microservice** - Data enrichment and ML features
5. **Create React Frontend** - Admin dashboard and order management UI
6. **Add Comprehensive Testing** - Unit tests, integration tests, performance tests

---

**Ready to test?** Start with Step 1 above and let me know if you encounter any issues!
