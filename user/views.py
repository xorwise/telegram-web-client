from django.shortcuts import render, redirect
from django.views.generic import View
# Create your views here.
from user import services
from user.forms import ProfileForm
from django.contrib.auth import authenticate, login
from asgiref.sync import sync_to_async

from user.models import CustomUser


class UserChangeView(View):
    template_name = 'index.html'

    async def get(self, request, *args, **kwargs):
        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated, thread_sensitive=True)()
        if is_authenticated:
            return render(request, self.template_name, {'is_authenticated': is_authenticated})
        return redirect('/login')


class LoginView(View):
    template_name = 'user/login.html'

    async def get(self, request, *args, **kwargs):
        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated, thread_sensitive=True)()
        if is_authenticated:
            return redirect('/')

        return render(request, self.template_name, {'result': ''})

    async def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = await sync_to_async(lambda: authenticate(request, username=username, password=password), thread_sensitive=True)()
        if user is None:
            return render(request, self.template_name, {'result': 'Incorrect username or password'})

        await sync_to_async(lambda: login(request, user), thread_sensitive=True)()
        return redirect('/')


class ProfileView(View):
    template_name = 'user/profile.html'
    form = ProfileForm

    async def get(self, request, *args, **kwargs):
        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated, thread_sensitive=True)()
        if not is_authenticated:
            return redirect('/login')

        return render(request, self.template_name, {'form': self.form, 'result': ''})

    async def post(self, request, *args, **kwargs):
        username = await sync_to_async(lambda: request.user.username, thread_sensitive=True)()
        user = await services.get_user(username)

        user.email = request.POST.get('email')
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.phone = request.POST.get('phone')
        user.telegram = request.POST.get('telegram')

        await sync_to_async(lambda: user.save(), thread_sensitive=True)()

        return redirect('/profile')
