from user.models import CustomUser
from asgiref.sync import sync_to_async


async def get_user(email: str) -> CustomUser:
    user = await sync_to_async(lambda: CustomUser.objects.get(email=email), thread_sensitive=True)()
    return user
