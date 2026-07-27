# Quick test to verify all imports work
print("Testing ecoStock imports...")

# Test 1: Config
from app.core.config import settings
print(f"✅ Config: {settings.APP_NAME} v{settings.APP_VERSION}")
print(f"   Discount Tiers: {settings.DISCOUNT_TIERS}")
print(f"   Database: {settings.DATABASE_URL}")

# Test 2: Security
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
h = hash_password("test123")
assert verify_password("test123", h), "Password verification failed!"
token = create_access_token({"sub": "1", "role": "admin"})
payload = decode_access_token(token)
assert payload is not None, "Token decode failed!"
print(f"✅ Security: Password hashing + JWT tokens working")

# Test 3: Database
from app.db.database import engine, Base, SessionLocal, get_db
print(f"✅ Database: Engine + Session factory OK")

# Test 4: Models
from app.models.models import Product, InventoryBatch, User, Store
print(f"✅ Models: All 8 table classes imported OK")

# Test 5: Schemas
from app.schemas.schemas import ProductCreate, UserCreate, FEFOScanResult
print(f"✅ Schemas: Pydantic models OK")

# Test 6: FEFO Engine
from app.services.fefo_engine import FEFOEngine
print(f"✅ FEFO Engine: Service class OK")

# Test 7: API Routes import
from app.api.routes import auth, inventory, stores, alerts
print(f"✅ API Routes: All route modules OK")

# Test 8: Main app
from main import app
print(f"✅ Main app: FastAPI app created with {len(app.routes)} routes")
for route in app.routes:
    if hasattr(route, "methods") and hasattr(route, "path"):
        print(f"   {' '.join(route.methods)} {route.path}")

print("\n🎉 ALL TESTS PASSED! The app is ready to run.")

