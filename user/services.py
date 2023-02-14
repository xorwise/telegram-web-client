from user.models import CustomUser
from asgiref.sync import sync_to_async
from django.core.exceptions import ValidationError

async def get_user(email: str) -> CustomUser:
    """ Get user object by email """
    user = await sync_to_async(lambda: CustomUser.objects.get(email=email), thread_sensitive=True)()
    return user


async def get_user_by_phone(phone: str) -> CustomUser:
    """ Get user object by phone number """
    return await sync_to_async(lambda: CustomUser.objects.get(phone=phone), thread_sensitive=True)()


async def validate_password(password1: str, password2: str) -> bool:
    if len(password1) < 8:
        raise ValidationError('Пароль слишком короткий!')
    if password1 != password2:
        raise ValidationError('Пароли не совпадают!')
    return True


async def validate_phone(phone: str) -> bool:
    if phone[0] != '+' or phone.count(' ') > 0 or phone.count('-') > 0 or len(phone) > 15:
        raise ValidationError('Введите номер телефона в правильном формате: +79000000000')
    return True
