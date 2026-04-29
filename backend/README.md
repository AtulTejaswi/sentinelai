# SentinelAI — Backend Services

This directory contains the FastAPI-based backend core for SentinelAI. It manages the continuous trust scoring mechanisms, behavioral signal processing, the SQLite events store, and the standard REST endpoints used by the dashboard.

## To Run the Backend Locally

1. **Activate the Environment**
   Ensure you have configured your `.venv` and install the required components:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Variables**
   Create/Update an `.env` file containing (at minimum) parameters needed for generating JWT and dispatching mock OTPs:
   ```bash
   JWT_SECRET="YOUR_SUPER_SECRET_KEY"
   GMAIL_USER="your-email@gmail.com"
   GMAIL_APP_PASSWORD="your-app-password"
   ```

3. **Start the ASGI Server**
   Start up `uvicorn` holding the FastAPI application:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

4. **Testing Endpoints**
   - The endpoints are fully documented automatically via Swagger. Go to: `http://localhost:8000/docs`.
   - Postman/Curl usage: You can register (`POST /api/register`), then obtain an access token through `POST /api/login`. Inject the bearer token into Authorization headers on your subsequent requests to securely access dashboard routes.
