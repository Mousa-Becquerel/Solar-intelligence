@echo off
REM Update Poetry dependencies for refactored application

echo ================================================
echo Updating Poetry Dependencies
echo ================================================
echo.

echo Step 1: Updating poetry.lock...
poetry lock --no-update

echo.
echo Step 2: Installing dependencies...
poetry install

echo.
echo Step 3: Verifying NumPy version...
poetry run python -c "import numpy; print(f'NumPy version: {numpy.__version__}')"

echo.
echo Step 4: Verifying Pydantic version...
poetry run python -c "import pydantic; print(f'Pydantic version: {pydantic.__version__}')"

echo.
echo ================================================
echo Dependencies Updated Successfully!
echo ================================================
echo.
echo You can now run the integration tests:
echo   poetry run python test_refactored_integration.py
echo.
pause
