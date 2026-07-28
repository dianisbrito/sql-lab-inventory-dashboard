"""
Synthetic data generator for the biological reference material inventory demo.

Generates a fully synthetic dataset (no real institutional data) mimicking
the structure of a diagnostic laboratory's biological control inventory, and
loads it into a local SQLite database (inventory.db). The database is the
backend the Streamlit dashboard and SQL example queries run against.

Run with: python data/seed_data.py
"""

import sqlite3
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

DB_PATH = Path(__file__).parent / "inventory.db"

# ------------------------------------------------------------------
# Reference lists (public, generic taxonomic examples — not real
# institutional records)
# ------------------------------------------------------------------
CATEGORIES = [
    "Fungi & Protists",
    "Bacteria",
    "Viruses & Viroids",
    "Phytoplasmas",
    "Synthetic Controls (gBlocks)",
    "Insects",
    "Nematodes",
    "Plant Tissue",
]

TAXA_BY_CATEGORY = {
    "Fungi & Protists": ["Phakopsora pachyrhizi", "Fusarium oxysporum", "Botrytis cinerea", "Phytophthora infestans"],
    "Bacteria": ["Ralstonia solanacearum", "Xanthomonas campestris", "Erwinia amylovora", "Pseudomonas syringae"],
    "Viruses & Viroids": ["Potato spindle tuber viroid", "Banana mild mosaic virus", "Citrus tristeza virus", "Tomato yellow leaf curl virus"],
    "Phytoplasmas": ["Candidatus Phytoplasma asteris", "Candidatus Phytoplasma solani"],
    "Synthetic Controls (gBlocks)": ["Synthetic positive control A", "Synthetic positive control B", "Synthetic positive control C"],
    "Insects": ["Ceratitis capitata", "Anastrepha fraterculus", "Bactrocera dorsalis"],
    "Nematodes": ["Meloidogyne incognita", "Globodera pallida"],
    "Plant Tissue": ["Reference leaf tissue - citrus", "Reference leaf tissue - potato", "Reference leaf tissue - tomato"],
}

STORAGE_MEDIA = ["Sterile water", "Glycerol 20%", "Silica gel", "Lyophilized", "TE buffer"]
LOCATIONS = [f"Freezer {f} - Box {b}" for f in ["A", "B", "C"] for b in range(1, 6)]
ANALYSTS = ["J. Martinez", "L. Fernandez", "A. Rossi", "M. Duarte", "S. Kim", "P. Alvarez"]
MOVEMENT_TYPES = ["IN", "OUT"]
MOVEMENT_REASONS_OUT = ["Used in validation run", "Sent to proficiency test", "Used in training", "Quality control check"]
MOVEMENT_REASONS_IN = ["New batch received", "Replenished from supplier", "Returned unused"]


def random_date(start_year=2019, end_year=2025):
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def build_items(n_items=180):
    items = []
    for i in range(1, n_items + 1):
        category = random.choice(CATEGORIES)
        taxon = random.choice(TAXA_BY_CATEGORY[category])
        collection_date = random_date(2022, 2026)
        reactivation_date = collection_date + timedelta(days=random.choice([180, 365, 540, 730, 900, 1095]))
        stock = random.choice([0, 1, 1, 2, 3, 4, 5, 6, 8, 10])
        items.append({
            "item_id": i,
            "collection_code": f"REF-{category[:2].upper()}{i:04d}",
            "category": category,
            "taxon": taxon,
            "storage_medium": random.choice(STORAGE_MEDIA),
            "location": random.choice(LOCATIONS),
            "responsible_analyst": random.choice(ANALYSTS),
            "conservation_date": collection_date.isoformat(),
            "reactivation_date": reactivation_date.isoformat(),
            "stock": stock,
        })
    return items


def build_movements(items, n_movements=400):
    movements = []
    for i in range(1, n_movements + 1):
        item = random.choice(items)
        mtype = random.choice(MOVEMENT_TYPES)
        reason = random.choice(MOVEMENT_REASONS_IN if mtype == "IN" else MOVEMENT_REASONS_OUT)
        mdate = random_date(2023, 2025)
        movements.append({
            "movement_id": i,
            "item_id": item["item_id"],
            "movement_date": mdate.isoformat(),
            "movement_type": mtype,
            "quantity": random.randint(1, 3),
            "reason": reason,
            "user": random.choice(ANALYSTS),
        })
    movements.sort(key=lambda m: m["movement_date"])
    return movements


def main():
    items = build_items()
    movements = build_movements(items)

    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE items (
            item_id INTEGER PRIMARY KEY,
            collection_code TEXT NOT NULL,
            category TEXT NOT NULL,
            taxon TEXT NOT NULL,
            storage_medium TEXT,
            location TEXT,
            responsible_analyst TEXT,
            conservation_date TEXT,
            reactivation_date TEXT,
            stock INTEGER NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE movements (
            movement_id INTEGER PRIMARY KEY,
            item_id INTEGER NOT NULL,
            movement_date TEXT NOT NULL,
            movement_type TEXT NOT NULL CHECK (movement_type IN ('IN','OUT')),
            quantity INTEGER NOT NULL,
            reason TEXT,
            user TEXT,
            FOREIGN KEY (item_id) REFERENCES items(item_id)
        )
    """)

    cur.executemany(
        """INSERT INTO items VALUES (:item_id, :collection_code, :category, :taxon,
           :storage_medium, :location, :responsible_analyst, :conservation_date,
           :reactivation_date, :stock)""",
        items,
    )
    cur.executemany(
        """INSERT INTO movements VALUES (:movement_id, :item_id, :movement_date,
           :movement_type, :quantity, :reason, :user)""",
        movements,
    )

    conn.commit()
    conn.close()
    print(f"Created {DB_PATH} with {len(items)} items and {len(movements)} movements.")


if __name__ == "__main__":
    main()
