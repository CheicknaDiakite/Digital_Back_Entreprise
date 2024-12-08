import os
from functools import wraps

from django.contrib.auth.models import Permission
from django.http import JsonResponse
from django.utils import timezone

from utilisateur.models import Token


def token_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        token_str = request.headers.get('Authorization')
        if not token_str:
            return JsonResponse({'message': 'Authentification requise !', 'etat': False}, status=401)

        # if token_str.startswith('Token '):
        #     token_str = token_str.split(' ')[1]

        try:
            token = Token.objects.get(token=token_str)
            request.user = token.user
        except Token.DoesNotExist:
            return JsonResponse({'message': 'Token invalide', 'etat': False}, status=401)

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def assign_permissions_to_group(group, permissions):
    for perm_codename in permissions:
        perm = Permission.objects.get(codename=perm_codename)
        if not group.permissions.filter(id=perm.id).exists():
            group.permissions.add(perm)


def get_facture_upload_to(instance, filename):
    # Récupérer la date actuelle pour déterminer la semaine de l'année
    current_date = timezone.now()
    week_number = current_date.strftime('%U')  # Obtient le numéro de la semaine
    year = current_date.year  # L'année en cours

    # Créez un chemin dynamique basé sur l'année et le numéro de la semaine
    return os.path.join(f'factures/{year}/semaine_{week_number}', filename)


def get_image_upload_to(instance, filename):
    # Récupérer la date actuelle pour déterminer la semaine de l'année
    current_date = timezone.now()
    week_number = current_date.strftime('%U')  # Obtient le numéro de la semaine
    year = current_date.year  # L'année en cours

    # Créez un chemin dynamique basé sur l'année et le numéro de la semaine
    return os.path.join(f'images/{year}/semaine_{week_number}', filename)
