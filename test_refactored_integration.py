"""
Integration test for refactored application.

Tests that the refactored backend works with the existing frontend templates.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_app_starts():
    """Test that the app can start with refactored backend."""
    print("\n" + "="*60)
    print("TEST 1: App Startup with Refactored Backend")
    print("="*60)

    try:
        # Suppress matplotlib warning
        import matplotlib
        matplotlib.use('Agg')

        from app import create_app
        app = create_app('testing')

        assert app is not None
        print("✅ App created successfully")

        # Setup login manager
        from models import User
        from app.extensions import login_manager

        @login_manager.user_loader
        def load_user(user_id):
            from models import db
            return db.session.get(User, int(user_id))

        print("✅ User loader configured")

        return app

    except Exception as e:
        print(f"❌ App startup failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_database_models(app):
    """Test that database models work with new app."""
    print("\n" + "="*60)
    print("TEST 2: Database Models Integration")
    print("="*60)

    if not app:
        print("❌ Skipping - no app available")
        return False

    try:
        with app.app_context():
            from models import db, User, Conversation, Message

            # Create tables
            db.create_all()
            print("✅ Database tables created")

            # Test creating a user
            test_user = User(
                username='test_user',
                email='test@example.com',
                plan_type='free'
            )
            test_user.set_password('Test123!@#')

            db.session.add(test_user)
            db.session.commit()
            print(f"✅ Test user created: {test_user.username}")

            # Test query
            user = User.query.filter_by(username='test_user').first()
            assert user is not None
            assert user.username == 'test_user'
            print(f"✅ User query works: {user.username}")

            # Cleanup
            db.session.delete(user)
            db.session.commit()
            print("✅ Cleanup successful")

            return True

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_services_with_app(app):
    """Test that services work in app context."""
    print("\n" + "="*60)
    print("TEST 3: Service Layer Integration")
    print("="*60)

    if not app:
        print("❌ Skipping - no app available")
        return False

    try:
        with app.app_context():
            from models import db
            from app.services.auth_service import AuthService

            # Create tables
            db.create_all()

            # Test registration
            user, error = AuthService.register_user(
                username='service_test',
                email='service@test.com',
                password='Test123!@#',
                plan_type='free',
                gdpr_consent=True
            )

            if user:
                print(f"✅ User registered via service: {user.username}")
            else:
                print(f"❌ Registration failed: {error}")
                return False

            # Test authentication
            auth_user, auth_error = AuthService.authenticate_user(
                username='service_test',
                password='Test123!@#'
            )

            if auth_user:
                print(f"✅ User authenticated via service: {auth_user.username}")
            else:
                print(f"❌ Authentication failed: {auth_error}")
                return False

            # Cleanup
            db.session.delete(user)
            db.session.commit()
            print("✅ Service cleanup successful")

            return True

    except Exception as e:
        print(f"❌ Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_routes_accessible(app):
    """Test that routes are accessible."""
    print("\n" + "="*60)
    print("TEST 4: Route Accessibility")
    print("="*60)

    if not app:
        print("❌ Skipping - no app available")
        return False

    try:
        client = app.test_client()

        # Test public routes
        routes_to_test = [
            ('/', 'Landing page'),
            ('/auth/login', 'Login page'),
            ('/auth/register', 'Registration page'),
            ('/health', 'Health check'),
        ]

        all_passed = True
        for route, description in routes_to_test:
            try:
                response = client.get(route)
                if response.status_code in [200, 302]:  # 302 = redirect (OK for auth routes)
                    print(f"✅ {description:20} ({route:25}) - Status: {response.status_code}")
                else:
                    print(f"❌ {description:20} ({route:25}) - Status: {response.status_code}")
                    all_passed = False
            except Exception as e:
                print(f"❌ {description:20} ({route:25}) - Error: {e}")
                all_passed = False

        return all_passed

    except Exception as e:
        print(f"❌ Route test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_template_rendering(app):
    """Test that templates can be rendered."""
    print("\n" + "="*60)
    print("TEST 5: Template Rendering")
    print("="*60)

    if not app:
        print("❌ Skipping - no app available")
        return False

    try:
        with app.test_request_context():
            from flask import render_template

            templates_to_test = [
                'login.html',
                'register.html',
                'landing.html',
            ]

            all_passed = True
            for template in templates_to_test:
                try:
                    html = render_template(template)
                    if html and len(html) > 0:
                        print(f"✅ Template rendered: {template:30} ({len(html)} chars)")
                    else:
                        print(f"❌ Template empty: {template}")
                        all_passed = False
                except Exception as e:
                    print(f"❌ Template failed: {template:30} - {e}")
                    all_passed = False

            return all_passed

    except Exception as e:
        print(f"❌ Template rendering test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all integration tests."""
    print("\n" + "="*60)
    print("REFACTORED BACKEND INTEGRATION TEST SUITE")
    print("="*60)
    print("Testing refactored backend with existing frontend")

    results = {}

    # Test 1: App starts
    app = test_app_starts()
    results['App Startup'] = app is not None

    # Test 2: Database models
    results['Database Models'] = test_database_models(app)

    # Test 3: Services
    results['Service Layer'] = test_services_with_app(app)

    # Test 4: Routes
    results['Route Accessibility'] = test_routes_accessible(app)

    # Test 5: Templates
    results['Template Rendering'] = test_template_rendering(app)

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
        print("\n🎉 ALL TESTS PASSED! Refactored backend is working with frontend.")
        print("\nYou can now:")
        print("  1. Run: python run_refactored.py")
        print("  2. Visit: http://localhost:5000")
        print("  3. Test the application in your browser")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review errors above.")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
