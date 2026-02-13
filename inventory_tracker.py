#!/usr/bin/env python3
"""Inventory tracking software for warehouses and service vehicles."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Iterable

DB_PATH = Path("inventory.db")


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN ('warehouse', 'vehicle'))
        );

        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY,
            sku TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            min_qty INTEGER NOT NULL DEFAULT 0 CHECK(min_qty >= 0)
        );

        CREATE TABLE IF NOT EXISTS stock (
            location_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            qty INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(location_id, item_id),
            FOREIGN KEY(location_id) REFERENCES locations(id) ON DELETE CASCADE,
            FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE,
            CHECK(qty >= 0)
        );

        CREATE TABLE IF NOT EXISTS moves (
            id INTEGER PRIMARY KEY,
            item_id INTEGER NOT NULL,
            from_location_id INTEGER,
            to_location_id INTEGER,
            qty INTEGER NOT NULL CHECK(qty > 0),
            note TEXT,
            moved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(item_id) REFERENCES items(id),
            FOREIGN KEY(from_location_id) REFERENCES locations(id),
            FOREIGN KEY(to_location_id) REFERENCES locations(id)
        );
        """
    )
    conn.commit()


def add_location(conn: sqlite3.Connection, name: str, kind: str) -> None:
    conn.execute("INSERT INTO locations(name, kind) VALUES(?, ?)", (name, kind))
    conn.commit()


def add_item(conn: sqlite3.Connection, sku: str, name: str, min_qty: int = 0) -> None:
    conn.execute("INSERT INTO items(sku, name, min_qty) VALUES(?, ?, ?)", (sku, name, min_qty))
    conn.commit()


def _get_location_id(conn: sqlite3.Connection, name: str) -> int:
    row = conn.execute("SELECT id FROM locations WHERE name = ?", (name,)).fetchone()
    if not row:
        raise ValueError(f"Unknown location: {name}")
    return int(row["id"])


def _get_item_id(conn: sqlite3.Connection, sku: str) -> int:
    row = conn.execute("SELECT id FROM items WHERE sku = ?", (sku,)).fetchone()
    if not row:
        raise ValueError(f"Unknown SKU: {sku}")
    return int(row["id"])


def _change_stock(conn: sqlite3.Connection, location_id: int, item_id: int, delta: int) -> None:
    row = conn.execute(
        "SELECT qty FROM stock WHERE location_id = ? AND item_id = ?",
        (location_id, item_id),
    ).fetchone()
    current = int(row["qty"]) if row else 0
    new_qty = current + delta
    if new_qty < 0:
        raise ValueError("Insufficient stock for operation")

    conn.execute(
        """
        INSERT INTO stock(location_id, item_id, qty)
        VALUES(?, ?, ?)
        ON CONFLICT(location_id, item_id) DO UPDATE SET qty=excluded.qty
        """,
        (location_id, item_id, new_qty),
    )


def receive_stock(conn: sqlite3.Connection, sku: str, to_location: str, qty: int, note: str | None = None) -> None:
    item_id = _get_item_id(conn, sku)
    to_id = _get_location_id(conn, to_location)
    with conn:
        _change_stock(conn, to_id, item_id, qty)
        conn.execute(
            "INSERT INTO moves(item_id, to_location_id, qty, note) VALUES(?, ?, ?, ?)",
            (item_id, to_id, qty, note),
        )


def transfer_stock(conn: sqlite3.Connection, sku: str, from_location: str, to_location: str, qty: int, note: str | None = None) -> None:
    item_id = _get_item_id(conn, sku)
    from_id = _get_location_id(conn, from_location)
    to_id = _get_location_id(conn, to_location)

    if from_id == to_id:
        raise ValueError("Source and destination locations must be different")

    with conn:
        _change_stock(conn, from_id, item_id, -qty)
        _change_stock(conn, to_id, item_id, qty)
        conn.execute(
            "INSERT INTO moves(item_id, from_location_id, to_location_id, qty, note) VALUES(?, ?, ?, ?, ?)",
            (item_id, from_id, to_id, qty, note),
        )


