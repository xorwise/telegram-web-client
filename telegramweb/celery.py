import os
from celery import Celery


os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'telegramweb.settings'
)

app = Celery('telegramweb')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()
CELERY_BROKER_URL = 'redis://localhost:6379'
