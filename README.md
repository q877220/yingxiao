# 云控助手 (YunKong Assistant)

A comprehensive Telegram marketing tool with automation capabilities.

## Features

### Core Features
- **Bulk Sending:** Send messages to all groups and channels at once, or with specified intervals
- **Message Customization:** Support for text and images to meet diverse marketing needs
- **Smart Scheduling:** Set messages to be sent at specific times for optimal reach
- **Feedback Tracking:** Real-time tracking of message sending status and effectiveness
- **User-Friendly Interface:** Simple and clear UI design

### Automation & Management Features
- **Keyword Group Joiner:** Automatically join groups based on keywords
- **User Scraping:** Scrape users from specified groups/channels
- **Bulk Invites:** Bulk invite users to groups
- **Bulk Private Messaging:** Send private messages to users in bulk
- **Automated Group Chatting:** Automatically send messages in group chats
- **Auto-Reply/Forwarding:** Automatically reply to messages or forward them
- **Automated Private Messaging:** Automatically initiate and handle private conversations
- **Marketing & Engagement:** Boost view counts, synchronize group member lists
- **Number & User Filtering:** Filter active phone numbers and usernames

### Account Management
- **Bulk Registration:** Register multiple Telegram accounts
- **Bulk Account Nurturing:** Keep multiple accounts online and active
- **Link/Message Scraping:** Scrape links or messages from channels
- **Member Management:** Comprehensive member management tools
- **Group Bot Management:** Manage group bots
- **Username Sniping:** Advanced username management
- **Change Phone Number:** Change phone numbers associated with accounts

## Installation

1. Clone the repository:
```bash
git clone https://github.com/q877220/yingxiao.git
cd yingxiao
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up configuration:
```bash
cp config.example.env .env
# Edit .env with your Telegram API credentials
```

4. Initialize the database:
```bash
python init_db.py
```

5. Run the application:
```bash
python app.py
```

6. Open your browser and navigate to `http://localhost:5000`

## Configuration

Create a `.env` file with the following variables:

```
# Telegram API Configuration
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_BOT_TOKEN=your_bot_token

# Database Configuration
DATABASE_URL=sqlite:///yunking_assistant.db

# Application Configuration
SECRET_KEY=your_secret_key
DEBUG=True
PORT=5000
```

## Usage

1. **Account Setup:** Add your Telegram accounts through the web interface
2. **Group Management:** Import groups and channels for bulk operations
3. **Message Creation:** Create and customize messages with text and media
4. **Scheduling:** Set up automated sending schedules
5. **Monitoring:** Track the performance of your marketing campaigns

## Project Structure

```
yingxiao/
├── app.py                 # Main Flask application
├── config.py              # Configuration management
├── init_db.py             # Database initialization
├── requirements.txt       # Python dependencies
├── models/                # Database models
├── services/              # Business logic services
├── templates/             # HTML templates
├── static/                # CSS, JS, images
├── migrations/            # Database migrations
└── utils/                 # Utility functions
```

## License

This project is for educational purposes only. Please ensure compliance with Telegram's Terms of Service and applicable laws when using automation tools.

## Disclaimer

This tool is designed for legitimate marketing purposes. Users are responsible for complying with Telegram's Terms of Service, applicable laws, and regulations. The developers do not endorse or encourage any misuse of this software.