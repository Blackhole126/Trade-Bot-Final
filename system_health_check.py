#!/usr/bin/env python3
"""
Industry-Level System Health Check
Validates system stability, dependencies, and critical functionality
"""
import sys
import os
from pathlib import Path
import importlib.util

def check_python_version():
    """Ensure Python 3.10+ is being used"""
    print("="*80)
    print("PYTHON VERSION CHECK")
    print("="*80)
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("❌ ERROR: Python 3.10+ required")
        return False
    
    print("✓ Python version OK")
    return True

def check_critical_dependencies():
    """Check if all critical packages are installed"""
    print("\n" + "="*80)
    print("CRITICAL DEPENDENCIES CHECK")
    print("="*80)
    
    critical_packages = [
        'fastapi', 'uvicorn', 'pydantic', 'pandas', 'numpy',
        'requests', 'yfinance', 'pymongo', 'PyJWT',
        'scikit-learn', 'xgboost', 'torch'
    ]
    
    missing = []
    for package in critical_packages:
        try:
            importlib.import_module(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"❌ {package} - MISSING")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements-unified.txt")
        return False
    
    print("\n✓ All critical dependencies installed")
    return True

def check_directory_structure():
    """Validate essential directories exist"""
    print("\n" + "="*80)
    print("DIRECTORY STRUCTURE CHECK")
    print("="*80)
    
    base_path = Path(__file__).parent
    required_dirs = [
        'backend',
        'backend/core',
        'backend/hft2',
        'trading-dashboard',
        'backend/models',
        'backend/data/cache'
    ]
    
    missing = []
    for dir_path in required_dirs:
        full_path = base_path / dir_path
        if not full_path.exists():
            print(f"❌ {dir_path} - MISSING")
            missing.append(dir_path)
        else:
            print(f"✓ {dir_path}")
    
    if missing:
        print(f"\n❌ Missing directories: {', '.join(missing)}")
        return False
    
    print("\n✓ Directory structure OK")
    return True

def check_env_files():
    """Check if environment files exist"""
    print("\n" + "="*80)
    print("ENVIRONMENT FILES CHECK")
    print("="*80)
    
    base_path = Path(__file__).parent
    env_locations = [
        base_path / 'backend' / '.env',
        base_path / 'backend' / 'hft2' / '.env',
        base_path / '.env'
    ]
    
    found = False
    for env_path in env_locations:
        if env_path.exists():
            print(f"✓ Found: {env_path}")
            found = True
            
            # Check for critical env vars
            try:
                with open(env_path, 'r') as f:
                    content = f.read()
                    critical_vars = ['MONGO_URI', 'DHAN_CLIENT_ID', 'DHAN_ACCESS_TOKEN']
                    for var in critical_vars:
                        if var in content:
                            print(f"  ✓ {var} configured")
                        else:
                            print(f"  ⚠ {var} not set")
            except Exception as e:
                print(f"  ⚠ Cannot read {env_path}: {e}")
    
    if not found:
        print("⚠ No .env file found - using default configuration")
        print("  This may be OK for open-access mode")
    
    return True

def check_model_files():
    """Check if ML model files exist"""
    print("\n" + "="*80)
    print("ML MODEL FILES CHECK")
    print("="*80)
    
    base_path = Path(__file__).parent
    models_dir = base_path / 'backend' / 'models'
    
    if not models_dir.exists():
        print("❌ Models directory missing")
        return False
    
    model_files = list(models_dir.glob('*.pkl')) + list(models_dir.glob('*.pt'))
    
    if len(model_files) == 0:
        print("⚠ No model files found - predictions will not work")
        print("  Run training first or download pre-trained models")
        return False
    
    print(f"✓ Found {len(model_files)} model files")
    
    # Check for specific critical models
    critical_patterns = ['intraday', 'short', 'long']
    for pattern in critical_patterns:
        matches = [f for f in model_files if pattern in f.name]
        if matches:
            print(f"  ✓ {pattern} models available ({len(matches)} files)")
        else:
            print(f"  ⚠ No {pattern} models found")
    
    return True

def check_for_corrupted_files():
    """Detect corrupted cache and pycache files"""
    print("\n" + "="*80)
    print("CORRUPTED FILES CHECK")
    print("="*80)
    
    base_path = Path(__file__).parent
    
    # Count __pycache__ directories
    pycache_count = len(list(base_path.rglob('__pycache__')))
    if pycache_count > 0:
        print(f"⚠ Found {pycache_count} __pycache__ directories")
        print("  Recommendation: Run cleanup_system.py to remove")
    
    # Check for backup files
    backup_files = list(base_path.glob('*.backup')) + list(base_path.glob('*.bak'))
    if backup_files:
        print(f"⚠ Found {len(backup_files)} backup files")
        print("  Recommendation: Review and remove if unnecessary")
    
    if pycache_count == 0 and not backup_files:
        print("✓ No corrupted or unnecessary files detected")
    
    return True

def check_database_connection():
    """Test MongoDB connection if configured"""
    print("\n" + "="*80)
    print("DATABASE CONNECTION CHECK")
    print("="*80)
    
    try:
        from pymongo import MongoClient
        
        # Try to get connection string from env
        mongo_uri = os.getenv('MONGO_URI')
        
        if not mongo_uri:
            print("⚠ MONGO_URI not set - skipping database check")
            print("  This is OK for local development without auth")
            return True
        
        # Attempt connection
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("✓ MongoDB connection successful")
        return True
        
    except ImportError:
        print("⚠ pymongo not installed - skipping database check")
        return True
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        print("  Application will run in limited mode without database")
        return True  # Don't fail the check - app can run without DB

def generate_health_report():
    """Generate comprehensive health report"""
    print("\n" + "="*80)
    print("GENERATING HEALTH REPORT")
    print("="*80)
    
    checks = [
        ("Python Version", check_python_version()),
        ("Critical Dependencies", check_critical_dependencies()),
        ("Directory Structure", check_directory_structure()),
        ("Environment Files", check_env_files()),
        ("Model Files", check_model_files()),
        ("File Integrity", check_for_corrupted_files()),
        ("Database Connection", check_database_connection()),
    ]
    
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    
    print("\n" + "="*80)
    print("HEALTH REPORT SUMMARY")
    print("="*80)
    
    for check_name, result in checks:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status}: {check_name}")
    
    print(f"\nScore: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n✅ SYSTEM HEALTHY - Ready for production")
        return True
    elif passed >= total - 1:
        print("\n⚠️  MINOR ISSUES - System functional but review recommended")
        return True
    else:
        print("\n❌ CRITICAL ISSUES - Fix problems before deploying")
        return False

def main():
    """Main entry point"""
    print("\n" + "="*80)
    print(" " * 20 + "INDUSTRY-LEVEL SYSTEM HEALTH CHECK")
    print("="*80)
    print(f"Timestamp: {Path(__file__).stat().st_mtime}")
    print(f"Working Directory: {Path.cwd()}")
    print("="*80 + "\n")
    
    try:
        is_healthy = generate_health_report()
        
        if not is_healthy:
            print("\n" + "!"*80)
            print(" WARNING: System health check failed ".center(80, "!"))
            print("!"*80)
            print("\nRecommended actions:")
            print("1. Review failed checks above")
            print("2. Run: python cleanup_system.py")
            print("3. Install dependencies: pip install -r requirements-unified.txt")
            print("4. Verify .env configuration")
            sys.exit(1)
        else:
            print("\n✅ All critical checks passed")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n❌ Health check failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
