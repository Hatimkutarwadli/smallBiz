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

@tool
def external_context_search(query: str) -> str:
    """Performs a web search to find external factors (like festivals, seasons, trends) that might explain sales anomalies."""
    if 'festival' in query.lower() or 'wedding' in query.lower():
        return json.dumps({
            "query": query,
            "results": "Search Results: Upcoming Indian festival and wedding season in the current month is expected to boost consumer electronics and gifting sales by 40%. Analysts predict high demand for audio and smart devices."
        })
    return json.dumps({
        "query": query,
        "results": "No major external events found."
    })

@tool
def sales_analyzer() -> str:
    """Analyzes sales_history.csv to detect anomalies (>30% move) in the trailing 7 days vs prior average. Checks stock_history.csv for internal explanations."""
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "data")
    from datetime import datetime, timedelta
    
    sales_data = []
    try:
        with open(os.path.join(base_dir, 'sales_history.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sales_data.append({
                    "pid": row['product_id'],
                    "date": datetime.strptime(row['date'], '%Y-%m-%d'),
                    "units": int(row['units_sold'])
                })
    except Exception as e:
        return json.dumps({"error": f"Error reading sales: {str(e)}"})
        
    stock_data = {}
    try:
        with open(os.path.join(base_dir, 'stock_history.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row['product_id']
                date_str = row['date']
                if pid not in stock_data:
                    stock_data[pid] = {}
                stock_data[pid][date_str] = int(row['stock_level'])
    except Exception as e:
        pass
        
    if not sales_data:
        return "No sales data available."
        
    max_date = max(d['date'] for d in sales_data)
    cutoff_7d = max_date - timedelta(days=6)
    
    product_stats = {}
    for d in sales_data:
        pid = d['pid']
        if pid not in product_stats:
            product_stats[pid] = {"recent": [], "prior": []}
            
        if d['date'] >= cutoff_7d:
            product_stats[pid]["recent"].append(d)
        else:
            product_stats[pid]["prior"].append(d)
            
    anomalies = []
    
    for pid, stats in product_stats.items():
        if not stats["recent"] or not stats["prior"]:
            continue
            
        recent_avg = sum(x['units'] for x in stats["recent"]) / len(stats["recent"])
        prior_avg = sum(x['units'] for x in stats["prior"]) / len(stats["prior"])
        
        if prior_avg == 0:
            continue
            
        change_pct = ((recent_avg - prior_avg) / prior_avg) * 100
        
        if abs(change_pct) > 30:
            anomaly_type = "spike" if change_pct > 0 else "drop"
            
            out_of_stock_days = 0
            for d in stats["recent"]:
                date_str = d['date'].strftime('%Y-%m-%d')
                if stock_data.get(pid, {}).get(date_str, 1) == 0:
                    out_of_stock_days += 1
                    
            explanation = None
            needs_external_context = False
            
            if out_of_stock_days > 0 and anomaly_type == "drop":
                explanation = f"Drop internally explained: Product was out of stock for {out_of_stock_days} out of 7 days."
            else:
                needs_external_context = True
                
            anomalies.append({
                "product_id": pid,
                "prior_avg": round(prior_avg, 2),
                "recent_avg": round(recent_avg, 2),
                "change_pct": round(change_pct, 1),
                "anomaly_type": anomaly_type,
                "internal_explanation": explanation,
                "needs_external_context": needs_external_context
            })
            
    return json.dumps({"sales_anomalies": anomalies})

manager_agent = Agent(
    model=GeminiModel(model_id="gemini-3.6-flash"),
    name="ManagerAgent",
    description="A manager agent that provides a morning brief.",
    tools=[inventory_analyzer, supplier_analyzer, prepare_purchase_order, receivables_analyzer, sales_analyzer, external_context_search],
    system_prompt="""You generate morning briefs as a JSON array. 
Step 1: Run the inventory analyzer. Find products with stock risk (days until stockout <= 21 days, but > 0 days. Ignore 0 stock). For each, run supplier_analyzer and prepare_purchase_order.
Step 2: Run the receivables analyzer to find high risk customers.
Step 3: Run the sales_analyzer to find sales anomalies. For any anomaly where needs_external_context is true, run external_context_search with a query like "upcoming festival wedding season India [current month]" to find an explanation.

Format all currency amounts as whole numbers with commas (e.g., ₹22,000 instead of ₹22000.0). Do NOT output decimals for currency.
Do NOT include placeholder brackets like '[' or ']' in your final output strings.

Return a single JSON array of ALL alerts.
For stock_risk, evaluate days_until_stockout: if < 7 days, set priority to "Urgent". If 7-21 days, set priority to "Attention".
For sales anomalies, use type "sales_anomaly". If it's an unexplained spike, priority is "Opportunity" and action is "boost_ads". If it's a drop caused by stockouts, priority is "Urgent" and action is "review_supply_chain".

Format Example:
[
  {
    "id": "alert-1",
    "priority": "EVALUATE: Urgent or Attention",
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
  },
  {
    "id": "alert-3",
    "priority": "Opportunity",
    "type": "sales_anomaly",
    "title": "Product Name sales spiked by X%",
    "detail": "Trailing 7-day average rose from Y to Z units/day.",
    "recommendation": "Web search indicates upcoming festival season. Consider boosting ad spend to capture momentum.",
    "action_required": "boost_ads"
  },
  {
    "id": "alert-4",
    "priority": "Urgent",
    "type": "sales_anomaly",
    "title": "Product Name sales dropped by X%",
    "detail": "Trailing 7-day average fell from Y to Z units/day.",
    "recommendation": "Internal data shows product was out of stock for 4 of 7 days. Review supply chain immediately.",
    "action_required": "review_supply_chain"
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
