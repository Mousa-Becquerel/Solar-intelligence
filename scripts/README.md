# Scripts Directory

This directory contains organized utility scripts, tests, and deployment tools for the PV Market Analysis application.

## 📁 Directory Structure

### 🧪 `tests/`
Contains all test scripts for application functionality:

- `comprehensive_test_suite.py` - Complete application test suite
- `test_conversation_creation.py` - Conversation management tests
- `test_csrf_debug.py` - CSRF protection tests
- `test_custom_agents_logfire.py` - Custom agent integration tests
- `test_delete_conversation.py` - Conversation deletion tests
- `test_logfire_integration.py` - Logfire monitoring tests
- `test_security_fixes.py` - Security feature tests
- `test_standard_agent.py` - Standard agent functionality tests
- `test_weaviate_connection.py` - Weaviate database connection tests

### 🛠️ `utils/`
Contains utility scripts for data processing and maintenance:

- `check_hjt_cells.py` - HJT cell data validation utility
- `remove_europe_entries.py` - Data cleaning utility for European entries

### 🚀 `deployment/`
Contains deployment and production configuration scripts:

- `deploy.ps1` - Windows PowerShell deployment script
- `deploy.sh` - Unix/Linux deployment script  
- `gunicorn.conf.py` - Gunicorn WSGI server configuration

## 🚀 Usage

### Running Tests
```bash
# Run comprehensive test suite
python scripts/tests/comprehensive_test_suite.py

# Run specific tests
python scripts/tests/test_security_fixes.py
python scripts/tests/test_weaviate_connection.py
```

### Using Utilities
```bash
# Check HJT cell data
python scripts/utils/check_hjt_cells.py

# Clean Europe data entries
python scripts/utils/remove_europe_entries.py
```

### Deployment
```bash
# Windows deployment
scripts/deployment/deploy.ps1

# Unix/Linux deployment  
bash scripts/deployment/deploy.sh
```

## 📝 Notes

- All test scripts include comprehensive logging and error reporting
- Utility scripts are designed to be run from the project root directory
- Deployment scripts handle both development and production environments
- See individual script headers for specific usage instructions