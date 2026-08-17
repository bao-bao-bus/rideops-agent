import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from rideops.domain.models import IncidentTicket, InventoryItem, Order, Vehicle


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
                """
            )
            if connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0:
                now = datetime.now(timezone.utc).isoformat()
                connection.execute("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)", ("ord_demo_001", "usr_demo_001", "veh_demo_001", "active", "active", now, "上海市静安区"))
                connection.execute("INSERT INTO vehicles VALUES (?, ?, ?, ?, ?, ?)", ("veh_demo_001", "沪A·MOCK01", "RideOps E-bike", "in_use", 72, "上海市静安区"))
                connection.execute("INSERT INTO inventory VALUES (?, ?, ?, ?)", ("inv_lock_001", "智能锁组件", 18, "上海一号仓"))

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

    def list_inventory(self) -> list[InventoryItem]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM inventory ORDER BY item_id").fetchall()
            return [InventoryItem(item_id=row["item_id"], item_name=row["item_name"], quantity=row["quantity"], warehouse=row["warehouse"]) for row in rows]

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

    def snapshot(self) -> dict:
        with self._connect() as connection:
            orders = [self._order(row).model_dump(mode="json") for row in connection.execute("SELECT * FROM orders").fetchall()]
            vehicles = [self._vehicle(row).model_dump(mode="json") for row in connection.execute("SELECT * FROM vehicles").fetchall()]
            tickets = [self._ticket(row).model_dump(mode="json") for row in connection.execute("SELECT * FROM incident_tickets").fetchall()]
            inventory = [item.model_dump(mode="json") for item in self.list_inventory()]
            return {"orders": orders, "vehicles": vehicles, "inventory": inventory, "tickets": tickets}
