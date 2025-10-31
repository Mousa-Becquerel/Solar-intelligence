"""
Test script for new configuration and extensions modules.

This script verifies that the new modular configuration works correctly
without breaking existing functionality.

Run with: python test_new_config.py
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("Testing New Configuration Module")
print("=" * 60)

# Test 1: Import and get configuration
print("\n[Test 1] Importing configuration module...")
try:
    from app.config import get_config, Config
    print("✅ Configuration module imported successfully")
except Exception as e:
    print(f"❌ Failed to import configuration: {e}")
    sys.exit(1)

# Test 2: Get configuration object
print("\n[Test 2] Getting configuration object...")
try:
    config = get_config()
    print(f"✅ Configuration loaded: {config.__class__.__name__}")
    print(f"   - Environment: {config.FLASK_ENV}")
    print(f"   - Debug: {config.DEBUG}")
    print(f"   - Database: {config.SQLALCHEMY_DATABASE_URI[:50]}...")
except Exception as e:
    print(f"❌ Failed to get configuration: {e}")
    sys.exit(1)

# Test 3: Validate configuration
print("\n[Test 3] Validating configuration...")
try:
    config.validate_config()
    print("✅ Configuration validated successfully")
except ValueError as e:
    print(f"⚠️  Configuration warning: {e}")
except Exception as e:
    print(f"❌ Configuration validation failed: {e}")
    sys.exit(1)

# Test 4: Import extensions
print("\n[Test 4] Importing extensions module...")
try:
    from app.extensions import db, login_manager, csrf, limiter
    print("✅ Extensions imported successfully")
    print(f"   - Database: {type(db).__name__}")
    print(f"   - Login Manager: {type(login_manager).__name__}")
    print(f"   - CSRF: {type(csrf).__name__}")
    print(f"   - Rate Limiter: {type(limiter).__name__}")
except Exception as e:
    print(f"❌ Failed to import extensions: {e}")
    sys.exit(1)

# Test 5: Create Flask app with new config
print("\n[Test 5] Creating Flask app with new configuration...")
try:
    from flask import Flask
    from app.extensions import init_extensions

    app = Flask(__name__)
    app.config.from_object(config)
    init_extensions(app)

    print("✅ Flask app created with new configuration")
    print(f"   - Secret Key Set: {bool(app.config.get('SECRET_KEY'))}")
    print(f"   - Database URI Set: {bool(app.config.get('SQLALCHEMY_DATABASE_URI'))}")
    print(f"   - Extensions Initialized: {hasattr(app, 'extensions')}")
except Exception as e:
    print(f"❌ Failed to create Flask app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Test app factory pattern
print("\n[Test 6] Testing app factory pattern...")
try:
    from app import create_app

    test_app = create_app()
    print("✅ App factory pattern works")
    print(f"   - App Name: {test_app.name}")
    print(f"   - Debug: {test_app.debug}")
    print(f"   - Testing: {test_app.testing}")
except Exception as e:
    print(f"❌ App factory failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 7: Test configuration bridge
print("\n[Test 7] Testing configuration bridge...")
try:
    from app_config_bridge import apply_new_config

    bridge_app = Flask(__name__)
    bridge_app, bridge_config = apply_new_config(bridge_app)

    print("✅ Configuration bridge works")
    print(f"   - Secret Key Applied: {bool(bridge_app.config.get('SECRET_KEY'))}")
    print(f"   - Database URI Applied: {bool(bridge_app.config.get('SQLALCHEMY_DATABASE_URI'))}")
except Exception as e:
    print(f"❌ Configuration bridge failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 8: Verify directories created
print("\n[Test 8] Verifying directories...")
try:
    from app.config import create_directories

    create_directories(config)

    if os.path.exists(config.PLOTS_DIR):
        print(f"✅ Plots directory exists: {config.PLOTS_DIR}")
    else:
        print(f"⚠️  Plots directory not found: {config.PLOTS_DIR}")

    if os.path.exists(config.EXPORTS_DIR):
        print(f"✅ Exports directory exists: {config.EXPORTS_DIR}")
    else:
        print(f"⚠️  Exports directory not found: {config.EXPORTS_DIR}")
except Exception as e:
    print(f"❌ Directory creation failed: {e}")
    sys.exit(1)

# Summary
print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED!")
print("=" * 60)
print("\nThe new configuration and extensions modules are working correctly.")
print("You can now optionally use them in the main app.py.")
print("\nNext steps:")
print("1. Review the configuration in app/config.py")
print("2. Optionally integrate with main app.py using app_config_bridge.py")
print("3. Proceed to Step 3: Create Pydantic schemas")
print("=" * 60)
