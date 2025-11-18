#!/usr/bin/env python3
"""
Quick start script for Glade Contest Bot
Checks dependencies and launches the GUI
"""

import sys
import subprocess

def check_dependencies():
    """Check if all required packages are installed"""
    required = ['requests', 'bs4', 'PyQt6']
    missing = []
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    return missing

def install_dependencies():
    """Install missing dependencies"""
    print("Installing missing dependencies...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Dependencies installed successfully!")
        return True
    except:
        print("❌ Failed to install dependencies")
        return False

def main():
    print("🎮 Glade Contest Bot - Starting...\n")
    
    # Check dependencies
    missing = check_dependencies()
    
    if missing:
        print(f"⚠️  Missing dependencies: {', '.join(missing)}")
        response = input("Install missing dependencies? (y/n): ")
        
        if response.lower() == 'y':
            if not install_dependencies():
                print("\nPlease install manually: pip install -r requirements.txt")
                sys.exit(1)
        else:
            print("\nPlease install dependencies: pip install -r requirements.txt")
            sys.exit(1)
    
    print("✅ All dependencies installed")
    print("🚀 Launching GUI...\n")
    
    # Import and run GUI
    try:
        from gui_app import main as gui_main
        gui_main()
    except Exception as e:
        print(f"❌ Error launching GUI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
