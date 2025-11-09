# Database setup and operations for the Trading Platform
# This file handles all the database stuff - creating tables, storing users, resources, positions, transactions
# I used SQLite because it's simple and doesn't need a separate server
# This matches the same pattern as keep-in-touch-chat
import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

class Database:
    def __init__(self, db_path: str = None):
        # Use environment variable or default path
        # This lets us configure where the database file goes
        self.db_path = db_path or os.getenv('DATABASE_URL', './trading.db')
        self.init_database()  # Create tables when we start up
    
    def get_connection(self):
        """Get a database connection"""
        # Connect to the SQLite database file
        conn = sqlite3.connect(self.db_path)
        # This makes it so we can access columns by name instead of just numbers
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database tables"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
        except Exception as e:
            print(f"Error connecting to database: {e}")
            raise
        
        try:
            # Users table - stores user account information
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    balance REAL DEFAULT 10000.0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Resources table - stores tradeable assets
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS resources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    current_price REAL NOT NULL,
                    volatility REAL DEFAULT 0.02,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Positions table - stores what users currently own
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    resource_id INTEGER NOT NULL,
                    quantity REAL NOT NULL,
                    average_price REAL NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (resource_id) REFERENCES resources (id),
                    UNIQUE(user_id, resource_id)
                )
            ''')
            
            # Transactions table - stores all buy/sell history
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    resource_id INTEGER NOT NULL,
                    transaction_type TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    total_value REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (resource_id) REFERENCES resources (id)
                )
            ''')
            
            conn.commit()
            print("Database tables initialized successfully")
            
            # Create default resources if they don't exist
            self.create_default_resources()
            
            # Create test user if it doesn't exist
            self.create_test_user()
            
        except Exception as e:
            print(f"Error initializing database: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def create_default_resources(self):
        """Create default resources if they don't exist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            default_resources = [
                {"symbol": "ENG", "name": "Energy Units", "price": 100.0, "volatility": 0.03},
                {"symbol": "DTA", "name": "Digital Tokens", "price": 50.0, "volatility": 0.05},
                {"symbol": "CRY", "name": "Crypto Crystals", "price": 200.0, "volatility": 0.04},
                {"symbol": "BIO", "name": "Bio Materials", "price": 75.0, "volatility": 0.02},
                {"symbol": "MET", "name": "Rare Metals", "price": 150.0, "volatility": 0.025},
            ]
            
            for resource_data in default_resources:
                cursor.execute('SELECT id FROM resources WHERE symbol = ?', (resource_data["symbol"],))
                existing = cursor.fetchone()
                
                if not existing:
                    cursor.execute(
                        'INSERT INTO resources (symbol, name, current_price, volatility, last_updated) VALUES (?, ?, ?, ?, ?)',
                        (resource_data["symbol"], resource_data["name"], resource_data["price"], 
                         resource_data["volatility"], datetime.utcnow())
                    )
                    print(f"  Added: {resource_data['name']} ({resource_data['symbol']})")
            
            conn.commit()
        except Exception as e:
            print(f"Error creating default resources: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def create_test_user(self):
        """Create test user if it doesn't exist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            from auth import get_password_hash
            
            cursor.execute('SELECT id FROM users WHERE username = ?', ('testuser',))
            existing = cursor.fetchone()
            
            if not existing:
                password_hash = get_password_hash("password123")
                cursor.execute(
                    'INSERT INTO users (username, email, hashed_password, balance) VALUES (?, ?, ?, ?)',
                    ('testuser', 'test@example.com', password_hash, 10000.0)
                )
                conn.commit()
                print("Added test user: testuser / password123")
        except Exception as e:
            print(f"Error creating test user: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    # User operations
    def create_user(self, username: str, email: str, password_hash: str) -> int:
        """Create a new user and return user ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'INSERT INTO users (username, email, hashed_password, balance) VALUES (?, ?, ?, ?)',
                (username, email, password_hash, 10000.0)
            )
            user_id = cursor.lastrowid
            conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            raise ValueError("User with this username or email already exists")
        finally:
            conn.close()
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'SELECT id, username, email, hashed_password, balance, created_at FROM users WHERE username = ?',
                (username,)
            )
            user = cursor.fetchone()
            return dict(user) if user else None
        finally:
            conn.close()
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'SELECT id, username, email, balance, created_at FROM users WHERE id = ?',
                (user_id,)
            )
            user = cursor.fetchone()
            return dict(user) if user else None
        finally:
            conn.close()
    
    def update_user_balance(self, user_id: int, new_balance: float):
        """Update user's balance"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'UPDATE users SET balance = ? WHERE id = ?',
                (new_balance, user_id)
            )
            conn.commit()
        finally:
            conn.close()
    
    # Resource operations
    def get_all_resources(self) -> List[Dict[str, Any]]:
        """Get all resources"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT id, symbol, name, current_price, volatility, last_updated FROM resources')
            resources = cursor.fetchall()
            return [dict(resource) for resource in resources]
        finally:
            conn.close()
    
    def get_resource_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get resource by symbol"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'SELECT id, symbol, name, current_price, volatility, last_updated FROM resources WHERE symbol = ?',
                (symbol,)
            )
            resource = cursor.fetchone()
            return dict(resource) if resource else None
        finally:
            conn.close()
    
    def update_resource_price(self, resource_id: int, new_price: float):
        """Update resource price"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'UPDATE resources SET current_price = ?, last_updated = ? WHERE id = ?',
                (new_price, datetime.utcnow(), resource_id)
            )
            conn.commit()
        finally:
            conn.close()
    
    # Position operations
    def get_user_positions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all positions for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT 
                    p.id,
                    p.user_id,
                    p.resource_id,
                    p.quantity,
                    p.average_price,
                    p.created_at,
                    r.symbol,
                    r.name,
                    r.current_price
                FROM positions p
                INNER JOIN resources r ON p.resource_id = r.id
                WHERE p.user_id = ?
            ''', (user_id,))
            positions = cursor.fetchall()
            return [dict(pos) for pos in positions]
        finally:
            conn.close()
    
    def get_position(self, user_id: int, resource_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific position"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT 
                    p.id,
                    p.user_id,
                    p.resource_id,
                    p.quantity,
                    p.average_price,
                    p.created_at,
                    r.symbol,
                    r.name,
                    r.current_price
                FROM positions p
                INNER JOIN resources r ON p.resource_id = r.id
                WHERE p.user_id = ? AND p.resource_id = ?
            ''', (user_id, resource_id))
            position = cursor.fetchone()
            return dict(position) if position else None
        finally:
            conn.close()
    
    def create_or_update_position(self, user_id: int, resource_id: int, quantity: float, average_price: float):
        """Create or update a position"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if position exists
            cursor.execute(
                'SELECT id, quantity FROM positions WHERE user_id = ? AND resource_id = ?',
                (user_id, resource_id)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Update existing position
                new_quantity = existing['quantity'] + quantity
                if new_quantity <= 0:
                    # Delete position if quantity is 0 or negative
                    cursor.execute(
                        'DELETE FROM positions WHERE user_id = ? AND resource_id = ?',
                        (user_id, resource_id)
                    )
                else:
                    # Recalculate average price
                    total_value = (existing['quantity'] * existing['average_price']) + (quantity * average_price)
                    new_avg_price = total_value / new_quantity
                    cursor.execute(
                        'UPDATE positions SET quantity = ?, average_price = ? WHERE user_id = ? AND resource_id = ?',
                        (new_quantity, new_avg_price, user_id, resource_id)
                    )
            else:
                # Create new position
                cursor.execute(
                    'INSERT INTO positions (user_id, resource_id, quantity, average_price) VALUES (?, ?, ?, ?)',
                    (user_id, resource_id, quantity, average_price)
                )
            
            conn.commit()
        finally:
            conn.close()
    
    # Transaction operations
    def create_transaction(self, user_id: int, resource_id: int, transaction_type: str, 
                          quantity: float, price: float, total_value: float) -> int:
        """Create a transaction and return transaction ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'INSERT INTO transactions (user_id, resource_id, transaction_type, quantity, price, total_value) VALUES (?, ?, ?, ?, ?, ?)',
                (user_id, resource_id, transaction_type, quantity, price, total_value)
            )
            transaction_id = cursor.lastrowid
            conn.commit()
            return transaction_id
        finally:
            conn.close()
    
    def get_user_transactions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all transactions for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT 
                    t.id,
                    t.user_id,
                    t.resource_id,
                    t.transaction_type,
                    t.quantity,
                    t.price,
                    t.total_value,
                    t.timestamp,
                    r.symbol,
                    r.name
                FROM transactions t
                INNER JOIN resources r ON t.resource_id = r.id
                WHERE t.user_id = ?
                ORDER BY t.timestamp DESC
            ''', (user_id,))
            transactions = cursor.fetchall()
            return [dict(txn) for txn in transactions]
        finally:
            conn.close()


# Global database instance - initializes automatically when imported (like keep-in-touch-chat)
db = Database()
