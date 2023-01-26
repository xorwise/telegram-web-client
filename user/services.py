from user.models import CustomUser
from asgiref.sync import sync_to_async


async def get_user(username: str) -> CustomUser:
    user = await sync_to_async(lambda: CustomUser.objects.get(username=username), thread_sensitive=True)()
    return user
