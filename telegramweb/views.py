from asgiref.sync import sync_to_async
from django.shortcuts import render, redirect
from django.views import View


class MainPage(View):
    template_name = 'index.html'

    async def get(self, request, *args, **kwargs):
        is_authenticated = await sync_to_async(lambda: request.user.is_authenticated, thread_sensitive=True)()
        if is_authenticated:
            return render(request, self.template_name, {'is_authenticated': is_authenticated})
        return redirect('/user/login')
