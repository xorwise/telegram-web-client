from telegramweb.services import get_async_loop
from telegram_api.services import send_message
from telegramweb.settings import TELEGRAM_API_ID, TELEGRAM_API_HASH, SITE_URL
from django.shortcuts import render, redirect
from django.views.generic import View
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError, PasswordHashInvalidError, CodeInvalidError
from telethon.sessions import StringSession
from telegram_api.forms import PhoneForm, ConfirmForm
from telegram_api import services
from telegram_api.tasks import messages_search
from user.services import get_user
from asgiref.sync import sync_to_async
from django.http import HttpRequest
from django.contrib.sessions.models import Session


# Create your views here.


class TelegramView(View):
    template_name = 'telegram_api/telegram.html'

    async def get(self, request, *args, **kwargs):
        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated)()
        return render(request, self.template_name, {'form': PhoneForm(), 'is_authenticated': is_authenticated})

    async def post(self, request, *args, **kwargs):
        await sync_to_async(lambda: request.session.update({"phone": request.POST.get('phone')}), thread_sensitive=True)()
        email = await sync_to_async(lambda: request.user.email)()
        user = await get_user(email)
        new_user = await send_message(request, request.POST.get('phone'), user)

        await sync_to_async(lambda: new_user.save(), thread_sensitive=True)()

        return redirect('/tg/confirm')


class TelegramConfirmView(View):
    template_name = 'telegram_api/telegram-confirm.html'

    async def get(self, request, *args, **kwargs):

        session = await services.get_telegram_session(request.session.get('phone'))
        telegram_client = TelegramClient(session=StringSession(session), api_id=TELEGRAM_API_ID,
                                         api_hash=TELEGRAM_API_HASH)
        await telegram_client.connect()

        if await telegram_client.is_user_authorized():
            return redirect('/tg/search')
        return render(request, self.template_name, {'form': ConfirmForm(), 'result': ''})

    async def post(self, request, *args, **kwargs):
        phone = request.session.get('phone')
        code = request.POST.get('code')
        password = request.POST.get('password')
        phone_code_hash = request.session.get('phone_code_hash')
        session = await services.get_telegram_session(phone)
        telegram_client = TelegramClient(session=StringSession(session), api_id=TELEGRAM_API_ID,
                                         api_hash=TELEGRAM_API_HASH)
        await telegram_client.connect()

        try:
            print(phone_code_hash)
            await telegram_client.send_code_request(phone)
            await telegram_client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        except SessionPasswordNeededError:
            try:
                await telegram_client.sign_in(password=password)
            except PasswordHashInvalidError:
                return render(request, self.template_name, {'form': ConfirmForm(), 'result': 'Incorrect password'})
        except CodeInvalidError:
            return render(request, self.template_name, {'form': ConfirmForm(), 'result': 'Incorrect code'})
        return redirect('/tg/search')


class MessageSearch(View):
    template_name = 'telegram_api/search-messages.html'

    async def get(self, request, *args, **kwargs):
        telegram_session = await sync_to_async(lambda: request.user.active_session, thread_sensitive=True)()
        client = TelegramClient(session=StringSession(telegram_session), api_id=TELEGRAM_API_ID,
                                api_hash=TELEGRAM_API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            return redirect('/tg')
        choices = await services.get_dialog_choices(client)
        active_session_phone = await services.get_active_session(telegram_session)
        return render(request, self.template_name, {'channels': choices, 'result': '', 'active_tg': active_session_phone})

    async def post(self, request, *args, **kwargs):
        telegram_session = await sync_to_async(lambda: request.user.telegram_session, thread_sensitive=True)()
        email = await sync_to_async(lambda: request.user.email, thread_sensitive=True)()
        channels = request.POST.get('channels').replace('\n', ' ').split(' ')
        keywords = request.POST.get('keywords').split(',')
        groups = await services.parse_request(mode=False, keys=list(request.POST.keys()))
        messages_search.delay(telegram_session, channels, keywords, groups, email)

        client = TelegramClient(session=StringSession(telegram_session), api_id=TELEGRAM_API_ID,
                                api_hash=TELEGRAM_API_HASH)
        await client.connect()
        choices = await services.get_dialog_choices(client)
        return render(request, self.template_name,
                      {'channels': choices, 'result': 'Запрос создан и добавлен в очередь!'})


class MessageQueue(View):
    template_name = 'telegram_api/message-queue.html'

    async def get(self, request, page: int = 0, *args, **kwargs):
        telegram_session = await sync_to_async(lambda: request.user.telegram_session, thread_sensitive=True)()
        email = await sync_to_async(lambda: request.user.email, thread_sensitive=True)()
        db_user = await get_user(email)
        requests = await services.get_sorted_requests(db_user)
        client = TelegramClient(session=StringSession(telegram_session), api_id=TELEGRAM_API_ID,
                                api_hash=TELEGRAM_API_HASH)
        await client.connect()
        parsed_requests = await services.parse_requests(requests)
        return render(request, self.template_name,
                      {'requests': parsed_requests[page * 8:page * 8 + 8], 'page': page, 'len': len(requests)})

    async def post(self, request, page: int = 0, *args, **kwargs):
        request_id = int([i for i in list(request.POST.keys()) if i.startswith('request')][0][8:])
        await services.delete_request(request_id)
        return redirect('/tg/queue/')
