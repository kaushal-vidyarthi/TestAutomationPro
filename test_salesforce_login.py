#!/usr/bin/env python3
"""
Test script for Salesforce Experience Cloud login functionality
Tests the enhanced login capabilities with user-provided credentials
"""

import sys
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import AppSettings
from crawler.site_crawler import SiteCrawler

async def test_salesforce_login():
    """Test the enhanced Salesforce login with provided credentials"""
    
    print("🧪 Testing AI Test Automation Tool - Salesforce Login")
    print("=" * 60)
    
    # Initialize settings with test credentials
    settings = AppSettings()
    
    # Display configuration
    print(f"\n📋 Configuration:")
    print(f"   Login URL: {settings.SF_LOGIN_URL}")
    print(f"   Username: {settings.SF_USERNAME}")
    print(f"   Password: {'*' * len(settings.SF_PASSWORD)}")
    print(f"   Timeout: {settings.CRAWLER_TIMEOUT}s")
    print(f"   Headless: {settings.CRAWLER_HEADLESS}")
    
    # Initialize crawler
    crawler_config = settings.get_crawler_config()
    salesforce_config = settings.get_salesforce_config()
    
    # Set crawler to visible mode for debugging
    crawler_config['headless'] = False
    crawler_config['timeout'] = 60  # Increased timeout
    
    crawler = SiteCrawler(crawler_config)
    
    try:
        print(f"\n🚀 Starting crawler test...")
        
        def progress_callback(current, total, message):
            percent = (current / total) * 100
            print(f"   [{current:3d}%] {message}")
        
        # Attempt to crawl the Salesforce site
        results = await crawler._crawl_salesforce_site_async(salesforce_config, progress_callback)
        
        print(f"\n✅ Crawl Results:")
        print(f"   Pages crawled: {len(results.get('pages', []))}")
        print(f"   Failed pages: {len(results.get('failed_pages', []))}")
        print(f"   Total execution time: {results.get('execution_time', 0):.2f}s")
        
        # Display page summaries
        if results.get('pages'):
            print(f"\n📄 Crawled Pages:")
            for i, page in enumerate(results['pages'][:5], 1):  # Show first 5
                print(f"   {i}. {page.get('title', 'Untitled')} - {page.get('url', '')}")
                print(f"      Elements: {len(page.get('elements', []))}")
                print(f"      Access: {page.get('access_type', 'authenticated')}")
        
        # Display any errors
        if results.get('failed_pages'):
            print(f"\n❌ Failed Pages:")
            for i, error in enumerate(results['failed_pages'][:3], 1):  # Show first 3
                print(f"   {i}. {error.get('url', 'Unknown URL')}")
                print(f"      Error: {error.get('error', 'Unknown error')}")
        
        print(f"\n🎉 Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        print(f"\n🔍 Troubleshooting:")
        print(f"   1. Check if the login URL is accessible")
        print(f"   2. Verify username and password are correct")
        print(f"   3. Ensure the site allows automated logins")
        print(f"   4. Check if MFA or additional verification is required")
        return False

async def test_login_detection():
    """Test the smart login detection functionality"""
    
    print(f"\n🔍 Testing Login Detection...")
    
    settings = AppSettings()
    crawler_config = settings.get_crawler_config()
    crawler_config['headless'] = True  # Run headless for detection test
    
    crawler = SiteCrawler(crawler_config)
    
    try:
        await crawler.initialize_browser()
        
        # Test login detection
        login_required = await crawler.detect_login_requirement(settings.SF_LOGIN_URL)
        
        print(f"   Login detection result: {'Required' if login_required else 'Not required'}")
        
        # Test base URL extraction
        base_url = crawler.extract_base_url(settings.SF_LOGIN_URL)
        print(f"   Base URL extracted: {base_url}")
        
        # Test public page discovery
        print(f"   Discovering public pages...")
        public_urls = await crawler.discover_public_pages(base_url)
        
        if public_urls:
            print(f"   Found {len(public_urls)} public pages:")
            for url in public_urls[:3]:  # Show first 3
                print(f"     - {url}")
        else:
            print(f"   No public pages found")
        
        await crawler.close()
        return True
        
    except Exception as e:
        print(f"   Detection test failed: {e}")
        if hasattr(crawler, 'browser') and crawler.browser:
            await crawler.close()
        return False

async def main():
    """Main test function"""
    print("Starting comprehensive Salesforce login tests...\n")
    
    # Test 1: Login detection and public page discovery
    detection_result = await test_login_detection()
    
    # Test 2: Full login and crawling
    login_result = await test_salesforce_login()
    
    print(f"\n" + "=" * 60)
    print(f"🏁 Test Results Summary:")
    print(f"   Login Detection: {'✅ PASSED' if detection_result else '❌ FAILED'}")
    print(f"   Salesforce Login: {'✅ PASSED' if login_result else '❌ FAILED'}")
    
    if detection_result and login_result:
        print(f"\n🎉 All tests passed! The enhanced login system is working correctly.")
    elif detection_result:
        print(f"\n⚠️  Login detection works, but Salesforce authentication needs attention.")
        print(f"   This could be due to:")
        print(f"   - Invalid credentials")
        print(f"   - Site security restrictions")
        print(f"   - Network connectivity issues")
    else:
        print(f"\n❌ Tests failed. Check the configuration and try again.")
    
    print(f"\n💡 Next Steps:")
    print(f"   1. Run the main application: python main.py")
    print(f"   2. Configure crawler settings in the GUI")
    print(f"   3. Test with your specific Salesforce site")
    print(f"   4. Review generated test cases")

if __name__ == "__main__":
    asyncio.run(main())