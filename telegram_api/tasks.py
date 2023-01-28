from user.models import CustomUser
from user.services import get_user
from telegramweb import celery_app
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telegramweb.settings import TELEGRAM_API_ID, TELEGRAM_API_HASH, SUPERUSER_USERNAME
import asyncio
from telegram_api import services
from telegramweb.services import get_async_loop


@celery_app.task()
def messages_search(session: str, channels: list[str],  keywords: list[str], groups: list[str], email: str):
    loop = get_async_loop()
    user = loop.run_until_complete(get_user(email))
    client = TelegramClient(session=StringSession(session), api_id=TELEGRAM_API_ID, api_hash=TELEGRAM_API_HASH)
    client.connect()

    request = services.create_request(session, channels, keywords, user)
    messages, new_groups, added_messages = loop.run_until_complete(services.search(client, channels, keywords, groups))
    request.added_messages = list(added_messages)
    for group in list(new_groups):
        print(group)
        new_group = services.create_channel(group)
        request.groups.add(new_group)

    request.save()
    print(f'{len(messages)} was found...')
    loop.run_until_complete(services.forward_messages(client=client, messages=messages, groups=new_groups))


@celery_app.task()
def research_queue():
    requests = services.get_active_requests()
    loop = get_async_loop()
    services.research_queue(requests, loop)

