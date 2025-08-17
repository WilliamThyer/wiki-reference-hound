#!/usr/bin/env python3
"""
Simple test script to verify the library functionality works.
"""

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from wikipedia_dead_ref_finder import (
            WikipediaDeadLinkFinder,
            ProcessingConfig,
            LinkResult,
            ArticleResult,
            ProcessingSummary
        )
        print("✅ Core classes imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import core classes: {e}")
        return False
    
    try:
        from wikipedia_dead_ref_finder import (
            get_top_articles,
            get_all_time_top_articles,
            get_article_html,
            extract_external_links_from_references
        )
        print("✅ Utility functions imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import utility functions: {e}")
        return False
    
    return True


def test_config_creation():
    """Test that configuration objects can be created."""
    print("\nTesting configuration creation...")
    
    try:
        from wikipedia_dead_ref_finder import ProcessingConfig
        
        # Test default config
        config = ProcessingConfig()
        print(f"✅ Default config created: limit={config.limit}, timeout={config.timeout}")
        
        # Test custom config
        custom_config = ProcessingConfig(
            limit=10,
            timeout=15.0,
            parallel=False,
            verbose=True
        )
        print(f"✅ Custom config created: limit={custom_config.limit}, timeout={custom_config.timeout}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to create config: {e}")
        return False


def test_finder_creation():
    """Test that the main finder class can be created."""
    print("\nTesting finder creation...")
    
    try:
        from wikipedia_dead_ref_finder import WikipediaDeadLinkFinder, ProcessingConfig
        
        # Test with default config
        finder = WikipediaDeadLinkFinder()
        print("✅ Finder created with default config")
        
        # Test with custom config
        config = ProcessingConfig(limit=5, verbose=False)
        finder = WikipediaDeadLinkFinder(config)
        print("✅ Finder created with custom config")
        
        return True
    except Exception as e:
        print(f"❌ Failed to create finder: {e}")
        return False


def test_basic_functionality():
    """Test basic functionality without making network requests."""
    print("\nTesting basic functionality...")
    
    try:
        from wikipedia_dead_ref_finder import WikipediaDeadLinkFinder, ProcessingConfig
        
        # Create a finder with minimal settings
        config = ProcessingConfig(
            limit=1,
            browser_validation=False,
            verbose=False
        )
        finder = WikipediaDeadLinkFinder(config)
        
        # Test that the finder has the expected methods
        expected_methods = [
            'find_dead_links',
            'get_dead_links_only',
            'get_summary_stats',
            'export_to_csv'
        ]
        
        for method in expected_methods:
            if hasattr(finder, method):
                print(f"✅ Method {method} exists")
            else:
                print(f"❌ Method {method} missing")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Failed to test basic functionality: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Testing Wikipedia Dead Link Finder Library")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_config_creation,
        test_finder_creation,
        test_basic_functionality
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The library is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
