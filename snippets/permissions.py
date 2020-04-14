from rest_framework import permissions, exceptions
from datetime import timedelta
import datetime
import pytz


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj): # This is the property checked by views in default permissions
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the snippet.
        return obj.owner == request.user


class IsOwnerOrNothing(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj): # This is the property checked by views in default permissions
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        # if request.method in permissions.SAFE_METHODS:
        #     return True
        #
        # # Write permissions are only allowed to the owner of the snippet.
        return obj.owner == request.user

# For an expiring token (there is no built in method)
from rest_framework.authentication import TokenAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

class ExpiringTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        try:
            token = self.model.objects.get(key=key)
        except self.model.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token')

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted')

        # This is required for the time comparison
        utc_now = datetime.utcnow()
        utc_now = utc_now.replace(tzinfo=pytz.utc)

        if token.created < utc_now - timedelta(hours=24):
            raise exceptions.AuthenticationFailed('Token has expired')

        return token.user, token
