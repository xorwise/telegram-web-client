from django.db import models
from django.contrib.postgres.fields import ArrayField
from datetime import datetime
import nest_asyncio
import asyncio
from telethon.sync import TelegramClient
from telethon.tl.types import PeerChannel


class Channel(models.Model):
    id = models.BigIntegerField(primary_key=True)
    title = models.CharField(max_length=255, blank=True)


class SearchRequest(models.Model):
    id = models.AutoField(primary_key=True)
    client = models.IntegerField()
    channels = ArrayField(models.CharField(max_length=255))
    keywords = ArrayField(models.CharField(max_length=100))
    groups = models.ManyToManyField(Channel, related_name='groups', blank=True)
    is_active = models.BooleanField(default=True)
    added_messages = ArrayField(models.IntegerField(), blank=True, default=list)


class ParsedRequest:
    id: int
    channels: str
    keywords: str
    groups: str
    last_checked: str
    is_active: bool

    def __init__(self, request: SearchRequest):
        self.id = request.id
        self.channels = request.channels
        new_groups = list()
        for group in list(request.groups.all()):
            new_groups.append(group.title)
        self.keywords = '; '.join(request.keywords)
        self.groups = '; '.join(new_groups)
        self.is_active = request.is_active




