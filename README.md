# Warehouse + Service Vehicle Inventory Tracker

A practical command-line inventory tool for:
- Warehouses
- Service vehicles (vans/trucks)

Data is stored in SQLite (`inventory.db` by default), so it runs on a normal laptop with no server setup.

## Make it usable day-to-day

### 1) Use guided mode (recommended for non-technical users)

```bash
python3 inventory_tracker.py interactive
```

This opens a numbered menu so your team can add items, move stock, and run reports without remembering commands.

### 2) Keep one shared database file

Use one file path consistently (for example on a shared drive):

```bash
python3 inventory_tracker.py --db /path/to/shared/inventory.db interactive
```

### 3) Create a simple desktop shortcut

- **Windows**: create a `.bat` file that runs `python inventory_tracker.py --db C:\inventory\inventory.db interactive`
- **Mac/Linux**: create a shell alias/script that runs the same command

## Core features

- Register warehouse/vehicle locations
- Register inventory items with minimum levels
- Receive stock
- Transfer stock between locations
- Consume stock for jobs
- Full stock report and low-stock report
- Movement history audit log

## Quick start (CLI mode)

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
python3 inventory_tracker.py --db inventory.db history --limit 10
```

## Command reference

- `init`
- `interactive`
- `list-locations`
- `list-items`
- `history [--limit N]`
- `add-location <name> <warehouse|vehicle>`
- `add-item <sku> <name> [--min-qty N]`
- `receive <sku> <location> <qty> [--note TEXT]`
- `transfer <sku> <from_location> <to_location> <qty> [--note TEXT]`
- `consume <sku> <location> <qty> [--note TEXT]`
- `report`
- `low-stock`

## Notes

- Quantities are integer units.
- Stock cannot go negative.
- Most commands auto-create DB tables if needed.
