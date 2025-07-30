#!/usr/bin/env python3
"""
Setup script for browser validation dependencies.
"""

import subprocess
import sys
import os


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher is required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True


def install_selenium():
    """Install Selenium and webdriver-manager."""
    print("📦 Installing Selenium and webdriver-manager...")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "selenium", "webdriver-manager"
        ])
        print("✅ Selenium installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Selenium: {e}")
        return False


def check_chrome_installation():
    """Check if Chrome/Chromium is installed."""
    print("🔍 Checking for Chrome/Chromium installation...")
    
    # Common Chrome/Chromium paths
    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS
        "/usr/bin/google-chrome",  # Linux
        "/usr/bin/chromium-browser",  # Linux
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",  # Windows
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",  # Windows
    ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            print(f"✅ Chrome found at: {path}")
            return True
    
    print("⚠️  Chrome/Chromium not found in common locations")
    print("   Please install Chrome or Chromium manually:")
    print("   - macOS: Download from https://www.google.com/chrome/")
    print("   - Linux: sudo apt-get install google-chrome-stable")
    print("   - Windows: Download from https://www.google.com/chrome/")
    return False


def test_selenium_import():
    """Test if Selenium can be imported."""
    print("🧪 Testing Selenium import...")
    
    try:
        import selenium
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        print("✅ Selenium imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import Selenium: {e}")
        return False


def test_browser_validation():
    """Test browser validation with a simple URL."""
    print("🧪 Testing browser validation...")
    
    try:
        from browser_validation import BrowserValidator
        
        with BrowserValidator(headless=True, timeout=10) as validator:
            result = validator.validate_url_with_browser("https://httpstat.us/200")
            print(f"✅ Browser validation test successful: {result[1]}")
            return True
    except Exception as e:
        print(f"❌ Browser validation test failed: {e}")
        return False


def main():
    """Main setup function."""
    print("🔧 Browser Validation Setup")
    print("=" * 40)
    print()
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install Selenium
    if not install_selenium():
        return False
    
    # Test Selenium import
    if not test_selenium_import():
        return False
    
    # Check Chrome installation
    if not check_chrome_installation():
        print("\n⚠️  Please install Chrome/Chromium and run this script again")
        return False
    
    # Test browser validation
    if not test_browser_validation():
        print("\n❌ Browser validation test failed")
        print("   This might be due to:")
        print("   - Chrome/Chromium not installed")
        print("   - ChromeDriver not in PATH")
        print("   - System-specific issues")
        return False
    
    print("\n🎉 Browser validation setup complete!")
    print("   You can now use --browser-validation with your main script")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 