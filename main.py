import json
import time
import random
import re
import sys
from urllib.parse import quote
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import html

from qwen_generator import generate_instagram_search_queries




class InstagramScraper:
    def __init__(self):
        self.driver = None

    def get_chrome_version(self):
        try:
            if sys.platform == 'win32':
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\\Google\\Chrome\\BLBeacon") as key:
                    version = winreg.QueryValueEx(key, "version")[0]
                    return version.split('.')[0]
        except Exception:
            return None

    def create_driver(self):
        self.safe_quit()
        options = uc.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--headless")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--blink-settings=imagesEnabled=false")
        prefs = {"profile.managed_default_content_settings.images": 2, "profile.managed_default_content_settings.javascript": 1}
        options.add_experimental_option("prefs", prefs)
        options = uc.ChromeOptions()
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        self.driver = uc.Chrome(options=options, headless=True)
        self.driver.set_page_load_timeout(30)

    def load_cookies(self, path):
        if not self.driver:
            self.create_driver()
        
        self.driver.get("https://www.instagram.com/")  # Must visit domain first

        with open(path, 'r') as file:
            cookies = json.load(file)

        for cookie in cookies:
            if ".instagram.com" not in cookie.get("domain", ""):
                continue
            try:
                # Only keep Selenium-compatible fields
                valid_cookie = {
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie.get('domain', '.instagram.com'),
                    'path': cookie.get('path', '/'),
                    'secure': cookie.get('secure', True),
                    'httpOnly': cookie.get('httpOnly', False),
                }

                # Convert expirationDate to expiry if present
                if 'expirationDate' in cookie:
                    valid_cookie['expiry'] = int(cookie['expirationDate'])

                self.driver.add_cookie(valid_cookie)
            except Exception as e:
                pass
                # print(f"⚠️ Failed to add cookie {cookie['name']}: {e}")


    def safe_quit(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                print(f"⚠️ Error during driver.quit(): {e}")
            finally:
                self.driver = None
                time.sleep(1)

    def google_search_instagram_profiles(self, location, query, max_results):
        # search_query = f'site:instagram.com "{query}" "{location}"'
        base_url = f"https://www.google.com/search?q={quote(query)}&tbm=nws"
        profile_urls = []
        page = 0

        self.create_driver()
        try:
            while len(profile_urls) < max_results and page < 10:
                url = f"{base_url}&start={page*10}&num=50"
                print(f"🔎 Searching {url} ...")
                self.driver.get(url)

                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a"))
                    )
                except TimeoutException:
                    print("⚠️ Google page load timeout.")
                    break

                anchors = self.driver.find_elements(By.CSS_SELECTOR, "a")
                before_count = len(profile_urls)

                print(f"🔍 Found {len(anchors)} on this page")
                if len(anchors) ==3:
                    print([a.get_attribute('href') for a in anchors])
                for a in anchors:
                    href = a.get_attribute("href")
                    if href and "instagram.com" in href:
                        href = href.split("?")[0]
                        match = re.search(r"https://www\.instagram\.com/([a-zA-Z0-9_.]+)/?", href)
                        if match:
                            username = match.group(1)
                            if username.lower() not in ("p", "reel", "tv", "stories", "explore"):
                                full_url = f"https://www.instagram.com/{username}/"
                                if full_url not in profile_urls:
                                    print(f"✅ Found profile: {username}")
                                    profile_urls.append(full_url)

                after_count = len(profile_urls)
                if after_count == before_count:
                    print("⛔ No new Instagram links found on this page. Stopping search.")
                    break  # No new links found, stop searching

                page += 1
                time.sleep(random.uniform(1, 2))
        except Exception as e:
            print(f"⚠️ Error during search: {e}")
            return []

        print(f"📦 Collected {len(profile_urls)} Instagram profile URLs.")
        return profile_urls[:max_results * 3]


    def scrape_instagram_bio(self, url):
        try:
            self.driver.get("https://www.instagram.com/")
            time.sleep(random.uniform(0.8, 1.2))
            self.load_cookies("cookies.json")
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(random.uniform(0.8, 1.2))
            if "login" in self.driver.current_url:
                print("🚫 Redirected to login page, skipping...")
                return 0, ""

            followers = 0
            bio = ""

            WebDriverWait(self.driver, 10).until(
    EC.presence_of_element_located((By.XPATH, '//meta[@name="description"]'))
)
            meta_tag = self.driver.find_element(By.XPATH, '//meta[@name="description"]')
            content = meta_tag.get_attribute("content")
            if content:
                followers = 0
                bio = ""

                match = re.search(r'([\d.,KMkm]+)\s+Followers', content)
                if match:
                        raw = match.group(1).upper().replace(",", "").strip()
                        if "K" in raw:
                            followers = int(float(raw.replace("K", "")) * 1_000)
                        elif "M" in raw:
                            followers = int(float(raw.replace("M", "")) * 1_000_000)
                        else:
                            followers = int(float(raw))

                if "on Instagram:" in content:
                    bio = content.split("on Instagram:")[-1].strip()

                    if bio.startswith('"') and bio.endswith('"'):
                        bio = bio[1:-1]


            return followers, bio

        except Exception as e:
            print(f"⚠️ Error scraping {url}: {e}")
            return 0, ""


    def find_top_accounts(self, location, query, count, queries):
        print(f"\n🚀 Starting search for {count} Instagram accounts in '{location}' about '{query}'")
        results = []
        for q in queries:
            profiles = self.google_search_instagram_profiles(location, q, count)
        
        # Ensure the driver is still alive
        if not self.driver:
            self.create_driver()

        try:
            for i, profile in enumerate(profiles, 1):
                print(f"🔍 Scraping profile {i}/{len(profiles)}: {profile}")
                followers, bio = self.scrape_instagram_bio(profile)

                if followers > 0 and bio:
                    username = profile.split("/")[-2] if profile.endswith("/") else profile.split("/")[-1]
                    results.append({
                        "username": username,
                        "follower_count": followers,
                        "bio": bio,
                        "profile_url": profile
                    })
                else:
                    continue
                if len(results) >= count:
                    break

                time.sleep(random.uniform(0.8, 1.2))

            results.sort(key=lambda x: x["follower_count"], reverse=True)

            filename = f"{count}_{location.lower().replace(' ', '_')}_{query.lower().replace(' ', '_')}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(results[:count], f, indent=2, ensure_ascii=False)

            print(f"\n✅ Completed: Found {len(results)} top profiles.")
            return results[:count]

        finally:
            self.safe_quit()


if __name__ == "__main__":
    scraper = InstagramScraper()

    location = input("Enter location (e.g., New York): ")
    query = input("Enter search topic (e.g., motorsport): ")
    count = int(input("Enter number of accounts to find (e.g., 10): "))

    try:
        print("🔍 generating appropriate queries with LLM ...")
        queries = generate_instagram_search_queries(topic=query, location=location)
        if len(queries):
            print("✔️ queries generated")
            results = scraper.find_top_accounts(location, query, count, queries)
            print("\n📊 Top Results:")
            for i, r in enumerate(results, 1):
                print(f"{i}. @{r['username']} - {r['follower_count']:,} followers")
                print(f"   URL: {r['profile_url']}")
                print(f"   Bio: {r['bio']}\n")

    except Exception as e:
        print(f"❌ Script failed: {str(e)}")
    finally:
        scraper.safe_quit()
        print("👋 Done.")
