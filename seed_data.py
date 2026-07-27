# ============================================================
# seed_data.py — Populate ecoStock with realistic sample data
# ============================================================
# Run this ONCE to fill your database with fake data:
#   .\venv\Scripts\python seed_data.py
#
# Then open http://localhost:8000 and login:
#   Email: manager@ecostock.com
#   Password: password123
# ============================================================

import random
from datetime import date, timedelta, datetime

from app.db.database import SessionLocal, engine, Base
from app.models.models import (
    Store, User, Product, InventoryBatch,
    PriceHistory, Alert, AlertType, BatchStatus,
    ProductCategory, UserRole
)
from app.core.security import hash_password

# ── Step 1: Create tables ─────────────────────────────────
print("📦 Creating database tables...")
Base.metadata.create_all(bind=engine)

# ── Step 2: Get DB session ────────────────────────────────
db = SessionLocal()

try:
    # ── Step 3: Check if already seeded ───────────────────
    existing_products = db.query(Product).count()
    if existing_products > 0:
        print(f"✅ Database already has {existing_products} products — skipping seed.")
        print("   To re-seed, delete the database file and run again.")
        exit()

    # ============================================================
    # STORES
    # ============================================================
    print("🏪 Creating stores...")
    stores_data = [
        {"name": "ecoStock Downtown", "location": "123 Main St, Downtown"},
        {"name": "ecoStock Uptown", "location": "456 Park Ave, Uptown"},
        {"name": "ecoStock Mall", "location": "789 Shopping Center, Westside"},
    ]
    stores = []
    for s in stores_data:
        store = Store(name=s["name"], location=s["location"])
        db.add(store)
        stores.append(store)
    db.flush()

    # ============================================================
    # USERS
    # ============================================================
    print("👤 Creating users...")
    users_data = [
        {"full_name": "Rahul Sharma", "email": "manager@ecostock.com", "password": "password123", "role": UserRole.STORE_MANAGER, "store": stores[0]},
        {"full_name": "Priya Patel", "email": "priya@ecostock.com", "password": "password123", "role": UserRole.FLOOR_STAFF, "store": stores[0]},
        {"full_name": "Amit Singh", "email": "amit@ecostock.com", "password": "password123", "role": UserRole.ADMIN, "store": None},
        {"full_name": "Sneha Reddy", "email": "sneha@ecostock.com", "password": "password123", "role": UserRole.FLOOR_STAFF, "store": stores[1]},
        {"full_name": "Vikram Joshi", "email": "vikram@ecostock.com", "password": "password123", "role": UserRole.STORE_MANAGER, "store": stores[2]},
    ]
    users = []
    for u in users_data:
        user = User(
            full_name=u["full_name"],
            email=u["email"],
            hashed_password=hash_password(u["password"]),
            role=u["role"],
            store_id=u["store"].id if u["store"] else None,
        )
        db.add(user)
        users.append(user)
    db.flush()

    # ============================================================
    # PRODUCTS (Master Catalog)
    # ============================================================
    print("🏷️ Creating products...")
    products_data = [
        # Dairy
        {"sku": "MILK-001", "name": "Full Cream Milk 1L", "category": ProductCategory.DAIRY, "brand": "Amul", "unit": "litre", "price": 56.0, "cost": 42.0, "shelf_life": 5, "trigger": 0.6},
        {"sku": "MILK-002", "name": "Toned Milk 1L", "category": ProductCategory.DAIRY, "brand": "Mother Dairy", "unit": "litre", "price": 48.0, "cost": 36.0, "shelf_life": 5, "trigger": 0.6},
        {"sku": "YOG-001", "name": "Strawberry Yogurt 150g", "category": ProductCategory.DAIRY, "brand": "Epigamia", "unit": "unit", "price": 35.0, "cost": 22.0, "shelf_life": 14, "trigger": 0.7},
        {"sku": "YOG-002", "name": "Greek Yogurt 200g", "category": ProductCategory.DAIRY, "brand": "Yoplait", "unit": "unit", "price": 65.0, "cost": 45.0, "shelf_life": 18, "trigger": 0.7},
        {"sku": "CHS-001", "name": "Cheddar Cheese 200g", "category": ProductCategory.DAIRY, "brand": "Britannia", "unit": "unit", "price": 120.0, "cost": 85.0, "shelf_life": 30, "trigger": 0.75},
        {"sku": "CHS-002", "name": "Mozzarella Cheese 200g", "category": ProductCategory.DAIRY, "brand": "Amul", "unit": "unit", "price": 110.0, "cost": 78.0, "shelf_life": 25, "trigger": 0.7},
        {"sku": "BTR-001", "name": "Salted Butter 500g", "category": ProductCategory.DAIRY, "brand": "Amul", "unit": "unit", "price": 260.0, "cost": 195.0, "shelf_life": 60, "trigger": 0.8},

        # Produce
        {"sku": "VEG-001", "name": "Organic Spinach 250g", "category": ProductCategory.PRODUCE, "brand": "FreshFarm", "unit": "unit", "price": 30.0, "cost": 18.0, "shelf_life": 3, "trigger": 0.5},
        {"sku": "VEG-002", "name": "Tomatoes 1kg", "category": ProductCategory.PRODUCE, "brand": "FarmFresh", "unit": "kg", "price": 40.0, "cost": 25.0, "shelf_life": 5, "trigger": 0.5},
        {"sku": "VEG-003", "name": "Potatoes 5kg", "category": ProductCategory.PRODUCE, "brand": "FreshFarm", "unit": "kg", "price": 80.0, "cost": 50.0, "shelf_life": 14, "trigger": 0.6},
        {"sku": "VEG-004", "name": "Onions 1kg", "category": ProductCategory.PRODUCE, "brand": "FarmFresh", "unit": "kg", "price": 35.0, "cost": 22.0, "shelf_life": 10, "trigger": 0.6},
        {"sku": "FRT-001", "name": "Red Apples 1kg", "category": ProductCategory.PRODUCE, "brand": "KashmirValley", "unit": "kg", "price": 120.0, "cost": 80.0, "shelf_life": 10, "trigger": 0.6},
        {"sku": "FRT-002", "name": "Bananas 1kg", "category": ProductCategory.PRODUCE, "brand": "FreshFarm", "unit": "kg", "price": 45.0, "cost": 28.0, "shelf_life": 4, "trigger": 0.5},
        {"sku": "FRT-003", "name": "Strawberries 200g", "category": ProductCategory.PRODUCE, "brand": "KashmirValley", "unit": "unit", "price": 85.0, "cost": 55.0, "shelf_life": 3, "trigger": 0.4},

        # Bakery
        {"sku": "BAK-001", "name": "Whole Wheat Bread 400g", "category": ProductCategory.BAKERY, "brand": "ModernBakery", "unit": "unit", "price": 40.0, "cost": 25.0, "shelf_life": 4, "trigger": 0.5},
        {"sku": "BAK-002", "name": "Croissant 4-pack", "category": ProductCategory.BAKERY, "brand": "ModernBakery", "unit": "unit", "price": 95.0, "cost": 60.0, "shelf_life": 3, "trigger": 0.5},
        {"sku": "BAK-003", "name": "Chocolate Muffin", "category": ProductCategory.BAKERY, "brand": "SweetTooth", "unit": "unit", "price": 55.0, "cost": 32.0, "shelf_life": 5, "trigger": 0.5},

        # Meat
        {"sku": "MET-001", "name": "Chicken Breast 500g", "category": ProductCategory.MEAT, "brand": "FreshCuts", "unit": "unit", "price": 180.0, "cost": 130.0, "shelf_life": 4, "trigger": 0.5},
        {"sku": "MET-002", "name": "Eggs 12-pack", "category": ProductCategory.MEAT, "brand": "FarmEggs", "unit": "unit", "price": 72.0, "cost": 48.0, "shelf_life": 12, "trigger": 0.6},
        {"sku": "MET-003", "name": "Fish Fillets 250g", "category": ProductCategory.MEAT, "brand": "SeafoodCo", "unit": "unit", "price": 220.0, "cost": 160.0, "shelf_life": 3, "trigger": 0.4},

        # Beverages
        {"sku": "BEV-001", "name": "Orange Juice 1L", "category": ProductCategory.BEVERAGES, "brand": "Tropicana", "unit": "litre", "price": 95.0, "cost": 68.0, "shelf_life": 20, "trigger": 0.7},
        {"sku": "BEV-002", "name": "Coconut Water 1L", "category": ProductCategory.BEVERAGES, "brand": "RawPressery", "unit": "litre", "price": 80.0, "cost": 52.0, "shelf_life": 15, "trigger": 0.7},
        {"sku": "BEV-003", "name": "Cold Coffee 500ml", "category": ProductCategory.BEVERAGES, "brand": "Bru", "unit": "unit", "price": 65.0, "cost": 42.0, "shelf_life": 10, "trigger": 0.6},
    ]

    products = []
    for p in products_data:
        product = Product(
            sku=p["sku"],
            name=p["name"],
            category=p["category"],
            brand=p["brand"],
            unit=p["unit"],
            base_price=p["price"],
            cost_price=p["cost"],
            typical_shelf_life_days=p["shelf_life"],
            discount_trigger_threshold=p["trigger"],
        )
        db.add(product)
        products.append(product)
    db.flush()

    # ============================================================
    # INVENTORY BATCHES — Each product gets 1-3 batches with mixed expiry dates
    # ============================================================
    print("📦 Creating inventory batches...")
    batches = []
    today = date.today()

    for product in products:
        # How many batches for this product?
        num_batches = random.randint(1, 3)

        for b in range(num_batches):
            shelf_life = product.typical_shelf_life_days
            received_date = today - timedelta(days=random.randint(0, shelf_life))
            manufacture_date = received_date - timedelta(days=random.randint(1, 5))

            # Days until expiry: mix of fresh, expiring soon, and expired
            expiry_offset = random.choice([
                # Fresh stock (60% chance)
                random.randint(shelf_life // 2, shelf_life),
                # Near expiry (25% chance)
                random.randint(1, max(1, shelf_life // 3)),
                # Expired (15% chance)
                random.randint(-5, 0),
            ])

            if random.random() < 0.6:
                expiry_offset = random.randint(shelf_life // 2, shelf_life)
            elif random.random() < 0.65:
                expiry_offset = random.randint(1, max(1, shelf_life // 3))
            else:
                expiry_offset = random.randint(-5, 0)

            expiry_date = received_date + timedelta(days=expiry_offset)

            # Quantity
            initial_qty = random.choice([10, 20, 24, 30, 36, 48, 50, 60, 100])
            if expiry_offset <= 0:
                current_qty = random.randint(0, max(1, initial_qty // 4))
            else:
                # Some stock has been sold
                sold = random.randint(0, int(initial_qty * 0.7))
                current_qty = max(1, initial_qty - sold)

            # Determine status based on expiry
            days_left = (expiry_date - today).days
            if days_left <= 0:
                status = BatchStatus.EXPIRED_WASTED if random.random() < 0.3 else BatchStatus.SOLD
                current_qty = 0 if status == BatchStatus.SOLD else current_qty
                current_price = product.base_price
                discount_pct = 0.0
            elif days_left <= 2:
                status = random.choice([BatchStatus.DISCOUNTED, BatchStatus.FLAGGED])
                discount_pct = random.choice([35.0, 50.0])
                current_price = round(product.base_price * (1 - discount_pct / 100), 2)
            elif days_left <= 5:
                status = random.choice([BatchStatus.ACTIVE, BatchStatus.DISCOUNTED])
                if status == BatchStatus.DISCOUNTED:
                    discount_pct = random.choice([20.0, 25.0, 30.0])
                    current_price = round(product.base_price * (1 - discount_pct / 100), 2)
                else:
                    discount_pct = 0.0
                    current_price = product.base_price
            else:
                status = BatchStatus.ACTIVE
                discount_pct = 0.0
                current_price = product.base_price

            batch = InventoryBatch(
                product_id=product.id,
                store_id=random.choice(stores).id,
                batch_number=f"BATCH-{product.sku}-{received_date.strftime('%Y%m%d')}-{b+1}",
                barcode=f"890{random.randint(1000000000, 9999999999)}",
                manufacture_date=manufacture_date,
                expiry_date=expiry_date,
                received_date=received_date,
                initial_quantity=float(initial_qty),
                current_quantity=float(current_qty),
                current_price=current_price,
                discount_percentage=discount_pct,
                status=status,
                storage_location=random.choice(["Aisle 1", "Aisle 2", "Aisle 3", "Cold Storage", "Back Stock"]),
            )
            db.add(batch)
            batches.append(batch)

    db.flush()
    print(f"   Created {len(batches)} inventory batches")

    # ============================================================
    # PRICE HISTORY — Log of markdowns on discounted items
    # ============================================================
    print("💰 Creating price history...")
    price_logs = []
    for batch in batches:
        if batch.status == BatchStatus.DISCOUNTED:
            log = PriceHistory(
                batch_id=batch.id,
                old_price=batch.current_price / (1 - batch.discount_percentage / 100) if batch.discount_percentage > 0 else batch.current_price,
                new_price=batch.current_price,
                discount_pct=batch.discount_percentage,
                days_to_expiry=(batch.expiry_date - today).days,
                triggered_by=random.choice(["system", "system", "system", "manager_override"]),
                note=f"Auto-discount: {batch.discount_percentage:.0f}% off — {batch.product.name if batch.product else 'N/A'} expiring soon",
            )
            db.add(log)
            price_logs.append(log)

    db.flush()
    print(f"   Created {len(price_logs)} price history entries")

    # ============================================================
    # ALERTS
    # ============================================================
    print("🔔 Creating alerts...")
    for batch in batches:
        if not batch.product:
            continue
        days_left = (batch.expiry_date - today).days

        # Alerts for expiring / discounted batches
        if batch.status == BatchStatus.DISCOUNTED:
            alert = Alert(
                store_id=batch.store_id,
                alert_type=AlertType.MARKDOWN_APPLIED,
                batch_id=batch.id,
                title=f"💰 Discount Applied: {batch.product.name}",
                message=f"Price reduced to ₹{batch.current_price:.2f} ({batch.discount_percentage:.0f}% off). {max(0, days_left)} days until expiry.",
                priority=2,
                created_at=datetime.now() - timedelta(hours=random.randint(1, 24)),
            )
            db.add(alert)

        if batch.status == BatchStatus.FLAGGED or (1 <= days_left <= 2 and batch.current_quantity > 0):
            alert = Alert(
                store_id=batch.store_id,
                alert_type=AlertType.FOOD_BANK_DISPATCH,
                batch_id=batch.id,
                title=f"🚛 Routing Needed: {batch.product.name}",
                message=f"Batch expires in {max(0, days_left)} days. Quantity: {batch.current_quantity} {batch.product.unit}. Arrange dispatch.",
                priority=1,
                created_at=datetime.now() - timedelta(hours=random.randint(1, 12)),
            )
            db.add(alert)

        if days_left <= 3 and batch.current_quantity > 0 and random.random() < 0.4:
            alert = Alert(
                store_id=batch.store_id,
                alert_type=AlertType.ROTATION_NEEDED,
                batch_id=batch.id,
                title=f"🔄 Rotation Alert: {batch.product.name}",
                message=f"Move older stock to front. {max(0, days_left)} days until expiry.",
                priority=3,
                created_at=datetime.now() - timedelta(hours=random.randint(2, 48)),
            )
            db.add(alert)

    # ============================================================
    # COMMIT EVERYTHING
    # ============================================================
    db.commit()

    print()
    print("=" * 60)
    print("🎉 DATABASE SEEDED SUCCESSFULLY!")
    print("=" * 60)
    print()
    print(f"   🏪 {len(stores)} Stores")
    print(f"   👤 {len(users_data)} Users")
    print(f"   🏷️  {len(products)} Products")
    print(f"   📦 {len(batches)} Inventory Batches")
    print(f"   💰 {len(price_logs)} Price History Entries")
    print()
    print("   Login Credentials:")
    print("   ─────────────────────")
    print(f"   Email:    manager@ecostock.com")
    print(f"   Password: password123")
    print()
    print("   Open http://localhost:8000 and start exploring!")
    print()

except Exception as e:
    db.rollback()
    print(f"❌ Error seeding database: {e}")
    raise

finally:
    db.close()

