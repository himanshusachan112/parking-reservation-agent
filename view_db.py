"""Quick script to view all database tables and data."""
from src.database.sql_store import SQLStore

store = SQLStore()

print("=" * 60)
print("  SQL DATABASE TABLES & DATA")
print("=" * 60)

print("\n--- TABLE: working_hours ---")
hours = store.get_working_hours()
for h in hours:
    day = h["day"]
    ot = h["open_time"]
    ct = h["close_time"]
    op = h["is_open"]
    print(f"  {day:12s} | {ot} - {ct} | Open: {op}")

print("\n--- TABLE: parking_prices ---")
prices = store.get_prices()
for p in prices:
    st = p["space_type"]
    dt = p["duration_type"]
    pr = p["price"]
    cu = p["currency"]
    print(f"  {st:10s} | {dt:8s} | ${pr:.2f} {cu}")

print("\n--- TABLE: parking_availability ---")
avail = store.get_availability()
for a in avail:
    fl = a["floor"]
    st = a["space_type"]
    av = a["available_spaces"]
    to = a["total_spaces"]
    print(f"  Floor {fl} | {st:10s} | {av}/{to} available")

print("\n--- TOTALS ---")
totals = store.get_total_availability()
for t, v in totals.items():
    print(f"  {t:10s} | {v['available']}/{v['total']} available")

print("\n" + "=" * 60)
print("  VECTOR DATABASE (Pinecone)")
print("=" * 60)

from src.database.vector_store import VectorStore
vs = VectorStore()
count = vs.get_collection_count()
print(f"\n  Collection: parking_info")
print(f"  Total documents: {count}")
print(f"\n  Sample documents:")
results = vs.similarity_search("parking information", k=3)
for i, doc in enumerate(results, 1):
    preview = doc.page_content[:120].replace("\n", " ")
    print(f"\n  [{i}] {preview}...")
