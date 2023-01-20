from user.services import get_user
from telegramweb import celery_app
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telegramweb.settings import TELEGRAM_API_ID, TELEGRAM_API_HASH, SUPERUSER_USERNAME
import asyncio
from telegram_api import services
import nest_asyncio


@celery_app.task()
def messages_search(session: str, channels: list[str],  keywords: list[str], groups: list[str]):
    nest_asyncio.apply()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    client = TelegramClient(session=StringSession(session), api_id=TELEGRAM_API_ID, api_hash=TELEGRAM_API_HASH)
    client.connect()

    client_id = loop.run_until_complete(services.get_client_id(client))
    request = services.create_request(client_id, channels, keywords)
    messages, new_groups, added_messages = loop.run_until_complete(services.search(client, channels, keywords, groups))
    request.added_messages = added_messages
    for group in list(new_groups):
        print(group)
        new_group = services.create_channel(group)
        request.groups.add(new_group)

    request.save()
    loop.run_until_complete(services.forward_messages(client=client, messages=messages, groups=new_groups))


@celery_app.task()
def research_queue():
    requests = services.get_active_requests()
    user = get_user(SUPERUSER_USERNAME)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    client = TelegramClient(session=StringSession(user.telegram_session), api_id=TELEGRAM_API_ID, api_hash=TELEGRAM_API_HASH)
    client.connect()

    for request in requests:
        new_messages = loop.run_until_complete(services.research(client=client, channels=list(request.channels), keywords=request.keywords, added_messages=request.added_messages))
        if(len(new_messages)) > 0:
            request.added_messages = request.added_messages + [msg.id for msg in new_messages]
            request.save()
        loop.run_until_complete(services.forward_messages(client=client, messages=new_messages, groups=list(request.groups.all())))
