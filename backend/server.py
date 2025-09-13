from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
from decimal import Decimal

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-this')

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    role: str = "kasir"  # kasir, admin
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "kasir"

class UserLogin(BaseModel):
    username: str
    password: str

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    sku: str
    description: Optional[str] = ""
    price_regular: float  # Harga pelanggan biasa
    price_sales: float    # Harga sales
    price_bengkel: float  # Harga bengkel
    stock: int
    min_stock: int = 5
    category: Optional[str] = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProductCreate(BaseModel):
    name: str
    sku: str
    description: Optional[str] = ""
    price_regular: float
    price_sales: float
    price_bengkel: float
    stock: int
    min_stock: int = 5
    category: Optional[str] = ""

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price_regular: Optional[float] = None
    price_sales: Optional[float] = None
    price_bengkel: Optional[float] = None
    stock: Optional[int] = None
    min_stock: Optional[int] = None
    category: Optional[str] = None

class CustomerType(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str  # "regular", "sales", "bengkel"
    display_name: str  # "Pelanggan Biasa", "Sales", "Bengkel"
    discount_percentage: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CustomerTypeCreate(BaseModel):
    name: str
    display_name: str
    discount_percentage: float = 0.0

class TransactionItem(BaseModel):
    product_id: str
    product_name: str
    product_sku: str
    quantity: int
    unit_price: float
    discount_amount: float = 0.0
    total_price: float

class Transaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    transaction_number: str
    customer_type: str  # "regular", "sales", "bengkel"
    customer_type_display: str
    items: List[TransactionItem]
    subtotal: float
    discount_total: float
    total_amount: float
    payment_method: str  # "tunai", "transfer"
    payment_amount: float
    change_amount: float = 0.0
    cashier_id: str
    cashier_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "completed"

class TransactionCreate(BaseModel):
    customer_type: str
    items: List[dict]  # {product_id, quantity}
    payment_method: str
    payment_amount: float

class ReportSummary(BaseModel):
    period: str
    start_date: str
    end_date: str
    total_transactions: int
    total_revenue: float
    total_items_sold: int
    payment_methods: dict
    customer_types: dict

# Helper functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict):
    return jwt.encode(data, JWT_SECRET, algorithm="HS256")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(token_data: dict = Depends(verify_token)):
    user = await db.users.find_one({"id": token_data["sub"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**user)

def prepare_for_mongo(data):
    """Convert datetime objects to ISO strings for MongoDB storage"""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, list):
                data[key] = [prepare_for_mongo(item) if isinstance(item, dict) else item for item in value]
    return data

def parse_from_mongo(item):
    """Parse datetime strings back from MongoDB"""
    if isinstance(item, dict):
        for key, value in item.items():
            if key.endswith('_at') and isinstance(value, str):
                try:
                    item[key] = datetime.fromisoformat(value)
                except:
                    pass
            elif isinstance(value, list):
                item[key] = [parse_from_mongo(subitem) if isinstance(subitem, dict) else subitem for subitem in value]
    return item

# Authentication Routes
@api_router.post("/auth/register", response_model=User)
async def register(user_data: UserCreate):
    # Check if username exists
    existing_user = await db.users.find_one({"username": user_data.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username sudah digunakan")
    
    # Hash password and create user
    hashed_password = hash_password(user_data.password)
    user_dict = user_data.dict()
    user_dict['password'] = hashed_password
    user_obj = User(username=user_data.username, role=user_data.role)
    
    user_dict_mongo = prepare_for_mongo(user_dict)
    user_dict_mongo['id'] = user_obj.id
    user_dict_mongo['created_at'] = user_obj.created_at.isoformat()
    
    await db.users.insert_one(user_dict_mongo)
    return user_obj

@api_router.post("/auth/login")
async def login(login_data: UserLogin):
    user = await db.users.find_one({"username": login_data.username})
    if not user or not verify_password(login_data.password, user['password']):
        raise HTTPException(status_code=401, detail="Username atau password salah")
    
    access_token = create_access_token({"sub": user['id'], "username": user['username']})
    return {"access_token": access_token, "token_type": "bearer", "user": User(**user)}

# Product Routes
@api_router.post("/products", response_model=Product)
async def create_product(product_data: ProductCreate, current_user: User = Depends(get_current_user)):
    # Check if SKU exists
    existing_product = await db.products.find_one({"sku": product_data.sku})
    if existing_product:
        raise HTTPException(status_code=400, detail="SKU sudah digunakan")
    
    product_obj = Product(**product_data.dict())
    product_dict = prepare_for_mongo(product_obj.dict())
    
    await db.products.insert_one(product_dict)
    return product_obj

@api_router.get("/products", response_model=List[Product])
async def get_products(current_user: User = Depends(get_current_user)):
    products = await db.products.find().to_list(1000)
    return [Product(**parse_from_mongo(product)) for product in products]

@api_router.get("/products/low-stock")
async def get_low_stock_products(current_user: User = Depends(get_current_user)):
    """Get products with stock below minimum threshold"""
    products = await db.products.find({
        "$expr": {"$lte": ["$stock", "$min_stock"]}
    }).to_list(100)
    return [Product(**parse_from_mongo(product)) for product in products]

@api_router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str, current_user: User = Depends(get_current_user)):
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
    return Product(**parse_from_mongo(product))

@api_router.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: str, product_data: ProductUpdate, current_user: User = Depends(get_current_user)):
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
    
    update_data = {k: v for k, v in product_data.dict().items() if v is not None}
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.products.update_one({"id": product_id}, {"$set": update_data})
    
    updated_product = await db.products.find_one({"id": product_id})
    return Product(**parse_from_mongo(updated_product))

@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, current_user: User = Depends(get_current_user)):
    result = await db.products.delete_one({"id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
    return {"message": "Produk berhasil dihapus"}

# Customer Type Routes
@api_router.post("/customer-types", response_model=CustomerType)
async def create_customer_type(customer_type_data: CustomerTypeCreate, current_user: User = Depends(get_current_user)):
    customer_type_obj = CustomerType(**customer_type_data.dict())
    customer_type_dict = prepare_for_mongo(customer_type_obj.dict())
    
    await db.customer_types.insert_one(customer_type_dict)
    return customer_type_obj

@api_router.get("/customer-types", response_model=List[CustomerType])
async def get_customer_types(current_user: User = Depends(get_current_user)):
    customer_types = await db.customer_types.find().to_list(100)
    return [CustomerType(**parse_from_mongo(ct)) for ct in customer_types]

# Transaction Routes
@api_router.post("/transactions", response_model=Transaction)
async def create_transaction(transaction_data: TransactionCreate, current_user: User = Depends(get_current_user)):
    # Get customer type info
    customer_type = await db.customer_types.find_one({"name": transaction_data.customer_type})
    if not customer_type:
        raise HTTPException(status_code=400, detail="Tipe pelanggan tidak ditemukan")
    
    # Process items and calculate totals
    transaction_items = []
    subtotal = 0.0
    
    for item_data in transaction_data.items:
        product = await db.products.find_one({"id": item_data["product_id"]})
        if not product:
            raise HTTPException(status_code=400, detail=f"Produk dengan ID {item_data['product_id']} tidak ditemukan")
        
        if product["stock"] < item_data["quantity"]:
            raise HTTPException(status_code=400, detail=f"Stok {product['name']} tidak mencukupi")
        
        # Get price based on customer type
        if transaction_data.customer_type == "regular":
            unit_price = product["price_regular"]
        elif transaction_data.customer_type == "sales":
            unit_price = product["price_sales"]
        else:  # bengkel
            unit_price = product["price_bengkel"]
        
        # Apply customer type discount
        discount_amount = unit_price * (customer_type["discount_percentage"] / 100) * item_data["quantity"]
        total_price = (unit_price * item_data["quantity"]) - discount_amount
        
        transaction_item = TransactionItem(
            product_id=product["id"],
            product_name=product["name"],
            product_sku=product["sku"],
            quantity=item_data["quantity"],
            unit_price=unit_price,
            discount_amount=discount_amount,
            total_price=total_price
        )
        
        transaction_items.append(transaction_item)
        subtotal += unit_price * item_data["quantity"]
    
    # Calculate totals
    discount_total = sum(item.discount_amount for item in transaction_items)
    total_amount = subtotal - discount_total
    change_amount = max(0, transaction_data.payment_amount - total_amount)
    
    if transaction_data.payment_amount < total_amount:
        raise HTTPException(status_code=400, detail="Jumlah pembayaran tidak mencukupi")
    
    # Generate transaction number
    transaction_count = await db.transactions.count_documents({})
    transaction_number = f"TRX{datetime.now().strftime('%Y%m%d')}{transaction_count + 1:04d}"
    
    # Create transaction
    transaction_obj = Transaction(
        transaction_number=transaction_number,
        customer_type=transaction_data.customer_type,
        customer_type_display=customer_type["display_name"],
        items=transaction_items,
        subtotal=subtotal,
        discount_total=discount_total,
        total_amount=total_amount,
        payment_method=transaction_data.payment_method,
        payment_amount=transaction_data.payment_amount,
        change_amount=change_amount,
        cashier_id=current_user.id,
        cashier_name=current_user.username
    )
    
    transaction_dict = prepare_for_mongo(transaction_obj.dict())
    await db.transactions.insert_one(transaction_dict)
    
    # Update product stocks
    for item_data in transaction_data.items:
        await db.products.update_one(
            {"id": item_data["product_id"]},
            {"$inc": {"stock": -item_data["quantity"]}}
        )
    
    return transaction_obj

@api_router.get("/transactions", response_model=List[Transaction])
async def get_transactions(current_user: User = Depends(get_current_user)):
    transactions = await db.transactions.find().sort("created_at", -1).to_list(100)
    return [Transaction(**parse_from_mongo(transaction)) for transaction in transactions]

@api_router.get("/transactions/{transaction_id}", response_model=Transaction)
async def get_transaction(transaction_id: str, current_user: User = Depends(get_current_user)):
    transaction = await db.transactions.find_one({"id": transaction_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
    return Transaction(**parse_from_mongo(transaction))

# Report Routes
@api_router.get("/reports/daily")
async def get_daily_report(date: str, current_user: User = Depends(get_current_user)):
    """Get daily report for specific date (YYYY-MM-DD format)"""
    try:
        start_date = datetime.fromisoformat(f"{date}T00:00:00")
        end_date = datetime.fromisoformat(f"{date}T23:59:59")
    except:
        raise HTTPException(status_code=400, detail="Format tanggal tidak valid (gunakan YYYY-MM-DD)")
    
    # Get transactions for the day
    transactions = await db.transactions.find({
        "created_at": {
            "$gte": start_date.isoformat(),
            "$lte": end_date.isoformat()
        }
    }).to_list(1000)
    
    total_revenue = sum(t["total_amount"] for t in transactions)
    total_items_sold = sum(sum(item["quantity"] for item in t["items"]) for t in transactions)
    
    # Group by payment method
    payment_methods = {}
    for t in transactions:
        method = t["payment_method"]
        payment_methods[method] = payment_methods.get(method, 0) + t["total_amount"]
    
    # Group by customer type
    customer_types = {}
    for t in transactions:
        ctype = t["customer_type_display"]
        customer_types[ctype] = customer_types.get(ctype, 0) + t["total_amount"]
    
    return ReportSummary(
        period="daily",
        start_date=date,
        end_date=date,
        total_transactions=len(transactions),
        total_revenue=total_revenue,
        total_items_sold=total_items_sold,
        payment_methods=payment_methods,
        customer_types=customer_types
    )

@api_router.get("/reports/weekly")
async def get_weekly_report(start_date: str, current_user: User = Depends(get_current_user)):
    """Get weekly report starting from start_date (YYYY-MM-DD format)"""
    try:
        start = datetime.fromisoformat(f"{start_date}T00:00:00")
        end = datetime.fromisoformat(f"{start_date}T00:00:00")
        end = end.replace(day=start.day + 6, hour=23, minute=59, second=59)
    except:
        raise HTTPException(status_code=400, detail="Format tanggal tidak valid (gunakan YYYY-MM-DD)")
    
    transactions = await db.transactions.find({
        "created_at": {
            "$gte": start.isoformat(),
            "$lte": end.isoformat()
        }
    }).to_list(1000)
    
    total_revenue = sum(t["total_amount"] for t in transactions)
    total_items_sold = sum(sum(item["quantity"] for item in t["items"]) for t in transactions)
    
    payment_methods = {}
    for t in transactions:
        method = t["payment_method"]
        payment_methods[method] = payment_methods.get(method, 0) + t["total_amount"]
    
    customer_types = {}
    for t in transactions:
        ctype = t["customer_type_display"]
        customer_types[ctype] = customer_types.get(ctype, 0) + t["total_amount"]
    
    return ReportSummary(
        period="weekly",
        start_date=start_date,
        end_date=end.strftime("%Y-%m-%d"),
        total_transactions=len(transactions),
        total_revenue=total_revenue,
        total_items_sold=total_items_sold,
        payment_methods=payment_methods,
        customer_types=customer_types
    )

@api_router.get("/reports/monthly")
async def get_monthly_report(month: str, current_user: User = Depends(get_current_user)):
    """Get monthly report for specific month (YYYY-MM format)"""
    try:
        year, month_num = month.split('-')
        start = datetime(int(year), int(month_num), 1)
        if int(month_num) == 12:
            end = datetime(int(year) + 1, 1, 1)
        else:
            end = datetime(int(year), int(month_num) + 1, 1)
    except:
        raise HTTPException(status_code=400, detail="Format bulan tidak valid (gunakan YYYY-MM)")
    
    transactions = await db.transactions.find({
        "created_at": {
            "$gte": start.isoformat(),
            "$lt": end.isoformat()
        }
    }).to_list(1000)
    
    total_revenue = sum(t["total_amount"] for t in transactions)
    total_items_sold = sum(sum(item["quantity"] for item in t["items"]) for t in transactions)
    
    payment_methods = {}
    for t in transactions:
        method = t["payment_method"]
        payment_methods[method] = payment_methods.get(method, 0) + t["total_amount"]
    
    customer_types = {}
    for t in transactions:
        ctype = t["customer_type_display"]
        customer_types[ctype] = customer_types.get(ctype, 0) + t["total_amount"]
    
    return ReportSummary(
        period="monthly",
        start_date=start.strftime("%Y-%m-%d"),
        end_date=(end - timedelta(days=1)).strftime("%Y-%m-%d"),
        total_transactions=len(transactions),
        total_revenue=total_revenue,
        total_items_sold=total_items_sold,
        payment_methods=payment_methods,
        customer_types=customer_types
    )

# Dashboard Stats
@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Get dashboard statistics"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Today's transactions
    today_transactions = await db.transactions.find({
        "created_at": {
            "$gte": f"{today}T00:00:00",
            "$lte": f"{today}T23:59:59"
        }
    }).to_list(1000)
    
    today_revenue = sum(t["total_amount"] for t in today_transactions)
    
    # Product counts
    total_products = await db.products.count_documents({})
    low_stock_count = await db.products.count_documents({
        "$expr": {"$lte": ["$stock", "$min_stock"]}
    })
    
    return {
        "today_transactions": len(today_transactions),
        "today_revenue": today_revenue,
        "total_products": total_products,
        "low_stock_products": low_stock_count
    }

# Initialize default data
@api_router.post("/init")
async def initialize_data():
    """Initialize default customer types and admin user"""
    # Check if already initialized
    existing_types = await db.customer_types.count_documents({})
    if existing_types > 0:
        return {"message": "Data sudah diinisialisasi"}
    
    # Create default customer types
    default_customer_types = [
        {"name": "regular", "display_name": "Pelanggan Biasa", "discount_percentage": 0.0},
        {"name": "sales", "display_name": "Sales", "discount_percentage": 5.0},
        {"name": "bengkel", "display_name": "Bengkel", "discount_percentage": 10.0}
    ]
    
    for ct_data in default_customer_types:
        ct_obj = CustomerType(**ct_data)
        ct_dict = prepare_for_mongo(ct_obj.dict())
        await db.customer_types.insert_one(ct_dict)
    
    # Create default admin user
    admin_user = UserCreate(username="admin", password="admin123", role="admin")
    hashed_password = hash_password(admin_user.password)
    user_obj = User(username=admin_user.username, role=admin_user.role)
    
    user_dict = {
        "id": user_obj.id,
        "username": user_obj.username,
        "password": hashed_password,
        "role": user_obj.role,
        "created_at": user_obj.created_at.isoformat()
    }
    
    await db.users.insert_one(user_dict)
    
    return {"message": "Data berhasil diinisialisasi"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()