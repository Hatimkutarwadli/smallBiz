# Morning Brief AI Dashboard

This project contains the **Morning Brief** intelligent dashboard, powered by an AI Agent that monitors your inventory stock levels, supplier options, and outstanding receivables.

The application consists of a **FastAPI** backend that runs the AI tools, and a **Next.js** frontend for the UI.

## Prerequisites
- Node.js (v18+)
- Python (v3.11+)
- A Gemini API Key

## Setup Instructions

### 1. Backend Setup
The backend runs the AI agent which processes the data from the CSV files and returns actionable alert JSONs.

1. Open a terminal and navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Install the required Python packages:
   ```bash
   pip install fastapi uvicorn strands-agents
   ```
3. Set your Gemini API key as an environment variable:
   - **Windows (PowerShell):**
     ```powershell
     $env:GEMINI_API_KEY="your-api-key-here"
     ```
   - **Mac/Linux:**
     ```bash
     export GEMINI_API_KEY="your-api-key-here"
     ```
4. Start the backend server:
   ```bash
   python main.py
   ```
   *The server will start on `http://127.0.0.1:8000`.*

### 2. Frontend Setup
The frontend is a responsive, card-based React dashboard built with Next.js 16 and Tailwind CSS.

1. Open a **new** terminal and navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install the Node dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
4. Open your browser and go to `http://localhost:3000`.

## Architecture & Data
- **Backend (`backend/main.py`)**: Defines custom tools (`inventory_analyzer`, `supplier_analyzer`, `prepare_purchase_order`, `receivables_analyzer`) that are passed to a `strands-agents` ManagerAgent.
- **Frontend (`frontend/src/app/page.tsx`)**: Fetches data from the `http://127.0.0.1:8000/morning-brief` endpoint. If the backend is unavailable or hits a demand error, it gracefully falls back to a mock local JSON file.
- **Data Store (`frontend/data/*.csv`)**: The backend agent analyzes dummy data stored in the frontend's `/data` directory:
  - `products.csv`
  - `sales_history.csv`
  - `suppliers.csv`
  - `receivables.csv`
