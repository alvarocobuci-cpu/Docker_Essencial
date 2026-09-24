from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """
    Permite acesso somente a usuários do grupo admin.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name='admin').exists()
        )