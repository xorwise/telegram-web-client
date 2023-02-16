from telegram_api.services import send_message
from telegramweb.exceptions import NotTelegramAuthorized
from telegramweb.settings import TELEGRAM_API_ID, TELEGRAM_API_HASH
from django.shortcuts import render, redirect
from django.views.generic import View
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError, PasswordHashInvalidError
from telethon.errors.rpcerrorlist import PhoneCodeInvalidError, FloodWaitError
from telethon.sessions import StringSession
from telegram_api.forms import PhoneForm, ConfirmForm, MailingForm
from telegram_api import services
from telegram_api.tasks import messages_search
from user.services import get_user
from asgiref.sync import sync_to_async
import asyncio
import phonenumbers
from phonenumbers import carrier
from phonenumbers.phonenumberutil import number_type


class TelegramView(View):
    """ Class based view for telegram authorization, phone number verification """
    template_name = 'telegram_api/telegram.html'

    async def get(self, request, *args, **kwargs):
        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated)()
        if not is_authenticated:
            return redirect('/user/login')
        return render(request, self.template_name, {'form': PhoneForm(), 'is_authenticated': is_authenticated})

    async def post(self, request, *args, **kwargs):
        phone = request.POST.get('phone')

        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated)()
        try:
            parsed_phone = phonenumbers.parse(phone)
        except phonenumbers.phonenumberutil.NumberParseException:
            return render(request, self.template_name, {'form': PhoneForm(), 'is_authenticated': is_authenticated,
                                                        'error': 'Невалидный номер телефона!', 'value': phone})
        else:
            if not phonenumbers.is_valid_number(parsed_phone):
                return render(request, self.template_name, {'form': PhoneForm(), 'is_authenticated': is_authenticated,
                                                            'error': 'Невалидный номер телефона!', 'value': phone})

        formatted_phone = phonenumbers.format_number(parsed_phone, phonenumbers.PhoneNumberFormat.E164)
        await sync_to_async(lambda: request.session.update({
                "phone": formatted_phone}),
                            thread_sensitive=True)()

        email = await sync_to_async(lambda: request.user.email)()
        user = await get_user(email)
        try:
            new_user = await send_message(request, formatted_phone, user)
        except FloodWaitError as e:
            time = e.seconds
            str_time = f'{time} секунд'
            if time > 60:
                str_time = f'{time // 60} минут {time % 60} секунд'
                if time > 3600:
                    str_time = f'{time // 3600} часов {(time % 3600) // 60} минут {(time % 3600) % 60} секунд'
            return render(request, self.template_name, {'form': PhoneForm(), 'is_authenticated': is_authenticated,
                                                        'error': f'Не посылайте запросы слишком часто, подождите {str_time}.', 'value': phone})

        await sync_to_async(lambda: new_user.save(), thread_sensitive=True)()

        return redirect('/tg/confirm')


class TelegramConfirmView(View):
    """ Class based view for telegram authorization, code and password verification """
    template_name = 'telegram_api/telegram-confirm.html'

    async def get(self, request, *args, **kwargs):
        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated, thread_sensitive=True)()
        if not is_authenticated:
            return redirect('/user/login')
        phone = await sync_to_async(lambda: request.session.get('phone'), thread_sensitive=True)()
        session = await services.get_telegram_session(phone)
        telegram_client = TelegramClient(session=StringSession(session), api_id=TELEGRAM_API_ID,
                                         api_hash=TELEGRAM_API_HASH)
        await telegram_client.connect()

        if await telegram_client.is_user_authorized():
            print('true ')
            return redirect('/tg/search')
        return render(request, self.template_name, {'form': ConfirmForm(),
                                                    'result': '',
                                                    'is_authenticated': is_authenticated})

    async def post(self, request, *args, **kwargs):
        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated, thread_sensitive=True)()
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
        except PhoneCodeInvalidError:
            return render(request, self.template_name, {'form': ConfirmForm(),
                                                        'result': 'Неверный код!',
                                                        'values': {'code': request.POST.get('code'),
                                                                   'password': request.POST.get('password')},
                                                        'is_authenticated': is_authenticated
                                                        })
        except SessionPasswordNeededError:
            try:
                await telegram_client.sign_in(password=password)
            except PasswordHashInvalidError:
                return render(request, self.template_name, {'form': ConfirmForm(),
                                                            'result': 'Неправильный пароль!', 'values': {'code': code,
                                                                                                       'password': password},
                                                            'is_authenticated': is_authenticated
                                                            })

        return redirect('/tg/search')


