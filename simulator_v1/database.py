
import sqlite3

DB_NAME = "medical_supply.db"


def initialize_database():

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    # 1. Warehouse inventory table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicine_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_name TEXT UNIQUE,
            quantity INTEGER,
            minimum_stock INTEGER
        )
    """)

    # 2. Hospital requirements table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hospital_needs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_name TEXT UNIQUE,
            required_quantity INTEGER
        )
    """)

    # 3. Insert sample warehouse stock
    cursor.executemany("""
        INSERT OR IGNORE INTO medicine_stock
        (medicine_name, quantity, minimum_stock)
        VALUES (?, ?, ?)
    """, [
        ("Paracetamol", 500, 100),
        ("Amoxicillin", 300, 80),
        ("Ibuprofen", 200, 50),
        ("Insulin", 150, 40)
    ])

    # 4. Insert hospital requirements
    cursor.executemany("""
        INSERT OR IGNORE INTO hospital_needs
        (medicine_name, required_quantity)
        VALUES (?, ?)
    """, [
        ("Paracetamol", 100),
        ("Amoxicillin", 80),
        ("Ibuprofen", 60),
        ("Insulin", 50)
    ])
    
    # 5. Hospital orders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_name TEXT,
            requested_quantity INTEGER,
            status TEXT DEFAULT 'Pending',
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()


# 5. Retrieve information from the database
def get_data(table_name):

    allowed_tables = [
        "medicine_stock",
        "hospital_needs",
        "vehicles"
    ]

    if table_name not in allowed_tables:
        raise ValueError("Invalid table name")

    connection = sqlite3.connect(DB_NAME)
    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    cursor.execute(f"SELECT * FROM {table_name}")

    data = [dict(row) for row in cursor.fetchall()]

    connection.close()

    return data

# Create a new hospital order
def create_order(medicine_name, quantity):

    if quantity <= 0:
        return False, "Quantity must be greater than zero."

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO orders
        (medicine_name, requested_quantity)
        VALUES (?, ?)
    """, (medicine_name, quantity))

    connection.commit()
    connection.close()

    return True, "Order submitted successfully!"


# Retrieve all hospital orders
def get_orders():

    connection = sqlite3.connect(DB_NAME)
    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()
    cursor.execute("SELECT * FROM orders ORDER BY id DESC")

    orders = [dict(row) for row in cursor.fetchall()]

    connection.close()

    return orders

# Approve a hospital order
def approve_order(order_id):

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    # Find the requested order
    cursor.execute("""
        SELECT medicine_name, requested_quantity, status
        FROM orders
        WHERE id = ?
    """, (order_id,))

    order = cursor.fetchone()

    if order is None:
        connection.close()
        return False, "Order not found."

    medicine_name = order[0]
    requested_quantity = order[1]
    status = order[2]

    if status != "Pending":
        connection.close()
        return False, "This order has already been processed."

    # Check warehouse stock
    cursor.execute("""
        SELECT quantity
        FROM medicine_stock
        WHERE medicine_name = ?
    """, (medicine_name,))

    stock = cursor.fetchone()

    if stock is None:
        connection.close()
        return False, "Medicine not found in warehouse."

    if stock[0] < requested_quantity:
        connection.close()
        return False, "Insufficient warehouse stock."

    # Deduct medicine from warehouse inventory
    cursor.execute("""
        UPDATE medicine_stock
        SET quantity = quantity - ?
        WHERE medicine_name = ?
    """, (requested_quantity, medicine_name))

    # Update order status
    cursor.execute("""
        UPDATE orders
        SET status = 'Approved'
        WHERE id = ?
    """, (order_id,))
    
    # 6. Transportation vehicles table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_name TEXT UNIQUE,
            capacity_units INTEGER,
            available INTEGER,
            cost_per_km REAL,
            average_speed_kmh REAL
        )
    """)

    # 7. Insert sample transportation vehicles
    cursor.executemany("""
        INSERT OR IGNORE INTO vehicles
        (vehicle_name, capacity_units, available,
         cost_per_km, average_speed_kmh)
        VALUES (?, ?, ?, ?, ?)
    """, [
        ("Delivery Van", 200, 1, 500, 40),
        ("Refrigerated Truck", 1000, 1, 800, 35)
    ])

    connection.commit()
    connection.close()

    return True, "Order approved. Warehouse stock updated."

def save_simulation_order(
    medicine_name,
    quantity,
    distance,
    vehicle,
    delivery_time,
    transportation_cost,
    status,
    reason
):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulation_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_name TEXT,
            quantity INTEGER,
            distance REAL,
            vehicle TEXT,
            delivery_time REAL,
            transportation_cost REAL,
            status TEXT,
            reason TEXT,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        INSERT INTO simulation_orders (
            medicine_name,
            quantity,
            distance,
            vehicle,
            delivery_time,
            transportation_cost,
            status,
            reason
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        medicine_name,
        quantity,
        distance,
        vehicle,
        delivery_time,
        transportation_cost,
        status,
        reason
    ))

    connection.commit()
    connection.close()


def get_simulation_orders():
    connection = sqlite3.connect(DB_NAME)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulation_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_name TEXT,
            quantity INTEGER,
            distance REAL,
            vehicle TEXT,
            delivery_time REAL,
            transportation_cost REAL,
            status TEXT,
            reason TEXT,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        SELECT * FROM simulation_orders
        ORDER BY id DESC
    """)

    orders = [dict(row) for row in cursor.fetchall()]

    connection.close()
    return orders

def deduct_medicine_stock(medicine_name, quantity):

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE medicine_stock
        SET quantity = quantity - ?
        WHERE medicine_name = ?
        AND quantity >= ?
    """, (quantity, medicine_name, quantity))

    connection.commit()

    success = cursor.rowcount > 0

    connection.close()

    return success

