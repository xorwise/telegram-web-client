import asyncio

from telegram_api.services import send_message
from telegramweb.settings import TELEGRAM_API_ID, TELEGRAM_API_HASH
from django.shortcuts import render, redirect
from django.views.generic import CreateView
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError, PasswordHashInvalidError, CodeInvalidError
from telethon.sessions import StringSession
from user.models import CustomUser
from telegram_api.forms import PhoneForm, ConfirmForm
from telegram_api import services
from telegram_api.tasks import messages_search
from user.services import get_user
# Create your views here.


class TelegramView(CreateView):
    template_name = 'telegram_api/telegram.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {'form': PhoneForm()})

    def post(self, request, *args, **kwargs):
        request.session['number'] = request.POST.get('phone')
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        user = get_user(request.user.username)
        loop.run_until_complete(send_message(request, request.POST.get('phone'), user))

        return redirect('/tg/confirm')


class TelegramConfirmView(CreateView):
    template_name = 'telegram_api/telegram-confirm.html'

    def get(self, request, *args, **kwargs):
        user = request.user

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        db_user = CustomUser.objects.get(username=user.username)

        telegram_client = TelegramClient(session=StringSession(db_user.telegram_session), api_id=TELEGRAM_API_ID, api_hash=TELEGRAM_API_HASH)
        telegram_client.connect()

        if telegram_client.is_user_authorized():
            return redirect('/tg/search')

        return render(request, self.template_name, {'form': ConfirmForm(), 'result': ''})

    def post(self, request, *args, **kwargs):
        user = request.user
        phone = request.session.get('number')
        code = request.POST.get('code')
        password = request.POST.get('password')
        phone_code_hash = request.session.get('phone_code_hash')
        db_user = CustomUser.objects.get(username=user.username)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        telegram_client = TelegramClient(session=StringSession(db_user.telegram_session), api_id=TELEGRAM_API_ID, api_hash=TELEGRAM_API_HASH)
        telegram_client.connect()

        try:
            telegram_client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        except SessionPasswordNeededError:
            try:
                telegram_client.sign_in(password=password)
            except PasswordHashInvalidError:
                return render(request, self.template_name, {'form': ConfirmForm(), 'result': 'Incorrect password'})
        except CodeInvalidError:
            return render(request, self.template_name, {'form': ConfirmForm(), 'result': 'Incorrect code'})

        return redirect('/tg/search')


class MessageSearch(CreateView):
    template_name = 'telegram_api/search-messages.html'

    def get(self, request, *args, **kwargs):
        user = request.user
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        client = TelegramClient(session=StringSession(user.telegram_session), api_id=TELEGRAM_API_ID, api_hash=TELEGRAM_API_HASH)
        if not loop.run_until_complete(services.is_telegram_authorized(client)):
            return redirect('/tg')
        choices = loop.run_until_complete(services.get_dialog_choices(client))
        return render(request, self.template_name, {'channels': choices, 'result': ''})

    def post(self, request, *args, **kwargs):
        user = request.user

        channels = request.POST.get('channels').replace('\n', ' ').split(' ')
        keywords = request.POST.get('keywords').split(',')
        groups = services.parse_request(mode=False, keys=list(request.POST.keys()))
        messages_search.delay(user.telegram_session, channels, keywords, groups)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        client = TelegramClient(session=StringSession(user.telegram_session), api_id=TELEGRAM_API_ID, api_hash=TELEGRAM_API_HASH)
        client.connect()
        choices = loop.run_until_complete(services.get_dialog_choices(client))
        return render(request, self.template_name, {'channels': choices, 'result': 'Запрос создан и добавлен в очередь!'})


class MessageQueue(CreateView):
    template_name = 'telegram_api/message-queue.html'

    def get(self, request, page: int = 0, *args, **kwargs):
        user = request.user
        requests = services.get_sorted_requests()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        client = TelegramClient(session=StringSession(user.telegram_session), api_id=TELEGRAM_API_ID,
                                api_hash=TELEGRAM_API_HASH)
        client.connect()
        parsed_requests = services.parse_requests(requests)
        return render(request, self.template_name, {'requests': parsed_requests[page * 8:page * 8 + 8], 'page': page, 'len': len(requests)})

    def post(self, request, page: int = 0, *args, **kwargs):
        request_id = int([i for i in list(request.POST.keys()) if i.startswith('request')][0][8:])
        services.delete_request(request_id)
        return redirect('/tg/queue/')