class MessageSearch(View):
    """ Class based view for message searching and forwarding based on keywords and channels."""
    template_name = 'telegram_api/search-messages.html'

    async def get(self, request, *args, **kwargs):
        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated, thread_sensitive=True)()
        if not is_authenticated:
            return redirect('/user/login')
        active_session_phone, client, numbers = await services.get_client_info(request)

        if not await client.is_user_authorized() or active_session_phone == '':
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
        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated, thread_sensitive=True)()
        if not is_authenticated:
            return redirect('/user/login')
        if 'number' in request.POST:
            if 'choose' in request.POST:
                email = await sync_to_async(lambda: request.user.email, thread_sensitive=True)()
                await services.change_active_session(request.POST.get('number'), email)
            else:
                await services.delete_session(request.POST.get('number'))
            return redirect('/tg/search')
        else:
            telegram_session = await sync_to_async(lambda: request.user.active_session, thread_sensitive=True)()
            email = await sync_to_async(lambda: request.user.email, thread_sensitive=True)()
            channels = request.POST.get('channels').replace('\n', ' ').split(' ')
            keywords = request.POST.get('keywords').split(',')
            groups = await services.parse_request(mode=False, keys=list(request.POST.keys()))
            phone = await services.get_number(telegram_session)
            client = TelegramClient(session=StringSession(telegram_session), api_id=TELEGRAM_API_ID,
                                    api_hash=TELEGRAM_API_HASH)
            await client.connect()
            choices = await services.get_dialog_choices(client)
            active_session_phone = await services.get_active_session(telegram_session)
            numbers = await services.get_numbers(request.user.email)
            try:
                await services.validate_channels(client, channels)
            except (ValueError, TypeError):
                result = 'Канал(ы) не был(и) найден(ы).'
                return render(request, self.template_name, {
                    'is_tg_authorized': True,
                    'channels': choices,
                    'active_tg': active_session_phone,
                    'result': result,
                    'numbers': numbers,
                    'values': {
                        'channels': request.POST.get('channels'),
                        'keywords': request.POST.get('keywords'),
                        'groups': groups,
                    }
                })
            else:
                result = 'Запрос создан и добавлен в очередь!'
            messages_search.delay(telegram_session, channels, keywords, groups, email, phone)

            return render(request, self.template_name, {'is_tg_authorized': True,
                                                        'channels': choices,
                                                        'active_tg': active_session_phone,
                                                        'result': result,
                                                        'numbers': numbers})


class SearchRequestQueue(View):
    """ Class based view for showing queue of search requests """
    template_name = 'telegram_api/search-queue.html'

    async def get(self, request, page: int = 0, *args, **kwargs):
        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated, thread_sensitive=True)()
        if not is_authenticated:
            return redirect('/user/login')
        email = await sync_to_async(lambda: request.user.email, thread_sensitive=True)()
        db_user = await get_user(email)
        requests = await services.get_sorted_requests(db_user)
        parsed_requests = await services.parse_requests(requests)
        return render(request, self.template_name,
                      {'requests': parsed_requests[page * 8:page * 8 + 8], 'page': page, 'len': len(requests)})

    async def post(self, request, page: int = 0, *args, **kwargs):
        request_id = int([i for i in list(request.POST.keys()) if i.startswith('request')][0][8:])
        await services.delete_request(request_id)
        return redirect('/tg/search-queue/')


