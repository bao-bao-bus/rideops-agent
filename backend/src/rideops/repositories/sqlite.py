import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from rideops.domain.models import IncidentTicket, InventoryItem, Order, RentalInventory, Vehicle


class BusinessToolError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class SQLiteBusinessRepository:
    """Persistent synthetic business data for the MVP accident loop."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    vehicle_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    billing_status TEXT NOT NULL DEFAULT 'active',
                    started_at TEXT NOT NULL,
                    pickup_location TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS vehicles (
                    vehicle_id TEXT PRIMARY KEY,
                    plate_number TEXT NOT NULL,
                    model TEXT NOT NULL,
                    status TEXT NOT NULL,
                    battery_percent INTEGER NOT NULL,
                    current_location TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS inventory (
                    item_id TEXT PRIMARY KEY,
                    item_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    warehouse TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS rental_inventory (
                    listing_id TEXT PRIMARY KEY,
                    city TEXT NOT NULL,
                    vehicle_type TEXT NOT NULL,
                    model TEXT NOT NULL,
                    available_units INTEGER NOT NULL,
                    daily_rate REAL NOT NULL,
                    monthly_rate REAL NOT NULL,
                    deposit REAL NOT NULL,
                    min_days INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS incident_tickets (
                    ticket_id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS idempotency_records (
                    idempotency_key TEXT PRIMARY KEY,
                    operation TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workflow_runs (
                    run_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS run_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reservations (
                    reservation_id TEXT PRIMARY KEY,
                    vehicle_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS long_rental_leads (
                    lead_id TEXT PRIMARY KEY,
                    listing_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    city TEXT NOT NULL,
                    duration_days INTEGER NOT NULL,
                    start_date TEXT,
                    status TEXT NOT NULL,
                    approval_reference TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE
                );
                """
            )
            if connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0:
                now = datetime.now(timezone.utc).isoformat()
                connection.execute("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)", ("ord_demo_001", "usr_demo_001", "veh_demo_001", "active", "active", now, "上海市静安区"))
                connection.execute("INSERT INTO vehicles VALUES (?, ?, ?, ?, ?, ?)", ("veh_demo_001", "沪A·MOCK01", "RideOps E-bike", "in_use", 72, "上海市静安区"))
                connection.execute("INSERT INTO vehicles VALUES (?, ?, ?, ?, ?, ?)", ("veh_demo_002", "沪A·MOCK02", "RideOps E-bike", "available", 88, "上海市静安区"))
                connection.execute("INSERT INTO inventory VALUES (?, ?, ?, ?)", ("inv_lock_001", "智能锁组件", 18, "上海一号仓"))
            if connection.execute("SELECT COUNT(*) FROM rental_inventory").fetchone()[0] == 0:
                connection.executemany(
                    "INSERT INTO rental_inventory VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        ("rent_sh_e1", "上海", "电单车", "RideOps E-bike E1", 8, 39.0, 699.0, 300.0, 3),
                        ("rent_sh_e2", "上海", "电单车", "RideOps E-bike E2", 3, 49.0, 899.0, 500.0, 7),
                        ("rent_hz_e1", "杭州", "电单车", "RideOps E-bike H1", 5, 35.0, 649.0, 300.0, 3),
                    ],
                )
            if connection.execute("SELECT 1 FROM vehicles WHERE vehicle_id = 'veh_demo_002'").fetchone() is None:
                connection.execute("INSERT INTO vehicles VALUES (?, ?, ?, ?, ?, ?)", ("veh_demo_002", "沪A·MOCK02", "RideOps E-bike", "available", 88, "上海市静安区"))

    @staticmethod
    def _order(row: sqlite3.Row | None) -> Order | None:
        if row is None:
            return None
        return Order(order_id=row["order_id"], user_id=row["user_id"], vehicle_id=row["vehicle_id"], status=row["status"], billing_status=row["billing_status"], started_at=row["started_at"], pickup_location=row["pickup_location"])

    @staticmethod
    def _vehicle(row: sqlite3.Row | None) -> Vehicle | None:
        if row is None:
            return None
        return Vehicle(vehicle_id=row["vehicle_id"], plate_number=row["plate_number"], model=row["model"], status=row["status"], battery_percent=row["battery_percent"], current_location=row["current_location"])

    @staticmethod
    def _ticket(row: sqlite3.Row | None) -> IncidentTicket | None:
        if row is None:
            return None
        return IncidentTicket(ticket_id=row["ticket_id"], order_id=row["order_id"], user_id=row["user_id"], category=row["category"], description=row["description"], status=row["status"], created_at=row["created_at"])

    def get_active_order(self, order_id: str) -> Order | None:
        with self._connect() as connection:
            return self._order(connection.execute("SELECT * FROM orders WHERE order_id = ? AND status = 'active'", (order_id,)).fetchone())

    def get_order(self, order_id: str) -> Order | None:
        with self._connect() as connection:
            return self._order(connection.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone())

    def get_vehicle(self, vehicle_id: str) -> Vehicle | None:
        with self._connect() as connection:
            return self._vehicle(connection.execute("SELECT * FROM vehicles WHERE vehicle_id = ?", (vehicle_id,)).fetchone())

    def get_available_vehicles(self, location: str, vehicle_type: str | None = None) -> list[Vehicle]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM vehicles WHERE status = 'available' AND current_location = ?", (location,)).fetchall()
            vehicles = [self._vehicle(row) for row in rows]
            if vehicle_type:
                vehicles = [vehicle for vehicle in vehicles if vehicle and vehicle_type.lower() in vehicle.model.lower()]
            return [vehicle for vehicle in vehicles if vehicle]

    def list_inventory(self) -> list[InventoryItem]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM inventory ORDER BY item_id").fetchall()
            return [InventoryItem(item_id=row["item_id"], item_name=row["item_name"], quantity=row["quantity"], warehouse=row["warehouse"]) for row in rows]

    def get_rental_inventory(self, city: str, vehicle_type: str | None = None) -> list[RentalInventory]:
        with self._connect() as connection:
            if vehicle_type:
                rows = connection.execute(
                    "SELECT * FROM rental_inventory WHERE city = ? AND vehicle_type = ? AND available_units > 0 ORDER BY monthly_rate",
                    (city, vehicle_type),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM rental_inventory WHERE city = ? AND available_units > 0 ORDER BY monthly_rate",
                    (city,),
                ).fetchall()
            return [
                RentalInventory(
                    listing_id=row["listing_id"],
                    city=row["city"],
                    vehicle_type=row["vehicle_type"],
                    model=row["model"],
                    available_units=row["available_units"],
                    daily_rate=row["daily_rate"],
                    monthly_rate=row["monthly_rate"],
                    deposit=row["deposit"],
                    min_days=row["min_days"],
                )
                for row in rows
            ]

    def get_rental_listing(self, listing_id: str) -> RentalInventory | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM rental_inventory WHERE listing_id = ?", (listing_id,)).fetchone()
            if row is None:
                return None
            return RentalInventory(
                listing_id=row["listing_id"],
                city=row["city"],
                vehicle_type=row["vehicle_type"],
                model=row["model"],
                available_units=row["available_units"],
                daily_rate=row["daily_rate"],
                monthly_rate=row["monthly_rate"],
                deposit=row["deposit"],
                min_days=row["min_days"],
            )

    def get_ticket(self, ticket_id: str) -> IncidentTicket | None:
        with self._connect() as connection:
            return self._ticket(connection.execute("SELECT * FROM incident_tickets WHERE ticket_id = ?", (ticket_id,)).fetchone())

    def suspend_order_billing(self, order_id: str, idempotency_key: str) -> dict:
        return self._idempotent_write(idempotency_key, "suspend_order_billing", lambda connection: self._suspend_order_billing(connection, order_id))

    def _suspend_order_billing(self, connection: sqlite3.Connection, order_id: str) -> dict:
        if connection.execute("SELECT 1 FROM orders WHERE order_id = ?", (order_id,)).fetchone() is None:
            raise BusinessToolError("NOT_FOUND", f"订单不存在: {order_id}")
        connection.execute("UPDATE orders SET billing_status = 'suspended' WHERE order_id = ?", (order_id,))
        return {"order_id": order_id, "billing_status": "suspended"}

    def mark_vehicle_unavailable(self, vehicle_id: str, idempotency_key: str) -> dict:
        return self._idempotent_write(idempotency_key, "mark_vehicle_unavailable", lambda connection: self._mark_vehicle_unavailable(connection, vehicle_id))

    def _mark_vehicle_unavailable(self, connection: sqlite3.Connection, vehicle_id: str) -> dict:
        if connection.execute("SELECT 1 FROM vehicles WHERE vehicle_id = ?", (vehicle_id,)).fetchone() is None:
            raise BusinessToolError("NOT_FOUND", f"车辆不存在: {vehicle_id}")
        connection.execute("UPDATE vehicles SET status = 'unavailable' WHERE vehicle_id = ?", (vehicle_id,))
        return {"vehicle_id": vehicle_id, "status": "unavailable"}

    def create_incident_ticket(self, order_id: str, user_id: str, description: str, idempotency_key: str) -> dict:
        return self._idempotent_write(idempotency_key, "create_incident_ticket", lambda connection: self._create_incident_ticket(connection, order_id, user_id, description, idempotency_key))

    def reserve_vehicle(self, vehicle_id: str, user_id: str, idempotency_key: str) -> dict:
        return self._idempotent_write(idempotency_key, "reserve_vehicle", lambda connection: self._reserve_vehicle(connection, vehicle_id, user_id, idempotency_key))

    def create_long_rental_lead(self, listing_id: str, user_id: str, duration_days: int, start_date: str | None, approval_reference: str, idempotency_key: str) -> dict:
        return self._idempotent_write(
            idempotency_key,
            "create_long_rental_lead",
            lambda connection: self._create_long_rental_lead(connection, listing_id, user_id, duration_days, start_date, approval_reference, idempotency_key),
        )

    def _create_long_rental_lead(self, connection: sqlite3.Connection, listing_id: str, user_id: str, duration_days: int, start_date: str | None, approval_reference: str, idempotency_key: str) -> dict:
        listing = connection.execute("SELECT city, available_units, min_days FROM rental_inventory WHERE listing_id = ?", (listing_id,)).fetchone()
        if listing is None:
            raise BusinessToolError("NOT_FOUND", f"长租方案不存在: {listing_id}")
        if listing["available_units"] < 1:
            raise BusinessToolError("CONFLICT", f"长租方案当前无库存: {listing_id}")
        if duration_days < listing["min_days"]:
            raise BusinessToolError("VALIDATION_ERROR", f"该方案最短租期为 {listing['min_days']} 天")
        lead_id = f"lead_{uuid.uuid4().hex[:12]}"
        created_at = datetime.now(timezone.utc).isoformat()
        connection.execute(
            "INSERT INTO long_rental_leads VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (lead_id, listing_id, user_id, listing["city"], duration_days, start_date, "pending_follow_up", approval_reference, created_at, idempotency_key),
        )
        return {
            "lead_id": lead_id,
            "listing_id": listing_id,
            "user_id": user_id,
            "city": listing["city"],
            "duration_days": duration_days,
            "start_date": start_date,
            "status": "pending_follow_up",
            "approval_reference": approval_reference,
            "created_at": created_at,
        }

    def _reserve_vehicle(self, connection: sqlite3.Connection, vehicle_id: str, user_id: str, idempotency_key: str) -> dict:
        row = connection.execute("SELECT status FROM vehicles WHERE vehicle_id = ?", (vehicle_id,)).fetchone()
        if row is None:
            raise BusinessToolError("NOT_FOUND", f"车辆不存在: {vehicle_id}")
        if row["status"] != "available":
            raise BusinessToolError("CONFLICT", f"车辆当前不可预约: {vehicle_id}")
        reservation_id = f"res_{uuid.uuid4().hex[:12]}"
        connection.execute("UPDATE vehicles SET status = 'in_use' WHERE vehicle_id = ?", (vehicle_id,))
        connection.execute("INSERT INTO reservations VALUES (?, ?, ?, ?, ?, ?)", (reservation_id, vehicle_id, user_id, "reserved", datetime.now(timezone.utc).isoformat(), idempotency_key))
        return {"reservation_id": reservation_id, "vehicle_id": vehicle_id, "status": "reserved"}

    def _create_incident_ticket(self, connection: sqlite3.Connection, order_id: str, user_id: str, description: str, idempotency_key: str) -> dict:
        if connection.execute("SELECT 1 FROM orders WHERE order_id = ?", (order_id,)).fetchone() is None:
            raise BusinessToolError("NOT_FOUND", f"订单不存在: {order_id}")
        ticket_id = f"ticket_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        connection.execute("INSERT INTO incident_tickets VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (ticket_id, order_id, user_id, "vehicle_incident", description, "open", now, idempotency_key))
        return {"ticket_id": ticket_id, "order_id": order_id, "status": "open"}

    def _idempotent_write(self, idempotency_key: str, operation: str, action) -> dict:
        if not idempotency_key:
            raise BusinessToolError("VALIDATION_ERROR", "必须提供 idempotency_key")
        with self._connect() as connection:
            existing = connection.execute("SELECT result_json FROM idempotency_records WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
            if existing:
                return json.loads(existing["result_json"])
            result = action(connection)
            connection.execute("INSERT INTO idempotency_records VALUES (?, ?, ?, ?)", (idempotency_key, operation, json.dumps(result), datetime.now(timezone.utc).isoformat()))
            return result

    def save_run(self, run_id: str, state: dict) -> None:
        now = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(state, ensure_ascii=False, default=str)
        with self._connect() as connection:
            connection.execute("INSERT INTO workflow_runs(run_id, state_json, created_at, updated_at) VALUES (?, ?, ?, ?) ON CONFLICT(run_id) DO UPDATE SET state_json = excluded.state_json, updated_at = excluded.updated_at", (run_id, payload, now, now))

    def get_run(self, run_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute("SELECT state_json FROM workflow_runs WHERE run_id = ?", (run_id,)).fetchone()
            return json.loads(row["state_json"]) if row else None

    def append_event(self, run_id: str, event_type: str, payload: dict | None = None) -> dict:
        event = {"event_id": None, "run_id": run_id, "event_type": event_type, "payload": payload or {}, "created_at": datetime.now(timezone.utc).isoformat()}
        with self._connect() as connection:
            cursor = connection.execute("INSERT INTO run_events(run_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?)", (run_id, event_type, json.dumps(event["payload"], ensure_ascii=False), event["created_at"]))
            event["event_id"] = cursor.lastrowid
        return event

    def list_events(self, run_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute("SELECT event_id, run_id, event_type, payload_json, created_at FROM run_events WHERE run_id = ? ORDER BY event_id", (run_id,)).fetchall()
        return [{"event_id": row["event_id"], "run_id": row["run_id"], "event_type": row["event_type"], "payload": json.loads(row["payload_json"]), "created_at": row["created_at"]} for row in rows]

    def snapshot(self) -> dict:
        with self._connect() as connection:
            orders = [self._order(row).model_dump(mode="json") for row in connection.execute("SELECT * FROM orders").fetchall()]
            vehicles = [self._vehicle(row).model_dump(mode="json") for row in connection.execute("SELECT * FROM vehicles").fetchall()]
            tickets = [self._ticket(row).model_dump(mode="json") for row in connection.execute("SELECT * FROM incident_tickets").fetchall()]
            inventory = [item.model_dump(mode="json") for item in self.list_inventory()]
            return {"orders": orders, "vehicles": vehicles, "inventory": inventory, "tickets": tickets}
