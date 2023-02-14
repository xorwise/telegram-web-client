import asyncio
import os.path
from typing import Any
from datetime import datetime, date, timedelta
from telethon.sessions import StringSession
from telethon.sync import TelegramClient
from telegram_api.models import SearchRequest, ParsedRequest, TelegramSession, MailingRequest, ParsedMailing
from telegram_api.models import File as DBFile
from telegram_api.models import Channel as DBChannel
from telethon.tl.types import PeerChannel, User, Chat, Channel
from telegramweb.settings import TELEGRAM_API_ID, TELEGRAM_API_HASH
from django.http import HttpRequest
from user.models import CustomUser
from asgiref.sync import sync_to_async
from user.services import get_user
from django.core.files.storage import default_storage
from django.core.files import File
from django.utils import timezone
from django.conf import settings
from telegram_api import tasks
from telegramweb.exceptions import NotTelegramAuthorized


async def get_telegram_session(phone: str) -> str:
    """ Get Telegram session from phone number """
    try:
        session = await sync_to_async(lambda: TelegramSession.objects.get(phone=phone), thread_sensitive=True)()
    except TelegramSession.DoesNotExist:
        return ''
    return session.session


async def get_active_session(session: str) -> str:
    """ Get telegram session by string session """
    try:
        ses = await TelegramSession.objects.aget(session=session)
    except TelegramSession.DoesNotExist:
        return ''
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


async def search(client: TelegramClient, channels, keywords, groups) -> tuple[
    list[Any], list[User | Chat | Channel], set[Any]]:
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


