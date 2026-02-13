# Warehouse + Service Vehicle Inventory Tracker

A lightweight command-line application to track inventory across:
- One or more warehouses
- One or more service vehicles

It stores data in SQLite (`inventory.db` by default), so no external database is required.

## Features

- Register warehouse and vehicle locations
- Register inventory items with a minimum quantity threshold
- Receive stock into any location
- Transfer stock between warehouse and vehicles
- Consume stock from a location (e.g., used during a service job)
- Run full stock and low-stock reports

## Quick Start

```bash
python3 inventory_tracker.py --db inventory.db init
python3 inventory_tracker.py --db inventory.db add-location MainWarehouse warehouse
python3 inventory_tracker.py --db inventory.db add-location Van-12 vehicle
python3 inventory_tracker.py --db inventory.db add-item FILTER01 "Oil Filter" --min-qty 20
python3 inventory_tracker.py --db inventory.db receive FILTER01 MainWarehouse 100
python3 inventory_tracker.py --db inventory.db transfer FILTER01 MainWarehouse Van-12 10 --note "Weekly restock"
python3 inventory_tracker.py --db inventory.db consume FILTER01 Van-12 2 --note "Work order #854"
python3 inventory_tracker.py --db inventory.db report
python3 inventory_tracker.py --db inventory.db low-stock
```

## Command Reference

- `init`
- `add-location <name> <warehouse|vehicle>`
- `add-item <sku> <name> [--min-qty N]`
- `receive <sku> <location> <qty> [--note TEXT]`
- `transfer <sku> <from_location> <to_location> <qty> [--note TEXT]`
- `consume <sku> <location> <qty> [--note TEXT]`
- `report`
- `low-stock`

## Notes

- Quantities are integer units.
- Transfers and consumption prevent negative stock.
- All movement operations are recorded in a `moves` log table for auditing.
