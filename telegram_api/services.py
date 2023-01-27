from telethon.sessions import StringSession
from telethon.sync import TelegramClient
from telegram_api.models import SearchRequest, ParsedRequest, TelegramSession
from telegram_api.models import Channel as DBChannel
from telethon.tl.types import PeerChannel, User, Chat, Channel
from telegramweb.settings import TELEGRAM_API_ID, TELEGRAM_API_HASH
from django.http import HttpRequest
from user.models import CustomUser
from asgiref.sync import sync_to_async


async def get_telegram_session(phone: str) -> str:
    try:
        session = await sync_to_async(lambda: TelegramSession.objects.get(phone=phone), thread_sensitive=True)()
    except TelegramSession.DoesNotExist:
        return ''
    return session.session


async def tuple_to_session(t: tuple) -> TelegramSession:
    return TelegramSession(t)


async def get_active_session(session: str) -> str:
    ses = await TelegramSession.objects.aget(session=session)
    return ses.phone


async def create_telegram_session(phone: str, session: str):
    new_session = await TelegramSession.objects.aget_or_create(phone=phone)
    new_session[0].session = session
    await sync_to_async(lambda: new_session[0].save(), thread_sensitive=True)()
    return new_session[0]


async def get_dialog_choices(client: TelegramClient) -> tuple[tuple[any, any], ...]:
    dialogs = list(await client.get_dialogs())
    choices = list()
    for dialog in dialogs:
        if dialog.name != '':
            choices.append((dialog.entity.id, dialog.name))
    return tuple(sorted(choices, key=lambda x: x[1]))


async def parse_request(mode: bool, keys: list) -> list:
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


async def search(client: TelegramClient, channels, keywords, groups) -> tuple[
    list[any], list[User | Chat | Channel], set[int]]:
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


def create_request(session: str, channels: list[str], keywords: list[str], user: CustomUser) -> SearchRequest:
    request = SearchRequest.objects.create(client=session, channels=channels, keywords=keywords, user_id=user.id)
    return request


def create_channel(channel: User | Chat | Channel) -> DBChannel:
    try:
        new_channel = DBChannel.objects.get(id=channel.id)
    except DBChannel.DoesNotExist:
        try:
            new_channel = DBChannel.objects.create(id=channel.id, title=channel.title)
        except AttributeError:
            new_channel = DBChannel.objects.create(id=channel.id, title=(
                '' if channel.first_name is None else channel.first_name + ' ' + '' if channel.last_name is None else channel.last_name))
    return new_channel


async def get_client_id(client: TelegramClient) -> int:
    info = await client.get_me()
    return info.id


def get_active_requests() -> dict[SearchRequest]:
    requests = SearchRequest.objects.all().filter(is_active=True)
    new_requests = dict()
    for request in requests:
        try:
            new_requests[request.client] += [request]
        except KeyError:
            new_requests[request.client] = [request]
    return new_requests


async def research(client: TelegramClient, channels: list[str], keywords: list[str], added_messages: set[int]) -> list:
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
    for group in groups:
        try:
            entity = await client.get_entity(group.id)
        except ValueError:
            entity = await client.get_entity(PeerChannel(group.id))
        for message in messages:
            await client.forward_messages(entity=entity, messages=message)


async def get_sorted_requests(user: CustomUser) -> list[SearchRequest]:
    active = await sync_to_async(lambda: SearchRequest.objects.all().filter(is_active=True, user=user).order_by('id').reverse(),
                                 thread_sensitive=True)()
    inactive = await sync_to_async(lambda: SearchRequest.objects.all().filter(is_active=False, user=user).order_by('id').reverse(),
                                   thread_sensitive=True)()
    return await sync_to_async(lambda: list(active) + list(inactive), thread_sensitive=True)()


async def parse_requests(requests: list[SearchRequest]) -> list[ParsedRequest]:
    new_requests = list()
    for request in requests:
        groups = await sync_to_async(lambda: list(request.groups.all()), thread_sensitive=True)()
        new_requests.append(ParsedRequest(request, groups))
    return new_requests


async def get_entity_name(client: TelegramClient, id: int):
    try:
        entity = await client.get_entity(id)
    except ValueError:
        entity = await client.get_entity(PeerChannel(id))
    return entity.title


async def delete_request(id: int):
    request = await sync_to_async(lambda: SearchRequest.objects.get(id=id), thread_sensitive=True)()
    await sync_to_async(lambda: request.delete(), thread_sensitive=True)()


async def send_message(request: HttpRequest, phone: str, user: CustomUser) -> CustomUser:
    session = await get_telegram_session(phone)
    client = TelegramClient(StringSession(session), TELEGRAM_API_ID, TELEGRAM_API_HASH)
    await client.connect()
    me = await client.get_me()
    if not await client.is_user_authorized():
        print('test2')
        await client.send_code_request(request.session.get('phone'), force_sms=True)
        result = await client.send_code_request(request.session.get('phone'))
        phone_hash = result.phone_code_hash
        request.session['phone_code_hash'] = phone_hash
        new_session = await create_telegram_session(phone, client.session.save())
        await sync_to_async(lambda: user.telegram_sessions.add(new_session), thread_sensitive=True)()
        if user.active_session == '':
            user.active_session = new_session.session
    elif str(me.phone) != phone.replace('+', ''):
        await client.send_code_request(phone, force_sms=True)
        result = await client.send_code_request(phone)
        phone_hash = result.phone_code_hash
        request.session['phone_code_hash'] = phone_hash
        new_session = await create_telegram_session(phone, client.session.save())
        await sync_to_async(lambda: user.telegram_sessions.add(new_session), thread_sensitive=True)()
        if user.active_session == '':
            user.active_session = new_session.session
    return user


def research_queue(requests: dict, loop):
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
