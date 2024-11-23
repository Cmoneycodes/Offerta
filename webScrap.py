import requests
from bs4 import BeautifulSoup
import json
from telegram import Bot
import asyncio
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Telegram Bot setup
BOT_TOKEN = "6789851954:AAFhh5WV_NbbINjnduOrtwJ16_8JQkbEwT8"
CHAT_ID = "-4551064532"
TRACK_FILE = "sent_proposals.json"
CHECK_INTERVAL = 300  # 5 minutes in seconds

async def scrape_latest_articles(url):
    try:
        logger.info(f"Fetching URL: {url}")
        response = requests.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        topic_rows = soup.find_all('tr', class_='topic-list-item')
        logger.info(f"Found {len(topic_rows)} topic rows.")
        
        articles = []
        seen_links = set()  # To prevent duplicate entries
        
        for idx, row in enumerate(topic_rows, start=1):
            logger.debug(f"Processing row {idx}.")
            title_element = row.find(class_='link-top-line')
            
            if title_element:
                title = title_element.text.strip()
                link_element = title_element.find('a')
                link = link_element['href'] if link_element else None
                
                if link:
                    full_link = f"https://gov.ethenafoundation.com{link}" if link.startswith('/') else link
                    
                    # Only add if we haven't seen this link before
                    if full_link not in seen_links:
                        seen_links.add(full_link)
                        articles.append({"title": title, "link": full_link})
                        logger.debug(f"Added: {title}")
        
        return articles
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching URL: {e}")
        return []

def load_sent_proposals():
    try:
        with open(TRACK_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_sent_proposals(sent_proposals):
    with open(TRACK_FILE, "w") as file:
        json.dump(sent_proposals, file, indent=2)

async def send_telegram_message(bot, message):
    try:
        await bot.send_message(
            chat_id=CHAT_ID,
            text=message,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        logger.info("Successfully sent message to Telegram")
    except Exception as e:
        logger.error(f"Error sending message to Telegram: {e}")

async def send_latest_proposal():
    url = "https://gov.ethenafoundation.com/latest"
    bot = Bot(token=BOT_TOKEN)
    
    # Scrape latest articles
    articles = await scrape_latest_articles(url)
    if not articles:
        logger.warning("No articles found.")
        return
    
    # Load sent proposals
    sent_proposals = load_sent_proposals()
    
    # Convert sent_proposals to set of links for efficient checking
    sent_links = {article['link'] for article in sent_proposals}
    
    # Check for new proposals
    new_proposals_found = False
    for article in articles:
        if article['link'] not in sent_links:
            message = (
                f"📢 *New Proposal*\n\n"
                f"*Title:* {article['title']}\n"
                f"🔗 [Read More]({article['link']})"
            )
            
            await send_telegram_message(bot, message)
            sent_proposals.append(article)
            new_proposals_found = True
            
            # Save after each new proposal is sent
            save_sent_proposals(sent_proposals)
            logger.info(f"Sent and saved new proposal: {article['title']}")
    
    if not new_proposals_found:
        logger.info("No new proposals to send.")

async def main():
    logger.info("Starting the bot...")
    try:
        while True:
            logger.info("Checking for new proposals...")
            await send_latest_proposal()
            logger.info(f"Waiting {CHECK_INTERVAL} seconds before next check...")
            await asyncio.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())