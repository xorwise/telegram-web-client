from django.urls import path
from telegram_api.views import TelegramView, TelegramConfirmView, MessageSearch, SearchRequestQueue

urlpatterns = [
    path('', TelegramView.as_view()),
    path('confirm/', TelegramConfirmView.as_view()),
    path('search/', MessageSearch.as_view()),
    path('search-queue/', SearchRequestQueue.as_view()),
    path('search-queue/<int:page>/', SearchRequestQueue.as_view()),
]