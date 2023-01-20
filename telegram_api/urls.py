from django.urls import path
from telegram_api.views import TelegramView, TelegramConfirmView, MessageSearch, MessageQueue

urlpatterns = [
    path('', TelegramView.as_view()),
    path('confirm/', TelegramConfirmView.as_view()),
    path('search/', MessageSearch.as_view()),
    path('queue/', MessageQueue.as_view()),
    path('queue/<int:page>/', MessageQueue.as_view()),
]