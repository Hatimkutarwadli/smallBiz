from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strands import Agent
from strands.tools import tool
from strands.models.gemini import GeminiModel
import uvicorn
import os
import csv
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@tool
def inventory_analyzer() -> str:
    """Analyzes inventory risk using products.csv and sales_history.csv. Also provides available supplier options for reordering."""
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "data")
    
    # Calculate velocity from sales history
    sales = {}
    try:
        with open(os.path.join(base_dir, 'sales_history.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row['product_id']
                units = int(row['units_sold'])
                sales[pid] = sales.get(pid, 0) + units
    except Exception as e:
        print("Error reading sales:", e)
        
    DAYS = 60 # Assume the history is 60 days
    
    results = []
    try:
        with open(os.path.join(base_dir, 'products.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row['id']
                name = row['name']
                stock = int(row['stock'])
                
                total_sold = sales.get(pid, 0)
                # If we have sales data, use it; else fallback to the CSV's static velocity
                velocity = total_sold / DAYS if total_sold > 0 else float(row.get('sales_velocity', 0))
                days_left = stock / velocity if velocity > 0 else 999
                
                results.append({
                    "product_id": pid,
                    "name": name,
                    "current_stock": stock,
                    "sales_velocity_per_day": round(velocity, 2),
                    "days_until_stockout": round(days_left, 1)
                })
    except Exception as e:
        print("Error reading products:", e)
        
    # Read suppliers to provide context to the LLM for recommendations
    suppliers = []
    try:
        with open(os.path.join(base_dir, 'suppliers.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                suppliers.append(row)
    except Exception as e:
        print("Error reading suppliers:", e)

    return json.dumps({
        "inventory_risk": results,
        "available_suppliers": suppliers
    })

@tool
def receivables_analyzer() -> str:
    """Analyzes receivables risk by ranking customers based on amount overdue and days overdue."""
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "data")
    
    results = []
    try:
        with open(os.path.join(base_dir, 'receivables.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                amount = float(row['amount_overdue'])
                days = int(row['days_overdue'])
                risk_score = amount * days
                
                results.append({
                    "id": row['id'],
                    "customer_name": row['customer_name'],
                    "amount_overdue": amount,
                    "days_overdue": days,
                    "notes": row['notes'],
                    "risk_score": risk_score
                })
    except Exception as e:
        print("Error reading receivables:", e)
        
    # Sort descending by risk score
    results.sort(key=lambda x: x['risk_score'], reverse=True)
    
    return json.dumps({
        "receivables_risk": results
    })

manager_agent = Agent(
    model=GeminiModel(model_id="gemini-3.6-flash"),
    name="ManagerAgent",
    description="A manager agent that provides a morning brief.",
    tools=[inventory_analyzer, receivables_analyzer],
    system_prompt="""You generate morning briefs as a JSON array. Run the inventory analyzer and receivables analyzer tools to get stock risk, supplier data, and receivables risk. 
Find products with stock risk (days until stockout < 10 days).
Use the available supplier data to write a highly detailed recommendation (e.g., recommend a specific supplier based on delivery days, reliability, and price).

Also find customers with high receivables risk (e.g. high risk score or > 7 days overdue) and create alerts for them.

Return a single JSON array of BOTH types of alerts in exactly this format:
[
  {
    "id": "alert-1",
    "priority": "Urgent",
    "type": "stock_risk",
    "title": "Product Name may stock out in X days",
    "detail": "Current stock: Y units. Sales velocity is Z/day.",
    "recommendation": "Reorder 20 units from Sharma Mobile Distributors (₹20,800/unit, 2-day delivery, 4.5★ reliability) — chosen over the cheaper TechWorld Wholesale (₹20,500) because its 5-day delivery would cause an actual stockout.",
    "action_required": "approve_purchase_order"
  },
  {
    "id": "alert-2",
    "priority": "Attention",
    "type": "receivables_risk",
    "title": "Customer Name is X days overdue",
    "detail": "Amount: ₹Y. Customer has a history of Z.",
    "recommendation": "Send a formal reminder email immediately, followed by a phone call to the owner tomorrow morning.",
    "action_required": "send_reminder_email"
  }
]
Output ONLY raw JSON (no markdown formatting or backticks)."""
)

@app.get("/morning-brief")
def get_morning_brief():
    try:
        response = manager_agent("Generate the morning brief JSON.")
        
        # Strands Agent returns an AgentResult object. We need to convert it to a string.
        response_text = str(response)
        
        # Clean up any potential markdown formatting (like ```json ... ```)
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        return json.loads(response_text.strip())
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
