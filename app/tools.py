import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "orders.csv"
EXACT = ["status", "category", "city", "payment_method"]
PARTIAL = ["customer_name", "product"]
MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]


def _parse_date(s):
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Unrecognised date: {s!r}. Use YYYY-MM-DD.")


def load_orders(path=DATA_PATH):
    with open(path, newline="", encoding="utf-8-sig") as f:
        lines = f.read().splitlines()
    if not lines:
        raise RuntimeError(f"{path} is empty")
    delim = max(",;\t", key=lines[0].count)
    rows = []
    for r in csv.DictReader(lines, delimiter=delim):
        r = {k.strip().lower(): (v or "").strip() for k, v in r.items() if k}
        if "order_date" not in r:
            raise RuntimeError(f"orders.csv header not recognised: {lines[0]!r}")
        r["order_date"] = _parse_date(r["order_date"]).isoformat()
        r["quantity"] = int(float(r["quantity"]))
        r["unit_price_inr"] = float(r["unit_price_inr"])
        r["total_inr"] = float(r["total_inr"])
        rows.append(r)
    return rows


ORDERS = load_orders()


def distinct_values():
    return {c: sorted({o[c] for o in ORDERS}) for c in EXACT}


def _month(v):
    s = str(v).strip().lower()
    if s.isdigit() and 1 <= int(s) <= 12:
        return int(s)
    for i, name in enumerate(MONTHS, 1):
        if len(s) >= 3 and name.startswith(s):
            return i
    raise ValueError(f"Invalid month: {v!r}")


def _filter(f):
    f = {k: v for k, v in f.items() if v not in (None, "")}
    allowed = set(EXACT + PARTIAL + ["date_from", "date_to", "month"])
    unknown = set(f) - allowed
    if unknown:
        raise ValueError(f"Unknown filter(s): {sorted(unknown)}")
    rows = ORDERS
    for k in EXACT:
        if k in f:
            rows = [o for o in rows if o[k].lower() == str(f[k]).strip().lower()]
    for k in PARTIAL:
        if k in f:
            rows = [o for o in rows if str(f[k]).strip().lower() in o[k].lower()]
    if "date_from" in f:
        d = _parse_date(str(f["date_from"])).isoformat()
        rows = [o for o in rows if o["order_date"] >= d]
    if "date_to" in f:
        d = _parse_date(str(f["date_to"])).isoformat()
        rows = [o for o in rows if o["order_date"] <= d]
    if "month" in f:
        m = _month(f["month"])
        rows = [o for o in rows if int(o["order_date"][5:7]) == m]
    return rows


def get_order(order_id):
    oid = str(order_id).strip().upper()
    for o in ORDERS:
        if o["order_id"].upper() == oid:
            return {"found": True, "order": o}
    return {"found": False, "message": f"No order with ID {oid} exists."}


def search_orders(limit=10, **filters):
    rows = _filter(filters)
    limit = max(1, min(int(limit or 10), 25))
    out = {"total_matched": len(rows), "orders": rows[:limit]}
    if not rows:
        out["message"] = "No orders matched these filters."
    return out


def _metric(metric, rows):
    if metric == "count":
        return len(rows)
    if metric == "revenue":
        return round(sum(o["total_inr"] for o in rows), 2)
    if metric == "quantity":
        return sum(o["quantity"] for o in rows)
    if metric == "avg_order_value":
        return round(sum(o["total_inr"] for o in rows) / len(rows), 2) if rows else 0
    raise ValueError("metric must be count, revenue, quantity or avg_order_value")


def aggregate_orders(metric, group_by=None, top_n=10, **filters):
    rows = _filter(filters)
    if not rows:
        return {"matched_orders": 0, "value": 0, "message": "No orders matched these filters."}
    if not group_by:
        return {"matched_orders": len(rows), "metric": metric, "value": _metric(metric, rows)}
    valid = EXACT + ["customer_name", "product", "month"]
    if group_by not in valid:
        raise ValueError(f"group_by must be one of {valid}")
    groups = defaultdict(list)
    for o in rows:
        groups[o["order_date"][:7] if group_by == "month" else o[group_by]].append(o)
    results = sorted(({"group": g, "value": _metric(metric, r)} for g, r in groups.items()),
                     key=lambda x: x["value"], reverse=True)
    return {"matched_orders": len(rows), "metric": metric, "group_by": group_by,
            "results": results[:max(1, min(int(top_n or 10), 25))]}


TOOLS = {"get_order": get_order, "search_orders": search_orders,
         "aggregate_orders": aggregate_orders}


def run_tool(name, args):
    """Never raises: failures come back as {"error": ...} so the model can explain them."""
    if name not in TOOLS:
        return {"error": f"Unknown tool: {name}"}
    try:
        return TOOLS[name](**(args or {}))
    except (ValueError, TypeError) as e:
        return {"error": str(e)}
    except Exception:
        return {"error": "Tool failed unexpectedly."}


_F = {
    "status": {"type": "string"}, "category": {"type": "string"},
    "city": {"type": "string"}, "payment_method": {"type": "string"},
    "customer_name": {"type": "string", "description": "Partial match"},
    "product": {"type": "string", "description": "Partial match"},
    "date_from": {"type": "string", "description": "YYYY-MM-DD inclusive"},
    "date_to": {"type": "string", "description": "YYYY-MM-DD inclusive"},
    "month": {"type": "string", "description": "Month number 1-12 or name"},
}


def _fn(name, desc, props, required):
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required}}}


TOOL_SCHEMAS = [
    _fn("get_order", "Look up one order by its ID (e.g. ORD-1025). Use for any question about a specific order.",
        {"order_id": {"type": "string"}}, ["order_id"]),
    _fn("search_orders", "List orders matching filters. Use when the user wants to see the orders themselves.",
        {**_F, "limit": {"type": "integer", "description": "Max rows, default 10, max 25"}}, []),
    _fn("aggregate_orders",
        "Compute count, revenue (sum of total_inr), quantity or avg_order_value over filtered orders, "
        "optionally grouped and ranked. Use for every how many / total / average / which-is-highest question.",
        {**_F,
         "metric": {"type": "string", "enum": ["count", "revenue", "quantity", "avg_order_value"]},
         "group_by": {"type": "string", "enum": EXACT + ["customer_name", "product", "month"]},
         "top_n": {"type": "integer"}}, ["metric"]),
]