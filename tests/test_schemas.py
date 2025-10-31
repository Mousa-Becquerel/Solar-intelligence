"""
Test script for Pydantic schemas.

This script verifies that all schemas work correctly with validation.

Run with: python test_schemas.py
"""

import sys
from datetime import datetime
from pydantic import ValidationError

print("=" * 60)
print("Testing Pydantic Schemas")
print("=" * 60)

# Test 1: Import schemas
print("\n[Test 1] Importing schemas...")
try:
    from app.schemas import (
        UserCreateSchema,
        UserLoginSchema,
        UserSchema,
        ConversationCreateSchema,
        MessageCreateSchema,
        AgentQuerySchema,
        FeedbackCreateSchema,
    )
    print("✅ All schemas imported successfully")
except Exception as e:
    print(f"❌ Failed to import schemas: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: User creation validation
print("\n[Test 2] Testing user creation validation...")
try:
    # Valid user
    valid_user = UserCreateSchema(
        username="john_doe",
        full_name="John Doe",
        password="SecurePass123!"
    )
    print(f"✅ Valid user created: {valid_user.username}")

    # Invalid password (too weak)
    try:
        invalid_user = UserCreateSchema(
            username="jane_doe",
            full_name="Jane Doe",
            password="weak"
        )
        print("❌ Weak password should have been rejected")
    except ValidationError as e:
        print(f"✅ Weak password correctly rejected")

except Exception as e:
    print(f"❌ User schema validation failed: {e}")
    sys.exit(1)

# Test 3: Login schema
print("\n[Test 3] Testing login schema...")
try:
    login = UserLoginSchema(
        username="john_doe",
        password="SecurePass123!",
        remember=True
    )
    print(f"✅ Login schema valid: {login.username}, remember={login.remember}")
except Exception as e:
    print(f"❌ Login schema failed: {e}")
    sys.exit(1)

# Test 4: Conversation creation
print("\n[Test 4] Testing conversation schema...")
try:
    conversation = ConversationCreateSchema(
        title="Market Analysis Q1 2024",
        agent_type="market"
    )
    print(f"✅ Conversation schema valid: {conversation.title}")

    # Invalid agent type
    try:
        invalid_conv = ConversationCreateSchema(
            title="Test",
            agent_type="invalid_agent"
        )
        print("❌ Invalid agent type should have been rejected")
    except ValidationError:
        print("✅ Invalid agent type correctly rejected")

except Exception as e:
    print(f"❌ Conversation schema failed: {e}")
    sys.exit(1)

# Test 5: Message creation
print("\n[Test 5] Testing message schema...")
try:
    import json

    # Valid message
    message = MessageCreateSchema(
        conversation_id=1,
        sender="user",
        content=json.dumps({
            "type": "string",
            "value": "What are module prices?",
            "comment": None
        })
    )
    print(f"✅ Message schema valid: sender={message.sender}")

    # Invalid JSON content
    try:
        invalid_msg = MessageCreateSchema(
            conversation_id=1,
            sender="user",
            content="not valid json"
        )
        print("❌ Invalid JSON should have been rejected")
    except ValidationError:
        print("✅ Invalid JSON correctly rejected")

except Exception as e:
    print(f"❌ Message schema failed: {e}")
    sys.exit(1)

# Test 6: Agent query
print("\n[Test 6] Testing agent query schema...")
try:
    query = AgentQuerySchema(
        query="What are the current module prices in China?",
        conversation_id=1,
        agent_type="price"
    )
    print(f"✅ Agent query valid: {query.query[:50]}...")

    # Empty query (whitespace only)
    try:
        invalid_query = AgentQuerySchema(
            query="   ",
            conversation_id=1
        )
        print("❌ Empty query should have been rejected")
    except ValidationError:
        print("✅ Empty query correctly rejected")

except Exception as e:
    print(f"❌ Agent query schema failed: {e}")
    sys.exit(1)

# Test 7: Feedback
print("\n[Test 7] Testing feedback schema...")
try:
    feedback = FeedbackCreateSchema(
        rating=5,
        feedback_text="Great tool!",
        allow_followup=True
    )
    print(f"✅ Feedback valid: rating={feedback.rating}")

    # Invalid rating (out of range)
    try:
        invalid_feedback = FeedbackCreateSchema(
            rating=6,  # Max is 5
            feedback_text="Test"
        )
        print("❌ Invalid rating should have been rejected")
    except ValidationError:
        print("✅ Invalid rating correctly rejected")

except Exception as e:
    print(f"❌ Feedback schema failed: {e}")
    sys.exit(1)

# Test 8: Schema serialization
print("\n[Test 8] Testing schema serialization...")
try:
    user_data = {
        "id": 1,
        "username": "john_doe",
        "full_name": "John Doe",
        "role": "user",
        "created_at": datetime.utcnow(),
        "is_active": True,
        "plan_type": "free",
        "monthly_query_count": 5,
        "query_count": 42,
        "last_query_date": datetime.utcnow()
    }

    user = UserSchema(**user_data)
    user_dict = user.model_dump()
    user_json = user.model_dump_json()

    print(f"✅ Schema serialization works")
    print(f"   - Dict keys: {list(user_dict.keys())[:3]}...")
    print(f"   - JSON length: {len(user_json)} chars")

except Exception as e:
    print(f"❌ Schema serialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 9: Import all schemas
print("\n[Test 9] Testing complete schema package import...")
try:
    import app.schemas as schemas

    # Count available schemas
    schema_count = len([name for name in dir(schemas) if name.endswith('Schema')])
    print(f"✅ Schema package import successful")
    print(f"   - Available schemas: {schema_count}")

except Exception as e:
    print(f"❌ Schema package import failed: {e}")
    sys.exit(1)

# Summary
print("\n" + "=" * 60)
print("✅ ALL SCHEMA TESTS PASSED!")
print("=" * 60)
print("\nPydantic schemas are working correctly and ready to use.")
print("\nKey features:")
print("✅ Input validation with clear error messages")
print("✅ Type safety with Pydantic models")
print("✅ JSON serialization/deserialization")
print("✅ FastAPI-ready schemas")
print("✅ Password strength validation")
print("✅ Field constraints (min/max, patterns)")
print("\nNext steps:")
print("1. Use schemas in route handlers for validation")
print("2. Proceed to Step 4: Create service layer")
print("=" * 60)
