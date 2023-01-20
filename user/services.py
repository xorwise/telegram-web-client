from user.models import CustomUser


def get_user(username: str) -> CustomUser:
    return CustomUser.objects.get(username=username)
