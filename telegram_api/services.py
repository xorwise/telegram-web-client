from telethon.sessions import StringSession
from telethon.sync import TelegramClient
from telegram_api.models import SearchRequest, ParsedRequest, TelegramSession
from telegram_api.models import Channel as DBChannel
from telethon.tl.types import PeerChannel, User, Chat, Channel
from telegramweb.settings import TELEGRAM_API_ID, TELEGRAM_API_HASH
from django.http import HttpRequest
from user.models import CustomUser
from asgiref.sync import sync_to_async
from user.services import get_user


async def get_telegram_session(phone: str) -> str:
    """ Get Telegram session from phone number """
    try:
        session = await sync_to_async(lambda: TelegramSession.objects.get(phone=phone), thread_sensitive=True)()
    except TelegramSession.DoesNotExist:
        return ''
    return session.session


async def get_active_session(session: str) -> str:
    """ Get telegram session by string session """
    ses = await TelegramSession.objects.aget(session=session)
    return ses.phone


async def create_telegram_session(phone: str, session: str):
    """ Create telegram session"""
    new_session = await TelegramSession.objects.aget_or_create(phone=phone)
    new_session[0].session = session
    await sync_to_async(lambda: new_session[0].save(), thread_sensitive=True)()
    return new_session[0]


async def get_dialog_choices(client: TelegramClient) -> tuple[tuple[int, str], ...]:
    """ Get dialog choices from Telegram account """
    dialogs = list(await client.get_dialogs())
    choices = list()
    for dialog in dialogs:
        if dialog.name != '':
            choices.append((dialog.entity.id, dialog.name))
    return tuple(sorted(choices, key=lambda x: x[1]))


async def parse_request(mode: bool, keys: list) -> list[str]:
    """ Get channels and groups id from request """
    response = list()
    if mode:
        for key in keys:
            if key.startswith('channel'):
                response.append(key[8:])
    else:
        for key in keys:
            if key.startswith('group'):
                response.append(key[6:])
    return response


async def search(client: TelegramClient, channels, keywords, groups) -> tuple[list[any], set[int], list[User | Chat |
                                                                                                        Channel]]:
    """ Search messages by keywords from channels """
    added_messages = set()
    messages = list()
    for channel in channels:
        try:
            entity = await client.get_entity(channel)
        except ValueError:
            entity = await client.get_entity(PeerChannel(channel))
        for keyword in keywords:
            async for message in client.iter_messages(entity=entity, search=keyword):
                messages.append(message)
                added_messages.add(message.id)
    new_groups = list()
    for group in groups:
        try:
            entity = await client.get_entity(int(group))
        except ValueError:
            entity = await client.get_entity(PeerChannel(int(group)))
        new_groups.append(entity)
    return messages[::-1], new_groups, added_messages


def create_request(phone: str, channels: list[str], keywords: list[str], user: CustomUser) -> SearchRequest:
    """ Create search request without messages"""
    request = SearchRequest.objects.create(client_phone=phone, channels=channels, keywords=keywords, user_id=user.id)
    return request


def create_channel(channel: User | Chat | Channel) -> DBChannel:
    """ Create Channel object """
    try:
        new_channel = DBChannel.objects.get(id=channel.id)
    except DBChannel.DoesNotExist:
        try:
            new_channel = DBChannel.objects.create(id=channel.id, title=channel.title)
        except AttributeError:
            new_channel = DBChannel.objects.create(id=channel.id, title=(
                '' if channel.first_name is None else channel.first_name + ' ' +
                                                      '' if channel.last_name is None else channel.last_name))
    return new_channel


def get_active_requests(loop) -> dict[str, list[SearchRequest]]:
    """ Get active search requests and parse them to dict with string session as a key"""
    requests = SearchRequest.objects.all().filter(is_active=True)
    new_requests = dict()
    for request in list(requests):
        session = loop.run_until_complete(get_telegram_session(request.client_phone))
        try:
            new_requests[session] += [request]
        except KeyError:
            new_requests[session] = [request]
    return new_requests


async def research(client: TelegramClient, channels: list[str], keywords: list[str], added_messages: set[int]) -> list:
    """ Research messages, check if new messages are added with particular keywords and from particular channels """
    new_messages = list()
    for channel in channels:
        entity = await client.get_entity(channel)
        for keyword in keywords:
            async for message in client.iter_messages(entity=entity, search=keyword):
                if message.id not in added_messages:
                    new_messages.append(message)
                else:
                    break
    return new_messages


