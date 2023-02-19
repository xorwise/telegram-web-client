from django.contrib import admin
from django.urls import path, include
from telegramweb.views import MainPage
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', MainPage.as_view()),
    path('user/', include('user.urls')),
    path('tg/', include('telegram_api.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

