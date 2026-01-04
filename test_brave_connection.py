import os
import sys

# Add the backend directory to sys.path so we can import app
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from dotenv import load_dotenv
load_dotenv()

from app.services.brave_search import brave_web_search, brave_news_search

def test_brave():
    key = os.getenv("BRAVE_SEARCH_API_KEY")
    print(f"Brave API Key found: {'Yes' if key else 'No'}")
    if not key:
        print("❌ Please set BRAVE_SEARCH_API_KEY in your .env file")
        return

    print("\n--- Testing Web Search ('Apples') ---")
    try:
        results = brave_web_search("Apples", count=3)
        print(f"✅ Found {len(results)} results")
        for i, r in enumerate(results):
            print(f"  {i+1}. {r['title']} ({r['url']})")
    except Exception as e:
        print(f"❌ Web search failed: {e}")

    print("\n--- Testing News Search ('Technology') ---")
    try:
        results = brave_news_search("Technology", count=3)
        print(f"✅ Found {len(results)} results")
        for i, r in enumerate(results):
            print(f"  {i+1}. {r['title']} ({r['source']})")
    except Exception as e:
        print(f"❌ News search failed: {e}")

if __name__ == "__main__":
    test_brave()
