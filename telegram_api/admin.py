from django.contrib import admin
from telegram_api.models import SearchRequest, Channel
# Register your models here.
admin.site.register(SearchRequest)
admin.site.register(Channel)
