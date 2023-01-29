from user.models import CustomUser
from asgiref.sync import sync_to_async


async def get_user(email: str) -> CustomUser:
    """ Get user object by email """
    user = await sync_to_async(lambda: CustomUser.objects.get(email=email), thread_sensitive=True)()
    return user


async def get_user_by_phone(phone: str) -> CustomUser:
    """ Get user object by phone number """
    return await sync_to_async(lambda: CustomUser.objects.get(phone=phone), thread_sensitive=True)()


async def validate_password(password1: str, password2: str) -> bool:
    if len(password1) < 8:
        return False
    if password1 != password2:
        return False
    return True