def consume_stock(conn: sqlite3.Connection, sku: str, from_location: str, qty: int, note: str | None = None) -> None:
    item_id = _get_item_id(conn, sku)
    from_id = _get_location_id(conn, from_location)
    with conn:
        _change_stock(conn, from_id, item_id, -qty)
        conn.execute(
            "INSERT INTO moves(item_id, from_location_id, qty, note) VALUES(?, ?, ?, ?)",
            (item_id, from_id, qty, note),
        )


def stock_report(conn: sqlite3.Connection) -> Iterable[sqlite3.Row]:
    return conn.execute(
        """
        SELECT i.sku, i.name AS item_name, i.min_qty, l.name AS location_name, l.kind, COALESCE(s.qty, 0) AS qty
        FROM items i
        CROSS JOIN locations l
        LEFT JOIN stock s ON s.item_id = i.id AND s.location_id = l.id
        ORDER BY i.sku, l.kind, l.name
        """
    ).fetchall()


def low_stock_report(conn: sqlite3.Connection) -> Iterable[sqlite3.Row]:
    return conn.execute(
        """
        SELECT i.sku, i.name, i.min_qty, COALESCE(SUM(s.qty), 0) AS total_qty
        FROM items i
        LEFT JOIN stock s ON s.item_id = i.id
        GROUP BY i.id
        HAVING total_qty < i.min_qty
        ORDER BY i.sku
        """
    ).fetchall()


def _print_rows(rows: Iterable[sqlite3.Row]) -> None:
    rows = list(rows)
    if not rows:
        print("No records.")
        return
    headers = rows[0].keys()
    widths = {h: len(h) for h in headers}
    for r in rows:
        for h in headers:
            widths[h] = max(widths[h], len(str(r[h])))

    print(" | ".join(f"{h:{widths[h]}}" for h in headers))
    print("-+-".join("-" * widths[h] for h in headers))
    for r in rows:
        print(" | ".join(f"{str(r[h]):{widths[h]}}" for h in headers))


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than 0")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Track warehouse and service vehicle inventory")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="Path to SQLite database")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize database")

    p = sub.add_parser("add-location", help="Add location")
    p.add_argument("name")
    p.add_argument("kind", choices=["warehouse", "vehicle"])

    p = sub.add_parser("add-item", help="Add item")
    p.add_argument("sku")
    p.add_argument("name")
    p.add_argument("--min-qty", type=int, default=0)

    p = sub.add_parser("receive", help="Receive stock into a location")
    p.add_argument("sku")
    p.add_argument("location")
    p.add_argument("qty", type=positive_int)
    p.add_argument("--note")

    p = sub.add_parser("transfer", help="Transfer stock between locations")
    p.add_argument("sku")
    p.add_argument("from_location")
    p.add_argument("to_location")
    p.add_argument("qty", type=positive_int)
    p.add_argument("--note")

    p = sub.add_parser("consume", help="Use stock from a location")
    p.add_argument("sku")
    p.add_argument("location")
    p.add_argument("qty", type=positive_int)
    p.add_argument("--note")

    sub.add_parser("report", help="Show stock by location")
    sub.add_parser("low-stock", help="Show low-stock items")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    conn = connect(args.db)

    if args.command == "init":
        init_db(conn)
        print(f"Database initialized at {args.db}")
    elif args.command == "add-location":
        add_location(conn, args.name, args.kind)
        print("Location added")
    elif args.command == "add-item":
        add_item(conn, args.sku, args.name, args.min_qty)
        print("Item added")
    elif args.command == "receive":
        receive_stock(conn, args.sku, args.location, args.qty, args.note)
        print("Stock received")
    elif args.command == "transfer":
        transfer_stock(conn, args.sku, args.from_location, args.to_location, args.qty, args.note)
        print("Stock transferred")
    elif args.command == "consume":
        consume_stock(conn, args.sku, args.location, args.qty, args.note)
        print("Stock consumed")
    elif args.command == "report":
        _print_rows(stock_report(conn))
    elif args.command == "low-stock":
        _print_rows(low_stock_report(conn))


if __name__ == "__main__":
    main()
