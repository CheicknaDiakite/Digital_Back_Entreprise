# permissions.py
from rest_framework.permissions import BasePermission

from .role_restriction import is_user_allowed


class RoleTimePermission(BasePermission):
    def has_permission(self, request, view):
        return is_user_allowed(request.user)
