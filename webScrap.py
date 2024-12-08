import requests
from bs4 import BeautifulSoup
import logging
import json
from telegram import Bot
import asyncio
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Telegram Bot setup
BOT_TOKEN = "6789851954:AAFhh5WV_NbbINjnduOrtwJ16_8JQkbEwT8"
CHAT_ID = "-1002003404373"
TRACK_FILE = "sent_articles.json"
WAIT_TIME = 24 * 60 * 60  # Default: 24 hours
MESSAGE_DELAY = 5  # Delay between messages in seconds

def escape_markdown(text):
    """Escape special characters for Telegram Markdown."""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in text)

def load_sent_articles():
    """Load sent articles from the tracking file."""
    try:
        with open(TRACK_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_sent_articles(sent_articles):
    """Save sent articles to the tracking file."""
    with open(TRACK_FILE, "w") as file:
        json.dump(sent_articles, file, indent=2)

async def send_telegram_message(bot, message, retries=3):
    """Send a message to Telegram with retry logic."""
    for attempt in range(retries):
        try:
            await bot.send_message(
                chat_id=CHAT_ID,
                text=message,
                parse_mode="MarkdownV2",  # Changed to MarkdownV2 for better compatibility
                disable_web_page_preview=True
            )
            logger.info("Successfully sent message to Telegram.")
            return True
        except Exception as e:
            logger.error(f"Attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(2)  # Wait before retrying
            continue
    return False

def scrape_latest_articles(url):
    """Scrape the latest articles from the given URL."""
    try:
        logger.info(f"Fetching URL: {url}")
        response = requests.get(url)
        response.raise_for_status()
        logger.info("Successfully fetched the webpage.")

        soup = BeautifulSoup(response.text, 'html.parser')
        logger.info("Successfully parsed the webpage content.")

        topic_rows = soup.find_all('tr', class_='topic-list-item')
        logger.info(f"Found {len(topic_rows)} topic rows.")

        articles = []
        base_url = url.split('/latest')[0]

        for row in topic_rows:
            title_element = row.find(class_='link-top-line')
            if title_element:
                title = title_element.text.strip()
                link_element = title_element.find('a')
                link = link_element['href'] if link_element else "No link found"
                full_link = f"{base_url}{link}" if link.startswith('/') else link
                articles.append({"title": title, "link": full_link})
                logger.info(f"Found title: {title}, Link: {full_link}")

        return articles
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching URL: {e}")
        return []

async def scrape_and_notify(bot, websites):
    """Scrape articles from multiple websites and send new ones via Telegram."""
    sent_articles = load_sent_articles()

    for site in websites:
        logger.info(f"Scraping site: {site}")
        articles = scrape_latest_articles(site)

        if site not in sent_articles:
            sent_articles[site] = []

        new_articles = [a for a in articles if a["link"] not in sent_articles[site]]
        logger.info(f"Found {len(new_articles)} new articles for {site}.")

        for article in new_articles:
            safe_title = escape_markdown(article["title"])
            main_name = site.split("//")[1].split(".")[0].capitalize()
            message = (
                f"📢 *New {main_name} Proposal*\n\n"
                f"*Title:* {safe_title}\n"
                f"[Read More]({article['link']})"
            )
            
            success = await send_telegram_message(bot, message)
            if success:
                sent_articles[site].append(article["link"])
                save_sent_articles(sent_articles)  # Save after each successful send
                await asyncio.sleep(MESSAGE_DELAY)
            else:
                logger.error(f"Failed to send article: {safe_title}")

        logger.info(f"Processed {len(new_articles)} articles for {site}.")

async def main():
    """Main function to repeatedly scrape and notify."""
    websites = [
        "https://gov.ethenafoundation.com/latest",
        "https://forum.arbitrum.foundation/latest",
        "https://gov.uniswap.org/latest",
        "https://governance.aave.com/latest",
        "https://forum.avax.network/latest",
        "https://www.comp.xyz/latest",
        "https://gov.curve.fi/latest"
    ]

    while True:
        try:
            bot = Bot(token=BOT_TOKEN)
            logger.info("Starting scrape-and-notify cycle...")
            await scrape_and_notify(bot, websites)
            logger.info(f"Waiting {WAIT_TIME} seconds before the next cycle...")
            await asyncio.sleep(WAIT_TIME)
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            await asyncio.sleep(60)  # Wait a minute before retrying if there's an error

if __name__ == "__main__":
    asyncio.run(main())
