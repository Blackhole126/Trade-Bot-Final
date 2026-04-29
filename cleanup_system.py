#!/usr/bin/env python3
"""
System Cleanup Script - Removes duplicate, backup, and cache files
Industry-level maintenance script for production stability
"""
import os
import shutil
from pathlib import Path


def remove_pycache_dirs(base_path: Path):
    """Remove all __pycache__ directories recursively"""
    count = 0
    for pycache in base_path.rglob('__pycache__'):
        try:
            shutil.rmtree(pycache)
            count += 1
            print(f"✓ Removed: {pycache}")
        except Exception as e:
            # Skip venv __pycache__ - those belong to dependencies
            if '.venv' not in str(pycache) and 'site-packages' not in str(pycache):
                print(f"✗ Failed to remove {pycache}: {e}")
    print(f"\nRemoved {count} __pycache__ directories")


def remove_backup_files(base_path: Path):
    """Remove backup and temporary files"""
    patterns = ['*.backup', '*.bak', '*.tmp', '*~']
    count = 0
    for pattern in patterns:
        for filepath in base_path.glob(pattern):
            try:
                filepath.unlink()
                count += 1
                print(f"✓ Removed backup: {filepath}")
            except Exception as e:
                print(f"✗ Failed to remove {filepath}: {e}")
    print(f"\nRemoved {count} backup files")


def remove_duplicate_test_files(base_path: Path):
    """Remove duplicate test files from trade-bot-main"""
    test_dir = base_path / 'trade-bot-main'
    if not test_dir.exists():
        return

    files_to_remove = []

    # Test files that are duplicated
    test_patterns = [
        'test_*.py',
        'test_*.ts',
        'test_*.js',
        '*test*.bat'
    ]

    for pattern in test_patterns:
        for filepath in test_dir.glob(pattern):
            # Skip if it's the only copy
            root_level = list(base_path.glob(filepath.name))
            if len(root_level) > 0:
                # Root has same file, safe to remove from trade-bot-main
                files_to_remove.append(filepath)

    for filepath in set(files_to_remove):
        try:
            filepath.unlink()
            print(f"✓ Removed duplicate: {filepath}")
        except Exception as e:
            print(f"✗ Failed to remove {filepath}: {e}")


def main():
    base_path = Path(__file__).parent

    print("="*80)
    print("INDUSTRY-LEVEL SYSTEM CLEANUP")
    print("="*80)

    print("\n[1/3] Removing __pycache__ directories...")
    remove_pycache_dirs(base_path)

    print("\n[2/3] Removing backup files...")
    remove_backup_files(base_path)

    print("\n[3/3] Removing duplicate test files...")
    remove_duplicate_test_files(base_path)

    print("\n" + "="*80)
    print("CLEANUP COMPLETE")
    print("="*80)
    print("\nNext steps:")
    print("1. Run: python -m pytest backend/tests/ (if tests exist)")
    print("2. Verify no import errors: python -c 'import backend'")
    print("3. Check application starts normally")


if __name__ == '__main__':
    main()
