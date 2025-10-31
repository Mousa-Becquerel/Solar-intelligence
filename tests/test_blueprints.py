"""
Test suite for Flask blueprints.

Tests all 5 blueprints to ensure they're properly registered and working.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_app_creation():
    """Test that the app factory creates an app successfully."""
    print("\n" + "="*60)
    print("TEST 1: App Creation")
    print("="*60)

    try:
        from app import create_app
        app = create_app('testing')

        assert app is not None
        print("✅ App created successfully")
        print(f"   App name: {app.name}")
        print(f"   Config: {app.config.get('ENV', 'unknown')}")
        return app

    except Exception as e:
        print(f"❌ App creation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_blueprints_registered(app):
    """Test that all blueprints are registered."""
    print("\n" + "="*60)
    print("TEST 2: Blueprint Registration")
    print("="*60)

    if not app:
        print("❌ Skipping - no app available")
        return False

    try:
        # Get all registered blueprints
        blueprints = app.blueprints

        expected_blueprints = ['static', 'auth', 'chat', 'conversation', 'admin']

        print(f"\nRegistered blueprints: {list(blueprints.keys())}")

        all_found = True
        for bp_name in expected_blueprints:
            if bp_name in blueprints:
                print(f"✅ Blueprint '{bp_name}' registered")
            else:
                print(f"❌ Blueprint '{bp_name}' NOT registered")
                all_found = False

        return all_found

    except Exception as e:
        print(f"❌ Blueprint check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_routes_registered(app):
    """Test that routes are registered correctly."""
    print("\n" + "="*60)
    print("TEST 3: Route Registration")
    print("="*60)

    if not app:
        print("❌ Skipping - no app available")
        return False

    try:
        # Get all registered routes
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'})),
                'path': str(rule)
            })

        print(f"\nTotal routes registered: {len(routes)}")

        # Check for key routes from each blueprint
        key_routes = {
            'static.landing': '/',
            'static.waitlist': '/waitlist',
            'auth.login': '/auth/login',
            'auth.register': '/auth/register',
            'chat.agents': '/agents',
            'chat.query': '/query',
            'conversation.get_conversations': '/conversations/',
            'admin.users': '/admin/users',
        }

        print("\nChecking key routes:")
        all_found = True
        for endpoint, expected_path in key_routes.items():
            found = False
            for route in routes:
                if route['endpoint'] == endpoint:
                    print(f"✅ {endpoint:35} -> {route['path']:30} [{route['methods']}]")
                    found = True
                    break

            if not found:
                print(f"❌ {endpoint:35} -> NOT FOUND")
                all_found = False

        # Print all routes for debugging
        print("\n" + "-"*60)
        print("All registered routes:")
        print("-"*60)
        for route in sorted(routes, key=lambda x: x['path']):
            print(f"{route['path']:40} [{route['methods']:15}] -> {route['endpoint']}")

        return all_found

    except Exception as e:
        print(f"❌ Route check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_blueprint_imports():
    """Test that all blueprint modules can be imported."""
    print("\n" + "="*60)
    print("TEST 4: Blueprint Module Imports")
    print("="*60)

    blueprints = [
        ('app.routes.auth', 'auth_bp'),
        ('app.routes.chat', 'chat_bp'),
        ('app.routes.conversation', 'conversation_bp'),
        ('app.routes.admin', 'admin_bp'),
        ('app.routes.static_pages', 'static_bp'),
    ]

    all_imported = True
    for module_name, bp_name in blueprints:
        try:
            module = __import__(module_name, fromlist=[bp_name])
            bp = getattr(module, bp_name)
            print(f"✅ {module_name:30} -> {bp_name:15} (name: {bp.name})")
        except Exception as e:
            print(f"❌ {module_name:30} -> Failed: {e}")
            all_imported = False

    return all_imported


def test_service_imports():
    """Test that all services can be imported."""
    print("\n" + "="*60)
    print("TEST 5: Service Module Imports")
    print("="*60)

    services = [
        ('app.services.auth_service', 'AuthService'),
        ('app.services.conversation_service', 'ConversationService'),
        ('app.services.agent_service', 'AgentService'),
        ('app.services.admin_service', 'AdminService'),
    ]

    all_imported = True
    for module_name, service_name in services:
        try:
            module = __import__(module_name, fromlist=[service_name])
            service = getattr(module, service_name)

            # Count methods
            methods = [m for m in dir(service) if not m.startswith('_') and callable(getattr(service, m))]
            print(f"✅ {module_name:35} -> {service_name:20} ({len(methods)} methods)")
        except Exception as e:
            print(f"❌ {module_name:35} -> Failed: {e}")
            all_imported = False

    return all_imported


def test_schema_imports():
    """Test that all schemas can be imported."""
    print("\n" + "="*60)
    print("TEST 6: Schema Module Imports")
    print("="*60)

    schemas = [
        'app.schemas.user',
        'app.schemas.conversation',
        'app.schemas.agent',
        'app.schemas.feedback',
    ]

    all_imported = True
    for schema_module in schemas:
        try:
            module = __import__(schema_module, fromlist=['*'])

            # Count schemas (classes that end with 'Schema')
            schema_classes = [name for name in dir(module) if name.endswith('Schema')]
            print(f"✅ {schema_module:30} -> {len(schema_classes)} schemas")
        except Exception as e:
            print(f"❌ {schema_module:30} -> Failed: {e}")
            all_imported = False

    return all_imported


def test_extensions_initialized(app):
    """Test that extensions are properly initialized."""
    print("\n" + "="*60)
    print("TEST 7: Extension Initialization")
    print("="*60)

    if not app:
        print("❌ Skipping - no app available")
        return False

    try:
        from app.extensions import db, login_manager, csrf, limiter

        # Check db
        print(f"✅ SQLAlchemy initialized: {db is not None}")
        print(f"   Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')[:50]}...")

        # Check login_manager
        print(f"✅ LoginManager initialized: {login_manager is not None}")

        # Check csrf
        print(f"✅ CSRFProtect initialized: {csrf is not None}")

        # Check limiter
        print(f"✅ Limiter initialized: {limiter is not None}")

        return True

    except Exception as e:
        print(f"❌ Extension check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "="*60)
    print("BLUEPRINT INTEGRATION TEST SUITE")
    print("="*60)
    print("Testing all blueprints, services, schemas, and routes")

    results = {}

    # Test 1: App creation
    app = test_app_creation()
    results['App Creation'] = app is not None

    # Test 2: Blueprints registered
    results['Blueprints Registered'] = test_blueprints_registered(app)

    # Test 3: Routes registered
    results['Routes Registered'] = test_routes_registered(app)

    # Test 4: Blueprint imports
    results['Blueprint Imports'] = test_blueprint_imports()

    # Test 5: Service imports
    results['Service Imports'] = test_service_imports()

    # Test 6: Schema imports
    results['Schema Imports'] = test_schema_imports()

    # Test 7: Extensions initialized
    results['Extensions Initialized'] = test_extensions_initialized(app)

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = 0
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:8} - {test_name}")
        if result:
            passed += 1

    print("\n" + "-"*60)
    print(f"Results: {passed}/{total} tests passed ({passed*100//total}%)")
    print("="*60)

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Blueprint integration is working correctly.")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review errors above.")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
