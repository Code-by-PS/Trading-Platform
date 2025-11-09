# FastAPI application for the trading demo.
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
import uvicorn
import logging
import random
import os

# Local modules
from database import db
from auth import hash_password, verify_password, generate_token, get_current_user
from fastapi import Depends

# Prepare paths and the FastAPI app instance.
BASE_DIR = Path(__file__).parent.parent
FRONTEND_DIR = BASE_DIR / 'frontend'

app = FastAPI(title="Resource Exchange Simulator", version="1.0.0")
CORS(app)  # Allow the web client to call the API

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initial startup logs.
print("Trading Platform server starting...")
print("Database initialized automatically")

@app.post("/api/register")
def register(request_data: dict):
    """Create a user account."""
    try:
        username = request_data.get('username', '').strip()
        email = request_data.get('email', '').strip()
        password = request_data.get('password', '')
        
        if not username or not email or not password:
            raise HTTPException(status_code=400, detail="Username, email, and password are required")
        
        # Check if user already exists
        existing_user = db.get_user_by_username(username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already registered")
        
        # Hash password before saving
        password_hash = hash_password(password)
        
        # Create new user
        user_id = db.create_user(username, email, password_hash)
        
        # Generate JWT token
        token = generate_token(user_id, username)
        
        # Get user data
        user_data = db.get_user_by_id(user_id)
        
        return {
            'message': 'User created successfully',
            'token': token,
            'user': {
                'id': user_data['id'],
                'username': user_data['username'],
                'email': user_data['email'],
                'balance': user_data['balance']
            }
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/login")
def login(request_data: dict):
    """Sign a user in."""
    try:
        username = request_data.get('username', '').strip()
        password = request_data.get('password', '')
        
        # Find user by username
        user = db.get_user_by_username(username)
        if not user:
            raise HTTPException(status_code=401, detail="Incorrect username or password")
        
        # Verify password
        if not verify_password(password, user['hashed_password']):
            raise HTTPException(status_code=401, detail="Incorrect username or password")
        
        # Generate JWT token
        token = generate_token(user['id'], username)
        
        return {
            'message': 'Login successful',
            'access_token': token,
            'token_type': 'bearer',
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'balance': user['balance']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/me")
def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Return details for the signed-in user."""
    try:
        user_id = current_user['userId']
        
        # Get user details from database
        user_data = db.get_user_by_id(user_id)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            'user': {
                'id': user_data['id'],
                'username': user_data['username'],
                'email': user_data['email'],
                'balance': user_data['balance'],
                'created_at': user_data['created_at']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/resources")
def get_resources():
    """Return every available resource."""
    try:
        resources = db.get_all_resources()
        return resources
    except Exception as e:
        logger.error(f"Get resources error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/update-prices")
def update_resource_prices():
    """Adjust each resource price by a small random amount."""
    try:
        resources = db.get_all_resources()
        updated_count = 0
        
        for resource in resources:
            # Random price change between -5% and +5%
            change_percent = random.uniform(-0.05, 0.05)
            new_price = resource['current_price'] * (1 + change_percent)
            
            # Update the price in database
            db.update_resource_price(resource['id'], new_price)
            updated_count += 1
        
        logger.info(f"Updated prices for {updated_count} resources")
        return {"message": f"Updated prices for {updated_count} resources", "updated_count": updated_count}
    except Exception as e:
        logger.error(f"Update prices error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/trade")
def execute_trade(trade_data: dict, current_user: dict = Depends(get_current_user)):
    """Handle buy and sell requests."""
    try:
        user_id = current_user['userId']
        
        trade_type = trade_data.get('trade_type', '').lower()
        resource_symbol = trade_data.get('resource_symbol', '')
        quantity = float(trade_data.get('quantity', 0))
        
        if trade_type not in ['buy', 'sell']:
            raise HTTPException(status_code=400, detail="trade_type must be 'buy' or 'sell'")
        
        if not resource_symbol or quantity <= 0:
            raise HTTPException(status_code=400, detail="resource_symbol and quantity are required")
        
        # Get user and resource
        user_data = db.get_user_by_id(user_id)
        resource = db.get_resource_by_symbol(resource_symbol)
        
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")
        
        price = resource['current_price']
        total_value = quantity * price
        
        if trade_type == 'buy':
            # Check if user has enough balance
            if user_data['balance'] < total_value:
                raise HTTPException(status_code=400, detail="Insufficient balance")
            
            # Update user balance
            new_balance = user_data['balance'] - total_value
            db.update_user_balance(user_id, new_balance)
            
            # Create or update position
            db.create_or_update_position(user_id, resource['id'], quantity, price)
            
        else:  # sell
            # Check if user has enough quantity
            position = db.get_position(user_id, resource['id'])
            if not position or position['quantity'] < quantity:
                raise HTTPException(status_code=400, detail="Insufficient quantity to sell")
            
            # Update user balance
            new_balance = user_data['balance'] + total_value
            db.update_user_balance(user_id, new_balance)
            
            # Update position (negative quantity for sell)
            db.create_or_update_position(user_id, resource['id'], -quantity, price)
        
        # Create transaction record
        transaction_id = db.create_transaction(user_id, resource['id'], trade_type, quantity, price, total_value)
        
        # Get updated user
        updated_user = db.get_user_by_id(user_id)
        
        logger.info(f"Trade executed - User ID: {user_id}, Type: {trade_type}, Symbol: {resource_symbol}, Quantity: {quantity}")
        
        return {
            "message": "Trade executed successfully",
            "transaction_id": transaction_id,
            "balance": updated_user['balance']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trade error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/positions")
def get_positions(current_user: dict = Depends(get_current_user)):
    """Return the user's holdings."""
    try:
        user_id = current_user['userId']
        
        positions = db.get_user_positions(user_id)
        result = []
        
        # Calculate current value and profit/loss for each position
        for position in positions:
            current_value = position['quantity'] * position['current_price']
            cost_basis = position['quantity'] * position['average_price']
            profit_loss = current_value - cost_basis
            
            result.append({
                "id": position['id'],
                "resource": {
                    "id": position['resource_id'],
                    "symbol": position['symbol'],
                    "name": position['name'],
                    "current_price": position['current_price']
                },
                "quantity": position['quantity'],
                "average_price": position['average_price'],
                "current_value": current_value,
                "profit_loss": profit_loss,
                "created_at": position['created_at']
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Get positions error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/transactions")
def get_transactions(current_user: dict = Depends(get_current_user)):
    """Return the user's trade history."""
    try:
        user_id = current_user['userId']
        
        transactions = db.get_user_transactions(user_id)
        
        logger.info(f"User {user_id} has {len(transactions)} transactions")
        
        return transactions
        
    except Exception as e:
        logger.error(f"Get transactions error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Serve static files such as CSS and JavaScript.
@app.get("/style.css")
def serve_css():
    """Serve the CSS file."""
    css_file = FRONTEND_DIR / "style.css"
    if css_file.exists():
        return FileResponse(css_file, media_type="text/css")
    raise HTTPException(status_code=404, detail="CSS file not found")

@app.get("/script.js")
def serve_js():
    """Serve the JavaScript file."""
    js_file = FRONTEND_DIR / "script.js"
    if js_file.exists():
        return FileResponse(js_file, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="JavaScript file not found")

# Serve main HTML file for root
@app.get("/")
def serve_index():
    """Serve the main HTML file."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    raise HTTPException(status_code=404, detail="Frontend not found")

@app.get("/api")
def read_root():
    """Give a brief API description."""
    return {"message": "Resource Exchange Simulator API", "docs": "/docs"}

if __name__ == "__main__":
    # Get port from environment variable (for deployment) or use default
    port = int(os.getenv('PORT', 8000))
    
    print(f"Starting Trading Platform server on port {port}")
    print(f"Open your browser and navigate to http://localhost:{port}")
    
    # Run the FastAPI app
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
