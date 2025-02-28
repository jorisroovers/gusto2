# Gusto2 2-Tier Web Application

A simple web application with a VueJS frontend and Python FastAPI backend, running on Docker Compose.

## Project Structure

```
gusto2-app/
├── backend/
│   ├── main.py             # FastAPI application
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile          # Backend Docker configuration
├── frontend/
│   ├── public/             # Static assets
│   ├── src/                # Vue source code
│   ├── package.json        # Node.js dependencies
│   ├── vue.config.js       # Vue configuration
│   ├── nginx.conf          # Nginx configuration for API proxying
│   └── Dockerfile          # Frontend Docker configuration
└── docker-compose.yml      # Docker Compose configuration
```

## Running the Application

### Development Mode (with Hot Reloading)

For development with hot reloading (code changes are immediately applied):

1. Make sure you have Docker and Docker Compose installed on your system.

2. Clone this repository:
   ```
   git clone <repository-url>
   cd gusto2-app
   ```

3. Start the application in development mode:
   ```
   docker-compose up
   ```

4. Make changes to the code:
   - Frontend (Vue.js): Changes in the `frontend/src` directory will be automatically applied
   - Backend (FastAPI): Changes in the `backend` directory will be automatically applied

5. Access the application:
   - Frontend: http://localhost:8080
   - Backend API: http://localhost:8000/api/hello

### Production Mode

For production deployment:

1. Modify the docker-compose.yml file to remove the development-specific settings:
   ```
   # Remove these lines from the frontend service
   volumes:
     - ./frontend:/app
     - /app/node_modules
   environment:
     - NODE_ENV=development
   command: npm run serve
   
   # And change the build configuration
   build: ./frontend
   ports:
     - "8080:80"
   ```

2. Start the application:
   ```
   docker-compose up --build
   ```

## Accessing from a Different Host

The application is configured to work when accessed from any host, not just localhost. When deployed:

1. Replace `localhost` with your server's IP address or domain name:
   - Frontend: http://your-server-ip:8080
   - Backend API: http://your-server-ip:8000/api/hello

2. The frontend will automatically proxy API requests to the backend, so you only need to access the frontend URL.

## API Endpoints

- `GET /api/hello`: Returns a "Hello from Gusto2!" message

## Development

### Backend

The backend is built with FastAPI, a modern Python web framework.

To run the backend locally without Docker:
```
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend

The frontend is built with Vue.js 3.

To run the frontend locally without Docker:
```
cd frontend
npm install
npm run serve
```
