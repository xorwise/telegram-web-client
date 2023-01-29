from django.urls import path
from telegram_api.views import (
    TelegramView,
    TelegramConfirmView,
    MessageSearch,
    SearchRequestQueue,
    MessageMailing,
    MailingQueue,
    MailingArchive
)

urlpatterns = [
    path('', TelegramView.as_view()),
    path('confirm/', TelegramConfirmView.as_view()),
    path('search/', MessageSearch.as_view()),
    path('search-queue/', SearchRequestQueue.as_view()),
    path('search-queue/<int:page>/', SearchRequestQueue.as_view()),
    path('mailing/', MessageMailing.as_view()),
    path('mailing-queue/', MailingQueue.as_view()),
    path('mailing-queue/<int:page>/', MailingQueue.as_view()),
    path('mailing-archive/', MailingArchive.as_view()),
    path('mailing-archive/<int:page>/', MailingArchive.as_view()),
]