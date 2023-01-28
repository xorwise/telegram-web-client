from telegram_api.services import send_message
from telegramweb.settings import TELEGRAM_API_ID, TELEGRAM_API_HASH
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


class TelegramView(View):
    """ Class based view for telegram authorization, phone number verification """
    template_name = 'telegram_api/telegram.html'

    async def get(self, request, *args, **kwargs):
        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated)()
        return render(request, self.template_name, {'form': PhoneForm(), 'is_authenticated': is_authenticated})

    async def post(self, request, *args, **kwargs):
        await sync_to_async(lambda: request.session.update({"phone": request.POST.get('phone')}),
                            thread_sensitive=True)()
        email = await sync_to_async(lambda: request.user.email)()
        user = await get_user(email)
        new_user = await send_message(request, request.POST.get('phone'), user)

        await sync_to_async(lambda: new_user.save(), thread_sensitive=True)()

        return redirect('/tg/confirm')


class TelegramConfirmView(View):
    """ Class based view for telegram authorization, code and password verification """
    template_name = 'telegram_api/telegram-confirm.html'

    async def get(self, request, *args, **kwargs):
        phone = await sync_to_async(lambda: request.session.get('phone'), thread_sensitive=True)()
        session = await services.get_telegram_session(phone)
        telegram_client = TelegramClient(session=StringSession(session), api_id=TELEGRAM_API_ID,
                                         api_hash=TELEGRAM_API_HASH)
        await telegram_client.connect()

        if await telegram_client.is_user_authorized():
            print('true ')
            return redirect('/tg/search')
        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated, thread_sensitive=True)()
        return render(request, self.template_name, {'form': ConfirmForm(),
                                                    'result': '',
                                                    'is_authenticated': is_authenticated})

    async def post(self, request, *args, **kwargs):
        phone = await sync_to_async(lambda: request.session.get('phone'), thread_sensitive=True)()
        code = request.POST.get('code')
        password = request.POST.get('password')
        phone_code_hash = await sync_to_async(lambda: request.session.get('phone_code_hash'), thread_sensitive=True)()
        session = await services.get_telegram_session(phone)
        telegram_client = TelegramClient(session=StringSession(session), api_id=TELEGRAM_API_ID,
                                         api_hash=TELEGRAM_API_HASH)
        await telegram_client.connect()

        try:
            await telegram_client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        except SessionPasswordNeededError:
            try:
                await telegram_client.sign_in(password=password)
            except PasswordHashInvalidError:
                return render(request, self.template_name, {'form': ConfirmForm(),
                                                            'result': 'Incorrect password'})
        except CodeInvalidError:
            return render(request, self.template_name, {'form': ConfirmForm(),
                                                        'result': 'Incorrect code'})
        return redirect('/tg/search')


class MessageSearch(View):
    """ Class based view for message searching and forwarding based on keywords and channels."""
    template_name = 'telegram_api/search-messages.html'

    async def get(self, request, *args, **kwargs):
        telegram_session = await sync_to_async(lambda: request.user.active_session, thread_sensitive=True)()
        client = TelegramClient(session=StringSession(telegram_session), api_id=TELEGRAM_API_ID,
                                api_hash=TELEGRAM_API_HASH)
        await client.connect()
        active_session_phone = await services.get_active_session(telegram_session)
        numbers = await services.get_numbers(request.user.email)
        if not await client.is_user_authorized():
            return render(request, self.template_name, {'is_tg_authorized': False,
                                                        'active_tg': active_session_phone,
                                                        'numbers': numbers})
        choices = await services.get_dialog_choices(client)
        return render(request, self.template_name, {'is_tg_authorized': True,
                                                    'channels': choices,
                                                    'result': '',
                                                    'active_tg': active_session_phone,
                                                    'numbers': numbers})

    async def post(self, request, *args, **kwargs):
        if 'number' in request.POST:
            email = await sync_to_async(lambda: request.user.email, thread_sensitive=True)()
            await services.change_active_session(request.POST.get('number'), email)
            return redirect('/tg/search')
        else:
            telegram_session = await sync_to_async(lambda: request.user.active_session, thread_sensitive=True)()
            email = await sync_to_async(lambda: request.user.email, thread_sensitive=True)()
            channels = request.POST.get('channels').replace('\n', ' ').split(' ')
            keywords = request.POST.get('keywords').split(',')
            groups = await services.parse_request(mode=False, keys=list(request.POST.keys()))
            phone = await services.get_number(telegram_session)
            messages_search.delay(telegram_session, channels, keywords, groups, email, phone)

            client = TelegramClient(session=StringSession(telegram_session), api_id=TELEGRAM_API_ID,
                                    api_hash=TELEGRAM_API_HASH)
            await client.connect()
            choices = await services.get_dialog_choices(client)
            active_session_phone = await services.get_active_session(telegram_session)
            numbers = await services.get_numbers(request.user.email)
            return render(request, self.template_name, {'is_tg_authorized': True,
                                                        'channels': choices,
                                                        'active_tg': active_session_phone,
                                                        'result': 'Запрос создан и добавлен в очередь!',
                                                        'numbers': numbers})


class SearchRequestQueue(View):
    """ Class based view for showing queue of search requests """
    template_name = 'telegram_api/message-queue.html'

    async def get(self, request, page: int = 0, *args, **kwargs):
        telegram_session = await sync_to_async(lambda: request.user.active_session, thread_sensitive=True)()
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
        return redirect('/tg/search-queue/')