async def forward_messages(client: TelegramClient, messages: list, groups: list[Channel]) -> None:
    """ Forward messages to groups """
    for group in groups:
        try:
            entity = await client.get_entity(group.id)
        except ValueError:
            entity = await client.get_entity(PeerChannel(group.id))
        for message in messages:
            await client.forward_messages(entity=entity, messages=message)


async def get_sorted_requests(user: CustomUser) -> list[SearchRequest]:
    """ Sort requests firstly by is_active and secondly by date (id) """
    active = await sync_to_async(
        lambda: SearchRequest.objects.all().filter(is_active=True, user=user).order_by('id').reverse(),
        thread_sensitive=True)()
    inactive = await sync_to_async(
        lambda: SearchRequest.objects.all().filter(is_active=False, user=user).order_by('id').reverse(),
        thread_sensitive=True)()
    return await sync_to_async(lambda: list(active) + list(inactive), thread_sensitive=True)()


async def parse_requests(requests: list[SearchRequest]) -> list[ParsedRequest]:
    """ Parse requests to ParsedRequest objects """
    new_requests = list()
    for request in requests:
        groups = await sync_to_async(lambda: list(request.groups.all()), thread_sensitive=True)()
        new_requests.append(ParsedRequest(request, groups))
    return new_requests


async def get_entity_name(client: TelegramClient, id: int):
    """ Get channel name from id"""
    try:
        entity = await client.get_entity(id)
    except ValueError:
        entity = await client.get_entity(PeerChannel(id))
    return entity.title


async def delete_request(id: int):
    """ Delete request object"""
    request = await sync_to_async(lambda: SearchRequest.objects.get(id=id), thread_sensitive=True)()
    await sync_to_async(lambda: request.delete(), thread_sensitive=True)()


# Need to be refactored
async def send_message(request: HttpRequest, phone: str, user: CustomUser) -> CustomUser:
    """ Function to send a code request to authorize to a telegram account """
    session = await get_telegram_session(phone)
    client = TelegramClient(StringSession(session), TELEGRAM_API_ID, TELEGRAM_API_HASH)
    await client.connect()
    me = await client.get_me()
    if not await client.is_user_authorized():
        print('test2')
        await client.send_code_request(request.session.get('phone'), force_sms=True)
        result = await client.send_code_request(request.session.get('phone'))
        await adjust_user_active_session(client, phone, request, result, user)
    elif str(me.phone) != phone.replace('+', ''):
        await client.send_code_request(phone, force_sms=True)
        result = await client.send_code_request(phone)
        await adjust_user_active_session(client, phone, request, result, user)
    return user


async def adjust_user_active_session(client, phone, request, result, user):
    """ Add new session to user and change active session """
    phone_hash = result.phone_code_hash
    request.session['phone_code_hash'] = phone_hash
    new_session = await create_telegram_session(phone, client.session.save())
    await sync_to_async(lambda: user.telegram_sessions.add(new_session), thread_sensitive=True)()
    if user.active_session == '':
        user.active_session = new_session.session


def research_queue(requests: dict, loop):
    """ Iterate over requests and research messages from each of them"""
    for session in requests.keys():
        client = TelegramClient(session=StringSession(session), api_id=TELEGRAM_API_ID,
                                api_hash=TELEGRAM_API_HASH)
        client.connect()

        for request in requests[session]:
            new_messages = loop.run_until_complete(
                research(client=client, channels=list(request.channels), keywords=request.keywords,
                         added_messages=request.added_messages))
            if (len(new_messages)) > 0:
                request.added_messages = request.added_messages + [msg.id for msg in new_messages]
                request.save()
            loop.run_until_complete(
                forward_messages(client=client, messages=new_messages, groups=list(request.groups.all())))


async def change_active_session(phone: str, email: str) -> None:
    """ Change active session for user """
    session = await get_telegram_session(phone)
    db_user = await get_user(email)
    db_user.active_session = session
    await sync_to_async(lambda: db_user.save(), thread_sensitive=True)()


async def get_numbers(email: str) -> list[str]:
    """ Get phone numbers from user sessions """
    db_user = await get_user(email)
    sessions = await sync_to_async(lambda: list(db_user.telegram_sessions.all()), thread_sensitive=True)()
    new_sessions = list()
    for session in sessions:
        new_sessions.append(session.phone)
    return new_sessions


async def get_number(session: str) -> str:
    """ Get phone number from session """
    session = await TelegramSession.objects.aget(session=session)
    return session.phone
