import sys
sys.path.insert(0, ".")
from app.scrapers.selectors import SELECTOR_CONFIG, FieldSelectors

print(f"Total fields: {len(SELECTOR_CONFIG)}")
for k, v in SELECTOR_CONFIG.items():
    assert isinstance(v, FieldSelectors), f"{k} is not FieldSelectors"
    print(f"  {k}: {len(v.selectors)} selectors")

expected = ["title", "current_price", "list_price", "rating", "review_count", "main_image_url", "availability_text", "brand", "seller_info"]
for field in expected:
    assert field in SELECTOR_CONFIG, f"Missing field: {field}"

print("All checks passed!")
