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
    """Analyzes inventory risk using products.csv and sales_history.csv."""
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "data")
    from datetime import datetime, timedelta
    
    # Calculate velocity from sales history
    sales_data = []
    try:
        with open(os.path.join(base_dir, 'sales_history.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row['product_id']
                date_obj = datetime.strptime(row['date'], '%Y-%m-%d')
                units = int(row['units_sold'])
                sales_data.append((pid, date_obj, units))
    except Exception as e:
        print("Error reading sales:", e)
        
    sales = {}
    velocity_days = 10
    if sales_data:
        max_date = max(d[1] for d in sales_data)
        cutoff_date = max_date - timedelta(days=10)
        recent_sales = [d for d in sales_data if d[1] > cutoff_date]
        
        min_recent_date = min(d[1] for d in recent_sales) if recent_sales else max_date
        actual_span = (max_date - min_recent_date).days + 1
        velocity_days = min(10, max(1, actual_span))
        
        for pid, date, units in recent_sales:
            sales[pid] = sales.get(pid, 0) + units
            
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
                velocity = total_sold / velocity_days if total_sold > 0 else float(row.get('sales_velocity', 0))
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
        
    return json.dumps({
        "inventory_risk": results
    })

@tool
def supplier_analyzer(product_id: str, days_until_stockout: float) -> str:
    """Analyzes available suppliers for a product and recommends the best option considering delivery days vs stockout window."""
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "data")
    
    suppliers = []
    try:
        with open(os.path.join(base_dir, 'suppliers.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                suppliers.append({
                    "id": row['id'],
                    "name": row['name'],
                    "price": float(row['price']),
                    "delivery_days": int(row['delivery_days']),
                    "reliability": float(row['reliability'])
                })
    except Exception as e:
        print("Error reading suppliers:", e)
        return json.dumps({"error": str(e)})
        
    if not suppliers:
        return "No suppliers found."
        
    valid_suppliers = [s for s in suppliers if s['delivery_days'] < days_until_stockout]
    
    if not valid_suppliers:
        best_supplier = min(suppliers, key=lambda s: s['delivery_days'])
        reason = f"All suppliers exceed the {days_until_stockout} days window. Recommended the fastest option: {best_supplier['name']} (₹{int(best_supplier['price']):,}/unit, {best_supplier['delivery_days']}-day delivery, {best_supplier['reliability']}★ reliability)."
    else:
        best_supplier = min(valid_suppliers, key=lambda s: s['price'])
        reason = f"Reorder from {best_supplier['name']} (₹{int(best_supplier['price']):,}/unit, {best_supplier['delivery_days']}-day delivery, {best_supplier['reliability']}★ reliability) — chosen because it is fast enough to prevent stockout ({best_supplier['delivery_days']} days < {days_until_stockout}), and offers the best price among valid options."
        
    return json.dumps({
        "recommended_supplier": best_supplier,
        "reason": reason,
        "all_suppliers_considered": suppliers
    })

@tool
def prepare_purchase_order(supplier_id: str, product_id: str, quantity: int) -> str:
    """Prepares a draft purchase order for a given supplier and product."""
    return json.dumps({
        "status": "draft_prepared",
        "po_number": f"PO-{supplier_id}-{product_id}-001",
        "supplier_id": supplier_id,
        "product_id": product_id,
        "quantity": quantity,
        "message": f"Draft PO prepared for {quantity} units."
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
    tools=[inventory_analyzer, supplier_analyzer, prepare_purchase_order, receivables_analyzer],
    system_prompt="""You generate morning briefs as a JSON array. 
Step 1: Run the inventory analyzer. Find products with stock risk (days until stockout <= 21 days, but > 0 days. Ignore 0 stock).
Step 2: For each product with stock risk, run the supplier_analyzer to get the best supplier.
Step 3: Run the prepare_purchase_order tool to draft a PO with a suggested quantity (e.g., 20).
Step 4: Run the receivables analyzer to find high risk customers (e.g. high risk score or > 7 days overdue).

Format all currency amounts as whole numbers with commas (e.g., ₹22,000 instead of ₹22000.0). Do NOT output decimals for currency.
Do NOT include placeholder brackets like '[' or ']' in your final output strings.

Return a single JSON array of BOTH types of alerts.
For stock_risk, set priority to "Urgent" (<7 days) or "Attention" (7-21 days). Include the suggested quantity field.

Format:
[
  {
    "id": "alert-1",
    "priority": "Urgent",
    "type": "stock_risk",
    "title": "Product Name may stock out in X days",
    "detail": "Current stock: Y units. Sales velocity is Z/day.",
    "recommendation": "Use supplier_analyzer reason here.",
    "action_required": "approve_purchase_order",
    "suggested_quantity": 20
  },
  {
    "id": "alert-2",
    "priority": "Attention",
    "type": "receivables_risk",
    "title": "Customer Name is X days overdue",
    "detail": "Amount: ₹22,000. Customer has a history of chronic late payments.",
    "recommendation": "Write a detailed recommendation here.",
    "action_required": "send_reminder_email"
  }
]
Output ONLY raw JSON."""
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
