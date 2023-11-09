# Telegram Web Client

Welcome to the Telegram Web Client, a powerful tool built with Python, Django, Celery, and PostgreSQL. This web client not only supports Telegram authorization but also offers a range of features to enhance your Telegram experience.

## Features

### 1. Messages Search and Forwarding
Effortlessly search through selected Telegram channels with multiple search options. Once you've found the messages you're looking for, easily forward them to your selected channels. The client also supports scheduled mailing, allowing you to plan your message forwarding in advance.

### 2. Mailing Service with Markdown Editor
Enjoy a seamless mailing experience with our integrated Markdown editor. Craft visually appealing and formatted messages effortlessly. The client's mailing service lets you send messages at your convenience, and the scheduling feature ensures your messages are delivered precisely when you want them to be.

## Tech Stack

- **Python**: The backbone of the project, ensuring robust and efficient functionality.
- **Django**: Empowering the web client with a flexible and scalable web framework.
- **Celery**: Enhancing performance through asynchronous task execution.
- **PostgreSQL**: Providing a reliable and powerful database to store and manage your data.
- **Telethon**: Enabling seamless integration with the Telegram API.

## Getting Started

To get started with the Telegram Web Client, follow these simple steps:

1. Clone the repository: `git clone https://github.com/xorwise/telegram-web-client.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Configure your Telegram API credentials in the settings.
4. Run migrations: `python manage.py migrate`
5. Start the development server: `python manage.py runserver`
