#!/usr/bin/env python3
"""Test script to validate the notifications service"""

import ast
import sys

def check_syntax(filename):
    """Check Python syntax of a file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
        
        ast.parse(source)
        print(f"✅ {filename}: Syntax OK")
        return True
    except SyntaxError as e:
        print(f"❌ {filename}: Syntax Error - {e}")
        return False
    except Exception as e:
        print(f"❌ {filename}: Error - {e}")
        return False

# Check all modified files
files_to_check = [
    'app/services/notifications.py',
    'app/handlers/user/orders.py',
    'app/handlers/user/faq.py',
    'app/handlers/admin/admin_panel.py'
]

all_ok = True
for file in files_to_check:
    if not check_syntax(file):
        all_ok = False

if all_ok:
    print("\n🎉 All files passed syntax check!")
else:
    print("\n💥 Some files have syntax errors!")
    sys.exit(1)
