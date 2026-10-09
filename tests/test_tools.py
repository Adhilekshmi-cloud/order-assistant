import pytest

from app import tools

SAMPLE = [
    {"order_id": "ORD-1", "order_date": "2026-08-03", "customer_name": "Asha Nair", "city": "Kochi",
     "product": "Headphones", "category": "Electronics", "quantity": 2, "unit_price_inr": 1000.0,
     "total_inr": 2000.0, "payment_method": "UPI", "status": "Delivered"},
    {"order_id": "ORD-2", "order_date": "2026-08-20", "customer_name": "Ravi Kumar", "city": "Pune",
     "product": "Laptop", "category": "Electronics", "quantity": 1, "unit_price_inr": 50000.0,
     "total_inr": 50000.0, "payment_method": "Card", "status": "Cancelled"},
    {"order_id": "ORD-3", "order_date": "2026-07-11", "customer_name": "Asha Nair", "city": "Kochi",
     "product": "Kurta", "category": "Clothing", "quantity": 3, "unit_price_inr": 500.0,
     "total_inr": 1500.0, "payment_method": "UPI", "status": "Delivered"},
]


@pytest.fixture(autouse=True)
def sample(monkeypatch):
    monkeypatch.setattr(tools, "ORDERS", SAMPLE)


def test_get_order_is_case_insensitive():
    assert tools.get_order("ord-2")["order"]["status"] == "Cancelled"


def test_get_order_missing_id():
    r = tools.get_order("ORD-9999")
    assert r["found"] is False and "ORD-9999" in r["message"]


def test_count_cancelled():
    assert tools.aggregate_orders("count", status="cancelled")["value"] == 1


def test_revenue_by_category_and_month():
    assert tools.aggregate_orders("revenue", category="Electronics", month="August")["value"] == 52000.0


def test_top_customer_by_revenue():
    r = tools.aggregate_orders("revenue", group_by="customer_name", top_n=1)
    assert r["results"] == [{"group": "Ravi Kumar", "value": 50000.0}]


def test_no_match_returns_message_not_error():
    r = tools.search_orders(city="Atlantis")
    assert r["total_matched"] == 0 and "message" in r


def test_run_tool_never_raises():
    assert "error" in tools.run_tool("aggregate_orders", {"metric": "median"})
    assert "error" in tools.run_tool("search_orders", {"colour": "red"})
    assert "error" in tools.run_tool("nope", {})


def test_real_csv_loads():
    rows = tools.load_orders()
    assert len(rows) == 60 and all(r["total_inr"] >= 0 for r in rows)