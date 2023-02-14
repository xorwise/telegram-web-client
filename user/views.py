from django.shortcuts import render, redirect
from django.views.generic import View
from django.core.exceptions import ValidationError
from user import services
from user.forms import ProfileForm, RegisterForm
from django.contrib.auth import authenticate, login
from asgiref.sync import sync_to_async
from django.core.validators import EmailValidator
from user.models import CustomUser, CustomUserManager


class RegisterView(View):
    template_name = 'user/register.html'
    form_class = RegisterForm()

    async def get(self, request, *args, **kwargs):
        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated, thread_sensitive=True)()
        if is_authenticated:
            return redirect('/')
        return render(request, self.template_name, {'is_authenticated': is_authenticated, 'result': ''})

    async def post(self, request, *args, **kwargs):
        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated, thread_sensitive=True)()
        if is_authenticated:
            return redirect('/')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        result = 'Аккаунт был создан.\nПожалуйста, свяжитесь с администрацией для активации.'
        is_valid_password = is_valid_email = is_valid_phone = False

        try:
            is_valid_password = await services.validate_password(password1, password2)
        except ValidationError as e:
            result = e.message
        try:
            EmailValidator(message='Введите корректную почту!')
        except ValidationError as e:
            result = e.message
        else:
            is_valid_email = True
        try:
            is_valid_phone = await services.validate_phone(phone)
        except ValidationError as e:
            result = e.message

        if is_valid_password and is_valid_email and is_valid_phone:
            await sync_to_async(lambda: CustomUser.objects.create_user(email=email, phone=phone, password=password1), thread_sensitive=True)()

        return render(request, self.template_name, {'is_authenticated': is_authenticated, 'result': result})


class LoginView(View):
    """ Class based view for user login"""
    template_name = 'user/login.html'

    async def get(self, request, *args, **kwargs):
        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated, thread_sensitive=True)()
        if is_authenticated:
            return redirect('/')

        return render(request, self.template_name, {'result': ''})

    async def post(self, request, *args, **kwargs):
        email_or_phone = request.POST.get('username')
        password = request.POST.get('password')

        try:
            user = await services.get_user_by_phone(email_or_phone)
            email = user.email
        except CustomUser.DoesNotExist:
            email = email_or_phone

        user = await sync_to_async(lambda: authenticate(request, username=email, password=password),
                                   thread_sensitive=True)()
        if user is None:
            return render(request, self.template_name, {'result': 'Неправильный логин или пароль. Возможно ваш аккаунт не был активирован.\nПожалуйста, свяжитесь с администрацией'})

        await sync_to_async(lambda: login(request, user), thread_sensitive=True)()
        return redirect('/')


class ProfileView(View):
    """ Class based view for user profile"""
    template_name = 'user/profile.html'
    form = ProfileForm

    async def get(self, request, *args, **kwargs):
        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated, thread_sensitive=True)()
        if not is_authenticated:
            return redirect('/user/login')

        return render(request, self.template_name, {'form': self.form, 'result': ''})

    async def post(self, request, *args, **kwargs):
        email = await sync_to_async(lambda: request.user.email, thread_sensitive=True)()
        user = await services.get_user(email)

        user.email = request.POST.get('email')
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.phone = request.POST.get('phone')
        user.telegram = request.POST.get('telegram')

        await sync_to_async(lambda: user.save(), thread_sensitive=True)()

        return redirect('/user/profile')
