from django.shortcuts import render, redirect
from django.views.generic import CreateView
# Create your views here.
from user import services
from user.forms import ProfileForm
from django.contrib.auth import authenticate, login

from user.models import CustomUser


class UserChangeView(CreateView):
    template_name = 'index.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return render(request, self.template_name)

        return redirect('/login')


class LoginView(CreateView):
    template_name = 'user/login.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('/')

        return render(request, self.template_name, {'result': ''})

    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is None:
            return render(request, self.template_name, {'result': 'Incorrect username or password'})

        login(request, user)
        return redirect('/')


class ProfileView(CreateView):
    template_name = 'user/profile.html'
    form = ProfileForm

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/login')

        return render(request, self.template_name, {'form': self.form, 'result': ''})

    def post(self, request, *args, **kwargs):
        user = services.get_user(request.user.username)

        user.email = request.POST.get('email')
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.phone = request.POST.get('phone')
        user.telegram = request.POST.get('telegram')

        user.save()

        return render(request, self.template_name, {'form': self.form, 'result': 'Success!'})



