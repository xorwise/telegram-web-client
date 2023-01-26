from telethon.sessions import StringSession
from telethon.sync import TelegramClient
from telegram_api.models import SearchRequest, ParsedRequest
from telegram_api.models import Channel as DBChannel
from telethon.tl.types import PeerChannel, User, Chat, Channel
from telegramweb.settings import TELEGRAM_API_ID, TELEGRAM_API_HASH
from django.http import HttpRequest
from user.models import CustomUser



async def is_telegram_authorized(client: TelegramClient) -> bool:
    await client.connect()
    return await client.is_user_authorized()


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


async def search(client: TelegramClient, channels, keywords, groups) -> tuple[list[any], list[User | Chat | Channel], set[int]]:
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


def create_request(client_id, channels: list[str], keywords: list[str]) -> SearchRequest:
    request = SearchRequest.objects.create(client=client_id, channels=channels, keywords=keywords)
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


def get_active_requests() -> list[SearchRequest]:
    return SearchRequest.objects.all().filter(is_active=True)


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


def get_sorted_requests() -> list[SearchRequest]:
    active = SearchRequest.objects.all().filter(is_active=True).order_by('id').reverse()
    inactive = SearchRequest.objects.all().filter(is_active=False).order_by('id').reverse()
    return list(active) + list(inactive)


def parse_requests(requests: list[SearchRequest]) -> list[ParsedRequest]:
    new_requests = list()
    for request in requests:
        new_requests.append(ParsedRequest(request))
    return new_requests


async def get_entity_name(client: TelegramClient, id: int):
    try:
        entity = await client.get_entity(id)
    except ValueError:
        entity = await client.get_entity(PeerChannel(id))
    return entity.title


def delete_request(id: int):
    request = SearchRequest.objects.get(id=id)
    request.delete()


async def send_message(request: HttpRequest, phone: str, user: CustomUser) -> CustomUser:
    client = TelegramClient(StringSession(user.telegram_session), TELEGRAM_API_ID, TELEGRAM_API_HASH)
    await client.connect()
    me = await client.get_me()
    if not await client.is_user_authorized():
        print('test2')
        await client.send_code_request(request.session.get('phone'), force_sms=True)
        result = await client.send_code_request(request.session.get('phone'))
        phone_hash = result.phone_code_hash
        request.session['phone_code_hash'] = phone_hash
        print(user.telegram_session)
        user.telegram_session = client.session.save()
        return user
    elif str(me.phone) != phone.replace('+', ''):
        await client.send_code_request(phone, force_sms=True)
        result = await client.send_code_request(phone)
        phone_hash = result.phone_code_hash
        request.session['phone_code_hash'] = phone_hash
        user.telegram_session = client.session.save()
        return user
    return user