async def create_channel(channel: User | Chat | Channel) -> DBChannel:
    """ Create Channel object """
    try:
        new_channel = await DBChannel.objects.aget(id=channel.id)
    except DBChannel.DoesNotExist:
        try:
            new_channel = await DBChannel.objects.acreate(id=channel.id, title=channel.title)
        except AttributeError:
            new_channel = await DBChannel.objects.acreate(id=channel.id, title=(
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
        await client.send_code_request(request.session.get('phone'))
        result = await client.send_code_request(request.session.get('phone'))
        await adjust_user_active_session(client, phone, request, result, user)
    elif str(me.phone) != phone.replace('+', ''):
        await client.send_code_request(phone)
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


async def get_client_info(request):
    telegram_session = await sync_to_async(lambda: request.user.active_session, thread_sensitive=True)()
    client = TelegramClient(session=StringSession(telegram_session), api_id=TELEGRAM_API_ID,
                            api_hash=TELEGRAM_API_HASH)
    await client.connect()
    active_session_phone = await get_active_session(telegram_session)
    numbers = await get_numbers(request.user.email)
    return active_session_phone, client, numbers


async def save_files(files):
    new_files = list()
    for file in files:
        filename = file.name
        if filename[0].upper() not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            filename = 'A' + filename
        i = 0
        while os.path.isfile(os.path.join(settings.MEDIA_ROOT, f'{filename[0].upper()}/{filename[:filename.rindex(".")]} ({i}) {filename[filename.rindex("."):]}')):
            i += 1
        else:
            filename = filename[:filename.rindex(".")] + f' ({i})' + filename[filename.rindex("."):]
        with default_storage.open(f'tmp/{filename}', 'wb+') as f:
            for chunk in file.chunks():
                f.write(chunk)
            new_file = DBFile()
            await sync_to_async(lambda: new_file.file.save(f'{filename[0].upper()}/{filename}', File(f)), thread_sensitive=True)()
            await sync_to_async(lambda: new_file.save(), thread_sensitive=True)()
            new_files.append(new_file)
        os.remove(f'{settings.MEDIA_ROOT}tmp/{filename}')
    return new_files


async def make_mailing_request_object(request, title: str, text: str, images: list, files: list, groups: list,
                                      is_instant: str | None, dates: list, date_format: str = None, begin_time: str = None,
                                      end_time: str = None, intervals_number: int = None, interval: str = None):
    email = await sync_to_async(lambda: request.user.email, thread_sensitive=True)()
    user = await get_user(email)
    new_mailing_request = MailingRequest(message_title=title, message_text=text, user_id=user.id, is_instant=True if is_instant == 'on' else False)
    await sync_to_async(lambda: new_mailing_request.save(), thread_sensitive=True)()
    if len(images) > 0:
        new_images = await save_files(images)
        await sync_to_async(lambda: new_mailing_request.message_images.set(new_images), thread_sensitive=True)()
    if len(files) > 0:
        new_files = await save_files(files)
        await sync_to_async(lambda: new_mailing_request.message_files.set(new_files), thread_sensitive=True)()

    entity_groups = await get_groups_entity(request, groups)
    new_groups = list()
    for group in entity_groups:
        channel = await create_channel(group)
        new_groups.append(channel)
    client_phone = await get_active_session(user.active_session)
    new_mailing_request.client_phone = client_phone
    new_mailing_request.send_time = dates
    if date_format:
        match date_format:
            case 'periodical':
                new_mailing_request.date_format = 1
            case 'particular':
                new_mailing_request.date_format = 2
            case _:
                new_mailing_request.date_format = 3

    if date_format == 'periodical':
        new_mailing_request.begin_time = datetime.strptime(begin_time, '%Y-%m-%dT%H:%M')
        new_mailing_request.end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
        new_mailing_request.interval_duration = intervals_number
        new_mailing_request.interval_time = interval

    await sync_to_async(lambda: new_mailing_request.groups.set(new_groups), thread_sensitive=True)()
    await sync_to_async(lambda: new_mailing_request.save(), thread_sensitive=True)()
    if is_instant:
        tasks.send_message.delay(new_mailing_request.id)




async def get_groups_entity(request, groups: list[str]):
    session = await sync_to_async(lambda: request.user.active_session, thread_sensitive=True)()

    client = TelegramClient(session=StringSession(session), api_id=TELEGRAM_API_ID, api_hash=TELEGRAM_API_HASH)
    await client.connect()
    new_groups = list()
    for group in groups:
        try:
            entity = await client.get_entity(int(group))
        except ValueError:
            entity = await client.get_entity(PeerChannel(int(group)))
        new_groups.append(entity)
    return new_groups


async def get_last_mailing():
    mailing: MailingRequest = await sync_to_async(lambda: list(MailingRequest.objects.all())[-1], thread_sensitive=True)()
    images = list()
    for image in mailing.message_images:
        images.append(image.url)
    return images


async def parse_periodical_dates(begin_time: str, end_time: str, intervals_number: int, interval: str) -> list[datetime]:
    dates = list()
    new_begin_time = datetime.strptime(begin_time, '%Y-%m-%dT%H:%M')
    new_end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
    dates.append(new_begin_time)
    while dates[-1] < new_end_time:
        if interval == 'weeks':
            dates.append(dates[-1] + timedelta(weeks=int(intervals_number)))
        elif interval == 'days':
            dates.append(dates[-1] + timedelta(days=int(intervals_number)))
        elif interval == 'hours':
            dates.append(dates[-1] + timedelta(hours=int(intervals_number)))
        else:
            dates.append(dates[-1] + timedelta(minutes=int(intervals_number)))
    else:
        del dates[-1]
    return dates


async def parse_particular_dates(dates: list[str], time: str) -> list[datetime]:
    new_dates = list()
    for d in dates:
        new_dates.append(datetime.strptime(f'{d}T{time}', '%m/%d/%YT%H:%M'))
    return sorted(new_dates)


def get_mailing_request(id: int):
    request = MailingRequest.objects.get(id=id)
    return request


async def send_mailing(request: MailingRequest):
    session = await get_telegram_session(request.client_phone)
    client = TelegramClient(StringSession(session), api_id=settings.TELEGRAM_API_ID, api_hash=settings.TELEGRAM_API_HASH)
    await client.connect()
    text = await make_mailing_text(request.message_title, request.message_text)
    images = await sync_to_async(lambda: list(request.message_images.all()), thread_sensitive=True)()
    new_images = [image.file.file.name for image in images]
    files = await sync_to_async(lambda: list(request.message_files.all()), thread_sensitive=True)()
    new_files = [file.file.file.name for file in files]
    groups = await sync_to_async(lambda: list(request.groups.all()), thread_sensitive=True)()
    if len(list(images)) + len(list(files)) > 0:
        for group in groups:
            try:
                entity = await client.get_entity(group.id)
            except ValueError:
                entity = await client.get_entity(PeerChannel(group.id))
            if len(new_images) > 0:
                await client.send_file(entity=entity, file=new_images, caption=text)
                if len(new_files) > 0:
                    await client.send_file(entity=entity, file=new_files, force_document=True, allow_cache=False)
            else:
                await client.send_file(entity=entity, file=new_files, force_document=True, allow_cache=False, caption=text)
    else:
        for group in groups:
            try:
                entity = await client.get_entity(group.id)
            except ValueError:
                entity = await client.get_entity(PeerChannel(group.id))
            await client.send_message(entity=entity, message=text)
    if request.is_instant:
        request.is_active = False
    await sync_to_async(lambda: request.save(), thread_sensitive=True)()


async def make_mailing_text(title: str, text: str):
    if len(title) + len(text) == 0:
        return ''
    new_text = f'**{title}**\n\n{text}'
    return new_text


def get_active_mailings() -> list[MailingRequest]:
    mailings = MailingRequest.objects.all().filter(is_active=True)
    return list(mailings)


async def check_mailings(mailings: list[MailingRequest]) -> None:
    count = 0
    print(len(mailings))
    for mailing in mailings:
        for time in mailing.send_time:
            if 0 <= (timezone.now() - time).total_seconds() / 60 <= 1:

                count += 1
                await send_mailing(mailing)
        if (timezone.now() - mailing.send_time[-1]).total_seconds() / 60 > 0:
            mailing.is_active = False
            await sync_to_async(lambda: mailing.save(), thread_sensitive=True)()
    print(f'{count} mailings sent...')


async def get_active_mailings_by_user(user: CustomUser) -> list[MailingRequest]:
    mailings = await sync_to_async(lambda: list(MailingRequest.objects.all().filter(is_active=True, user_id=user.id)),
                                   thread_sensitive=True)()
    return mailings


async def parse_mailings(mailings: list[MailingRequest]) -> list[ParsedMailing]:
    new_mailings = list()
    for mailing in mailings:
        groups = await sync_to_async(lambda: list(mailing.groups.all()), thread_sensitive=True)()
        files = await sync_to_async(lambda: list(mailing.message_files.all()), thread_sensitive=True)()
        images = await sync_to_async(lambda: list(mailing.message_images.all()), thread_sensitive=True)()
        new_mailings.append(ParsedMailing(mailing, groups, images, files))
    return new_mailings


async def make_mailing_inactive(id: int) -> None:
    mailing = await MailingRequest.objects.aget(id=id)
    mailing.is_active = False
    await sync_to_async(lambda: mailing.save(), thread_sensitive=True)()


async def get_inactive_mailings_by_user(user: CustomUser) -> list[MailingRequest]:
    mailings = await sync_to_async(lambda: list(MailingRequest.objects.all().filter(is_active=False, user_id=user.id)),
                                   thread_sensitive=True)()
    return mailings


async def make_mailing_active(id: int) -> None:
    mailing = await MailingRequest.objects.aget(id=id)
    mailing.is_active = True
    await sync_to_async(lambda: mailing.save(), thread_sensitive=True)()
