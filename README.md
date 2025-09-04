# MindCanvas Microservices

A full-stack microservices application for AI-powered content and image exploration.

## Architecture Overview

This project implements a complete microservices architecture with:

### **API Gateway** (Port 8000)
- Central entry point for all client requests
- Route requests to appropriate microservices
- JWT token validation and caching with Redis
- Request logging to Kafka for analytics
- Load balancing and service discovery

### **Microservices**

#### **Auth Service** (Port 8001, gRPC 50051)
- User authentication and authorization
- JWT token generation and validation
- gRPC server for inter-service communication
- User registration and login
- **Uses**: PostgreSQL, Redis (caching), Kafka (events)

#### **User Service** (Port 8002)
- User profile management
- User activity tracking
- Kafka consumer for user events
- Preferences and settings management
- **Uses**: PostgreSQL, Redis (caching), Kafka (events/consumer)

#### **Search Service** (Port 8003)
- Web search using Tavily MCP server
- Search history management
- Results caching with Redis
- **Uses**: PostgreSQL, Redis (caching), Kafka (events), Tavily MCP

#### **Image Service** (Port 8004)
- AI image generation using Flux MCP server
- Image history management
- Generated image storage and metadata
- **Uses**: PostgreSQL, Redis (caching), Kafka (events), Flux MCP

#### **Dashboard Service** (Port 8005)
- Data aggregation from other services
- Export functionality (CSV/PDF)
- Analytics and statistics
- gRPC client connections to other services
- **Uses**: PostgreSQL, Redis (caching), Kafka (events)

### **Infrastructure Components**

#### **Apache Kafka**
- **Where Used**: 
  - API Gateway: Request logging and analytics
  - Auth Service: User authentication events
  - User Service: Event consumer for user activities
  - Search Service: Search activity events
  - Image Service: Image generation events
  - Dashboard Service: Analytics events
- **Purpose**: Event streaming, microservices communication, analytics

#### **Redis**
- **Where Used**:
  - API Gateway: Token caching, rate limiting
  - All Services: Data caching, session management
- **Purpose**: High-performance caching, session storage

#### **gRPC**
- **Where Used**:
  - Auth Service: gRPC server for token validation
  - Dashboard Service: gRPC client for service communication
- **Purpose**: High-performance inter-service communication

#### **PostgreSQL**
- **Where Used**: All services for persistent data storage
- **Purpose**: Relational database for user data, search history, images, etc.

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+

### Quick Start with Docker

1. **Clone and navigate to the project:**
   ```bash
   cd mindcanvas-microservices
   ```

2. **Start all services:**
   ```bash
   docker-compose up --build
   ```

3. **Access the application:**
   - Frontend: http://localhost:3000
   - API Gateway: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Manual Setup

#### Backend Services

1. **Start Infrastructure Services:**
   ```bash
   # Start PostgreSQL, Redis, Kafka, Zookeeper
   docker-compose up -d postgres redis kafka zookeeper
   ```

2. **Start each microservice:**

   **Auth Service:**
   ```bash
   cd auth-service
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8001
   ```

   **User Service:**
   ```bash
   cd user-service
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8002
   ```

   **Search Service:**
   ```bash
   cd search-service
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8003
   ```

   **Image Service:**
   ```bash
   cd image-service
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8004
   ```

   **Dashboard Service:**
   ```bash
   cd dashboard-service
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8005
   ```

   **API Gateway:**
   ```bash
   cd api-gateway
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```

#### Frontend

```bash
cd frontend
npm install
npm start
```

## Service Endpoints

### API Gateway (http://localhost:8000)

#### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `GET /auth/me` - Get current user
- `POST /auth/refresh` - Refresh token

#### Search
- `POST /search/` - Perform web search
- `GET /search/history` - Get search history

#### Image Generation
- `POST /image/generate` - Generate AI image
- `GET /image/history` - Get image history

#### Dashboard
- `GET /dashboard/search` - Get search summary
- `GET /dashboard/images` - Get image summary
- `DELETE /dashboard/search/{id}` - Delete search
- `DELETE /dashboard/image/{id}` - Delete image
- `GET /dashboard/export/csv` - Export data as CSV
- `GET /dashboard/export/pdf` - Export data as PDF

## Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **PostgreSQL**: Primary database
- **Redis**: Caching and session storage
- **Apache Kafka**: Event streaming
- **gRPC**: Inter-service communication
- **SQLAlchemy**: Database ORM
- **Alembic**: Database migrations
- **JWT**: Authentication
- **pytest**: Testing framework

### Frontend
- **React 18**: Frontend framework
- **React Router**: Client-side routing
- **Axios**: HTTP client
- **Context API**: State management

### DevOps
- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration

### External APIs
- **Tavily MCP**: Web search functionality
- **Flux MCP**: AI image generation

## Features

### User Features
- User registration and authentication
- Web search with AI-powered results
- AI image generation with custom prompts
- Search and image history
- Data export (CSV/PDF)
- Dark/Light theme toggle
- Responsive design

### System Features
- Microservices architecture
- Event-driven communication
- Horizontal scalability
- Real-time data caching
- Comprehensive logging
- API rate limiting
- Service health monitoring

## Testing

### Backend Tests
```bash
# Run tests for each service
cd auth-service && pytest -v
cd user-service && pytest -v
cd search-service && pytest -v
cd image-service && pytest -v
cd dashboard-service && pytest -v
```

### Frontend Tests
```bash
cd frontend
npm test
```


## Monitoring and Logging

- **API Gateway**: Centralized request logging
- **Kafka Topics**: 
  - `api_requests`: API request analytics
  - `user_events`: User authentication and profile events
  - `search_events`: Search activity events
  - `image_events`: Image generation events
- **Redis**: Caching metrics and session data
- **Health Checks**: Available at `/health` endpoint for each service

## Security

- JWT-based authentication
- Password hashing with bcrypt
- CORS configuration
- Input validation and sanitization
- SQL injection protection via SQLAlchemy ORM

## Scalability

- Horizontal scaling of microservices
- Load balancing via API Gateway
- Database connection pooling
- Redis caching for improved performance
- Kafka for asynchronous processing
- Docker containers for easy deployment