class MessageMailing(View):
    template_name = 'telegram_api/message-mailing.html'
    form_class = MailingForm()

    async def get(self, request, *args, **kwargs):
        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated, thread_sensitive=True)()
        if not is_authenticated:
            return redirect('/user/login')
        active_session_phone, client, numbers = await services.get_client_info(request)

        if not await client.is_user_authorized() or active_session_phone == '':
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
            if 'choose' in request.POST:
                email = await sync_to_async(lambda: request.user.email, thread_sensitive=True)()
                await services.change_active_session(request.POST.get('number'), email)
            else:
                await services.delete_session(request.POST.get('number'))
            return redirect('/tg/mailing')
        title = request.POST.get('title')
        text = request.POST.get('text')
        images = request.FILES.getlist('images')
        files = request.FILES.getlist('files')
        print(request.POST.keys())
        groups = [key[6:] for key in request.POST.keys() if key.startswith('group_')]
        is_instant = request.POST.get('is_instant')

        mailing_time = list()
        begin_time = None
        end_time = None
        intervals_number = None
        interval = None
        date_format = None
        if not is_instant:
            date_format = request.POST.get('date_format')
            if date_format == 'periodical':
                begin_time = request.POST.get('begin_time')
                end_time = request.POST.get('end_time')
                intervals_number = request.POST.get('intervals_number')
                interval = request.POST.get('interval')
                mailing_time = await services.parse_periodical_dates(begin_time, end_time, intervals_number, interval)
            elif date_format == 'particular':
                dates = request.POST.get('dates').split(',')
                time = request.POST.get('time')
                mailing_time = await services.parse_particular_dates(dates, time)

        await services.make_mailing_request_object(request, title, text, images, files, groups, is_instant,
                                                   mailing_time, date_format, begin_time,
                                                   end_time, intervals_number, interval)
        return redirect('/tg/mailing')


class MailingQueue(View):
    template_name = 'telegram_api/mailing-queue.html'

    async def get(self, request, page: int = 0, *args, **kwargs):
        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated, thread_sensitive=True)()
        if not is_authenticated:
            return redirect('/user/login')
        email = await sync_to_async(lambda: request.user.email, thread_sensitive=True)()
        user = await get_user(email)
        mailings = await services.get_active_mailings_by_user(user)
        parsed_mailings = await services.parse_mailings(mailings)
        return render(request, self.template_name, {
            'mailings': parsed_mailings[page * 8: page * 8 + 8],
            'page': page,
            'len': len(parsed_mailings),
        })

    async def post(self, request, page: int = 0, *args, **kwargs):
        keys = list(request.POST.keys())
        print(keys)
        mailing_id = [key[8:] for key in keys if key.startswith('mailing_')][0]
        await services.make_mailing_inactive(mailing_id)
        return redirect('/tg/mailing-queue')


class MailingArchive(View):
    template_name = 'telegram_api/mailing-archive.html'

    async def get(self, request, page: int = 0, *args, **kwargs):
        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated, thread_sensitive=True)()
        if not is_authenticated:
            return redirect('/user/login')
        email = await sync_to_async(lambda: request.user.email, thread_sensitive=True)()
        user = await get_user(email)
        mailings = await services.get_inactive_mailings_by_user(user)
        parsed_mailings = await services.parse_mailings(mailings)
        return render(request, self.template_name, {
            'mailings': parsed_mailings[page * 8: page * 8 + 8],
            'page': page,
            'len': len(parsed_mailings),
        })

    async def post(self, request, page: int = 0, *args, **kwargs):
        keys = list(request.POST.keys())
        print(keys)
        mailing_id = [key[8:] for key in keys if key.startswith('mailing_')][0]
        await services.make_mailing_active(mailing_id)
        return redirect('/tg/mailing-archive')
