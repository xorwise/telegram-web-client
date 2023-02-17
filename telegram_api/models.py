import enum
from datetime import datetime
from django.db import models
from django.contrib.postgres.fields import ArrayField
from user.models import CustomUser
from django.conf import settings
from django.utils import timezone


class TelegramSession(models.Model):
    """ Model of a Telegram session"""
    phone = models.CharField(max_length=255, primary_key=True)
    session = models.CharField(max_length=1000)


class Channel(models.Model):
    """ Model of a Telegram channel """
    id = models.BigIntegerField(primary_key=True)
    title = models.CharField(max_length=255, blank=True)


class SearchRequest(models.Model):
    """ Model of a search request by keywords """
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='user', blank=True,
                             null=True)
    client_phone = models.CharField(max_length=15, blank=True)
    channels = ArrayField(models.CharField(max_length=255))
    keywords = ArrayField(models.CharField(max_length=100))
    groups = models.ManyToManyField(Channel, related_name='groups', blank=True)
    is_active = models.BooleanField(default=True)
    added_messages = ArrayField(models.IntegerField(), blank=True, default=list)


class ParsedRequest:
    """ Search request parser to html view """
    id: int
    channels: str
    keywords: str
    groups: str
    last_checked: str
    is_active: bool
    client_phone: str

    def __init__(self, request: SearchRequest, groups):
        self.id = request.id
        self.channels = request.channels
        new_groups = list()
        for group in groups:
            new_groups.append(group.title)
        self.keywords = '; '.join(request.keywords)
        self.groups = '; '.join(new_groups)
        self.is_active = request.is_active
        self.client_phone = request.client_phone


class File(models.Model):
    file = models.FileField()


class DateFormatChoices(models.IntegerChoices):
    periodical = 1
    particular = 2
    none = 3


class IntervalTimeChoices(models.TextChoices):
    weeks = 'weeks'
    days = 'days'
    hours = 'hours'
    minutes = 'minutes'
    none = 'none'


class MailingRequest(models.Model):
    id = models.AutoField(primary_key=True)
    message_title = models.CharField(max_length=100)
    message_text = models.TextField()
    message_images = models.ManyToManyField(File, blank=True, related_name='mailing_images')
    message_files = models.ManyToManyField(File, blank=True, related_name='mailing_files')
    date_format = models.IntegerField(choices=DateFormatChoices.choices, default=DateFormatChoices.none)
    begin_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    interval_duration = models.IntegerField(blank=True, null=True)
    interval_time = models.CharField(max_length=7, choices=IntervalTimeChoices.choices, default=IntervalTimeChoices.none)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    client_phone = models.CharField(max_length=15, blank=True)
    is_active = models.BooleanField(default=True)
    is_instant = models.BooleanField(default=False)
    groups = models.ManyToManyField(Channel, blank=True, related_name="mailing_groups")
    send_time = ArrayField(models.DateTimeField(null=True), blank=True, null=True, default=list)

    def __str__(self):
        return self.message_title if self.message_title != '' else self.id


class ParsedMailing:
    id: int
    title: str = ''
    text: str = ''
    images: int = 0
    files: int = 0
    groups: str
    date_format: int
    begin_time: str = None
    end_time: str = None
    interval_duration: int = None
    interval_time: str = None
    dates: str = None
    is_active: str
    is_instant: bool
    client_phone: str

    def __init__(self, mailing: MailingRequest, groups: list[Channel], images: list[File], files: list[File]):
        data = {
            'weeks': 'недель',
            'days': 'дней',
            'hours': 'часов',
            'minutes': 'минут',
            'none': '',
        }

        self.id = mailing.id
        self.title = mailing.message_title
        self.text = mailing.message_text
        self.images = len(images)
        self.files = len(files)

        new_groups = list()
        for group in groups:
            new_groups.append(group.title)

        self.groups = ' ; '.join(new_groups)
        self.date_format = mailing.date_format if mailing.date_format is not None else 3
        self.begin_time = timezone.make_aware(timezone.make_naive(mailing.begin_time)).strftime('%Y-%m-%d %H:%M') if mailing.begin_time is not None else None
        self.end_time = timezone.make_aware(timezone.make_naive(mailing.end_time)).strftime('%Y-%m-%d %H:%M') if mailing.end_time is not None else None
        self.interval_duration = mailing.interval_duration
        self.interval_time = data[mailing.interval_time] if mailing.interval_time is not None else None
        self.dates = ' ; '.join([timezone.make_aware(timezone.make_naive(time)).strftime('%Y-%m-%d %H:%M') for time in mailing.send_time])
        self.is_active = 'Активно' if mailing.is_active else 'Не активно'
        self.is_instant = mailing.is_instant
        self.client_phone = mailing.client_phone

