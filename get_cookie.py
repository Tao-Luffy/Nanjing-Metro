from selenium import webdriver
from selenium.webdriver.edge.options import Options
import json
import time
import os


class WeiboLogin:
    def __init__(self):
        self.driver = None

    def init_driver(self):
        """Initialize Edge browser"""
        try:
            edge_options = Options()
            edge_options.add_argument('--start-maximized')

            # Fixed user data directory: will be reused after first login
            profile_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "edge_profile_weibo"))
            edge_options.add_argument(rf'--user-data-dir={profile_dir}')

            # Optional stability parameters
            edge_options.add_argument('--no-first-run')
            edge_options.add_argument('--no-default-browser-check')

            print("Starting Edge browser...")
            self.driver = webdriver.Edge(options=edge_options)

            # Hide webdriver features
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            })

            print("✓ Browser started successfully!\n")
            return True
        except Exception as e:
            print(f"Failed to start browser: {e}")
            return False

    def manual_login(self):
        """Manually log in to Weibo"""
        print("=" * 60)
        print("   Please log in manually in the browser")
        print("=" * 60)
        print("\nSteps:")
        print("1. Enter your username and password in the opened browser")
        print("2. Complete any CAPTCHA or slider verification (if required)")
        print("3. Click the login button")
        print("4. After confirming successful login, return to this window")
        print("=" * 60 + "\n")

        # Open Weibo login page
        self.driver.get('https://weibo.com')
        time.sleep(2)
        self.driver.get('https://weibo.com')
        time.sleep(2)

        # Skip if already logged in
        if 'login' not in self.driver.current_url.lower():
            print("\n✓ Login state detected, skipping manual login\n")
            return True

        # Wait for user to manually log in
        input("Press Enter after completing login...")

        # Verify login success
        current_url = self.driver.current_url
        page_title = self.driver.title

        if 'login' not in current_url.lower() and 'weibo' in current_url:
            print(f"\n✓ Login successful! Current page: {page_title}\n")
            return True
        else:
            print("\nLogin does not appear to be successful")
            retry = input("Retry? (y/n): ")
            if retry.lower() == 'y':
                return self.manual_login()
            return False

    def get_cookies(self):
        """Retrieve and save Cookies"""
        try:
            print("=" * 60)
            print("Retrieving Cookies...")
            print("=" * 60 + "\n")

            # Get all Cookies
            cookies = self.driver.get_cookies()

            if not cookies:
                print("No Cookies retrieved")
                return None

            print(f"✓ Successfully retrieved {len(cookies)} Cookies\n")

            # Display Cookie list
            print("Cookie list:")
            for i, cookie in enumerate(cookies, 1):
                name = cookie.get('name', '')
                value = cookie.get('value', '')[:50]  # Show only first 50 characters
                print(f"  {i}. {name}: {value}...")
            print()

            # Save as JSON format
            with open('weibo_cookies.json', 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            print("✓ Cookies saved to: weibo_cookies.json")

            # Save as string format
            cookie_list = [f"{c['name']}={c['value']}" for c in cookies]
            cookie_string = '; '.join(cookie_list)

            with open('weibo_cookies.txt', 'w', encoding='utf-8') as f:
                f.write(cookie_string)
            print("✓ Cookie string saved to: weibo_cookies.txt")

            # Display prompt in browser
            js_code = f'alert("Successfully retrieved {len(cookies)} Cookies!\\n\\nSaved to local files")'
            self.driver.execute_script(js_code)
            time.sleep(2)

            try:
                self.driver.switch_to.alert.accept()
            except:
                pass

            # Print Cookie string preview
            print("\n" + "=" * 60)
            print("Cookie string preview (first 200 characters):")
            print("=" * 60)
            print(cookie_string[:200] + "...")
            print("=" * 60 + "\n")

            return cookie_string

        except Exception as e:
            print(f"Failed to retrieve Cookies: {e}")
            return None

    def close(self):
        """Close browser"""
        if self.driver:
            print("Closing browser...")
            self.driver.quit()
            print("✓ Browser closed\n")


def main():
    print("\n" + "=" * 60)
    print("")
    print("=" * 60 + "\n")

    weibo = WeiboLogin()

    try:
        # Initialize browser
        if not weibo.init_driver():
            print("Initialization failed, exiting program")
            return

        # Manual login
        if not weibo.manual_login():
            print("\nLogin failed, exiting program")
            return

        # Retrieve Cookies
        cookies = weibo.get_cookies()

        if cookies:
            print("=" * 60)
            print("   ✓ All operations completed!")
            print("=" * 60)
            print("\nCookie files saved to:")
            print("  • weibo_cookies.json (JSON format)")
            print("  • weibo_cookies.txt  (String format)")
            print("\nYou can use these Cookie files in other programs\n")

        # input("Press Enter to close browser...")

    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user")
    except Exception as e:
        print(f"\nProgram exception: {e}")
    finally:
        weibo.close()


# Test update


if __name__ == '__main__':
    main()
