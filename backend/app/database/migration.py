import json
import logging
from sqlalchemy import text
from app.database.connection import engine, Base, SessionLocal
from app.models.billing import SubscriptionPlan

logger = logging.getLogger("nova_ai.migration")

def run_migrations():
    """Ensure all required columns exist in existing tables and seed default data."""
    # 1. Create any missing tables
    Base.metadata.create_all(bind=engine)

    # 2. Add columns to users table if missing (for existing sqlite databases)
    with engine.connect() as conn:
        try:
            # Check SQLite or Postgres
            dialect = engine.dialect.name
            if dialect == "sqlite":
                res = conn.execute(text("PRAGMA table_info(users)"))
                existing_cols = {row[1] for row in res.fetchall()}
                
                columns_to_add = [
                    ("role", "VARCHAR(20) DEFAULT 'user' NOT NULL"),
                    ("is_active", "BOOLEAN DEFAULT 1 NOT NULL"),
                    ("credits", "INTEGER DEFAULT 50 NOT NULL"),
                    ("plan", "VARCHAR(20) DEFAULT 'free' NOT NULL"),
                    ("plan_expires_at", "DATETIME NULL"),
                    ("full_name", "VARCHAR(100) DEFAULT '' NULL"),
                ]
                for col_name, col_def in columns_to_add:
                    if col_name not in existing_cols:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"))
                        logger.info(f"Added column {col_name} to users table")

                # Ensure admin access for user ID 1
                conn.execute(text("UPDATE users SET role = 'admin' WHERE id = 1 AND (role IS NULL OR role = 'user')"))
                conn.commit()
            elif dialect == "postgresql":
                # PostgreSQL migration
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user',
                    ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE,
                    ADD COLUMN IF NOT EXISTS credits INTEGER DEFAULT 50,
                    ADD COLUMN IF NOT EXISTS plan VARCHAR(20) DEFAULT 'free',
                    ADD COLUMN IF NOT EXISTS plan_expires_at TIMESTAMP WITH TIME ZONE NULL,
                    ADD COLUMN IF NOT EXISTS full_name VARCHAR(100) DEFAULT '';
                """))
                conn.commit()
        except Exception as e:
            logger.warning(f"Column migration warning (safe to ignore if already up to date): {e}")

    # 3. Seed default subscription plans
    db = SessionLocal()
    try:
        if db.query(SubscriptionPlan).count() == 0:
            free_plan = SubscriptionPlan(
                plan_code="free",
                name="Free Starter",
                description="Essential AI tools to explore and create.",
                price_month_uzs=0,
                price_year_uzs=0,
                monthly_credits=50,
                max_chat_messages=50,
                max_images=15,
                max_edits=10,
                max_videos=2,
                max_audio=10,
                features_json=json.dumps([
                    "50 AI Credits monthly",
                    "Basic AI Chat (GPT-4o mini)",
                    "Standard Image Generation (1:1, 16:9)",
                    "Basic Image Editing",
                    "Standard Queue Priority",
                ]),
                is_active=True
            )
            pro_plan = SubscriptionPlan(
                plan_code="pro",
                name="Pro Creator",
                description="For designers, developers and power users.",
                price_month_uzs=99000,
                price_year_uzs=990000,
                monthly_credits=500,
                max_chat_messages=500,
                max_images=150,
                max_edits=100,
                max_videos=20,
                max_audio=100,
                features_json=json.dumps([
                    "500 AI Credits monthly",
                    "Advanced AI Chat & Code Assistant",
                    "HD Image Generation & Negative Prompts",
                    "Multi-style Image Editor",
                    "AI Video Generation Access",
                    "Voice Studio & Music Generator",
                    "Priority Generation Queue",
                ]),
                is_active=True
            )
            premium_plan = SubscriptionPlan(
                plan_code="premium",
                name="Ultra Enterprise",
                description="Unlimited creative freedom with highest priority.",
                price_month_uzs=249000,
                price_year_uzs=2490000,
                monthly_credits=2000,
                max_chat_messages=2500,
                max_images=800,
                max_edits=500,
                max_videos=100,
                max_audio=500,
                features_json=json.dumps([
                    "2,000 AI Credits monthly",
                    "Top-Tier AI Intelligence & Full Code Sandbox",
                    "Ultra-Res Image Generation & Inpainting",
                    "Extended Video Generation",
                    "Commercial License for All Media",
                    "Instant Processing / Zero Queue",
                    "24/7 Dedicated Support",
                ]),
                is_active=True
            )
            db.add_all([free_plan, pro_plan, premium_plan])
            db.commit()
            logger.info("Seeded default subscription plans.")
    except Exception as e:
        logger.warning(f"Error seeding plans: {e}")
        db.rollback()
    finally:
        db.close()

