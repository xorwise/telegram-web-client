from django.contrib import admin
from django.urls import path, include
from telegramweb.views import MainPage

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', MainPage.as_view()),
    path('user/', include('user.urls')),
    path('tg/', include('telegram_api.urls')),
]
