from django.contrib import admin
from telegram_api.models import SearchRequest, Channel, TelegramSession
# Register your models here.
admin.site.register(SearchRequest, Channel, TelegramSession)
