from django.contrib import admin
from telegram_api.models import SearchRequest, Channel, TelegramSession, File, MailingRequest
# Register your models here.
admin.site.register(SearchRequest)
admin.site.register(Channel)
admin.site.register(TelegramSession)
admin.site.register(MailingRequest)
admin.site.register(File)
