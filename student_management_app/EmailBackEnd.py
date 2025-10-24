from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackEnd(ModelBackend):
    def authenticate(self, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            # Use filter instead of get to handle multiple users
            users = UserModel.objects.filter(email=username)
            # Get the first active user with matching credentials
            for user in users:
                if user.check_password(password):
                    return user
            return None
        except UserModel.DoesNotExist:
            return None
