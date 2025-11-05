"""
Database migration script for agent access control.

This script adds the AgentAccess and AgentWhitelist tables to enable
fine-grained control over which users can access which agents.

Usage:
    python migrations/add_agent_access_control.py
"""

from app import create_app
from models import db, AgentAccess, AgentWhitelist
from datetime import datetime


def create_tables():
    """Create the new agent access control tables."""
    app = create_app()

    with app.app_context():
        print("Creating agent access control tables...")

        # Create tables
        db.create_all()

        print("✅ Tables created successfully")


def seed_default_agent_access():
    """
    Seed default agent access configurations.

    This creates default access rules for all existing agents.
    You can modify these defaults based on your business model.
    """
    app = create_app()

    with app.app_context():
        print("\nSeeding default agent access configurations...")

        # Default agent configurations
        # Format: (agent_type, required_plan, description)
        default_agents = [
            ('market', 'free', 'Market Intelligence Agent - Available to all users'),
            ('price', 'premium', 'Price Analytics Agent - Requires Premium plan or whitelist'),
            ('news', 'free', 'News & Updates Agent - Available to all users'),
            ('digitalization', 'premium', 'Digitalization Trends Agent - Requires Premium plan or whitelist'),
            ('nzia_policy', 'premium', 'NZIA Policy Expert Agent - Requires Premium plan or whitelist'),
            ('nzia_market_impact', 'premium', 'NZIA Market Impact Expert Agent - Requires Premium plan or whitelist'),
            ('manufacturer_financial', 'premium', 'Manufacturer Financial Analyst Agent - Requires Premium plan or whitelist'),
            ('om', 'max', 'Operations & Maintenance Agent - Requires Max plan or whitelist'),
            ('design', 'max', 'System Design Agent - Requires Max plan or whitelist'),
            ('forecasting', 'premium', 'Energy Forecasting Agent - Requires Premium plan or whitelist'),
            ('permitting', 'premium', 'Permitting & Compliance Agent - Requires Premium plan or whitelist'),
            ('technology', 'free', 'Technology Knowledge Agent - Available to all users'),
        ]

        for agent_type, required_plan, description in default_agents:
            # Check if already exists
            existing = AgentAccess.query.filter_by(agent_type=agent_type).first()

            if existing:
                print(f"⚠️  Agent '{agent_type}' already configured, skipping...")
                continue

            # Create new agent access configuration
            agent_access = AgentAccess(
                agent_type=agent_type,
                required_plan=required_plan,
                is_enabled=True,
                description=description,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            db.session.add(agent_access)
            print(f"✅ Configured '{agent_type}' agent (requires: {required_plan})")

        db.session.commit()
        print("\n✅ Default agent access configurations seeded successfully")


def main():
    """Run the migration."""
    print("=" * 70)
    print("Agent Access Control Migration")
    print("=" * 70)

    try:
        # Step 1: Create tables
        create_tables()

        # Step 2: Seed default configurations
        seed_default_agent_access()

        print("\n" + "=" * 70)
        print("✅ Migration completed successfully!")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Review agent access configurations in the admin panel")
        print("2. Add users to whitelist for premium agents if needed")
        print("3. Adjust required_plan levels based on your pricing strategy")
        print("\nTo grant a user access to a restricted agent:")
        print("  - Use the admin panel (coming soon)")
        print("  - Or manually add to AgentWhitelist table")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
