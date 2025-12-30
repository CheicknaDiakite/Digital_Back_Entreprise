import json
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from io import BytesIO
from itertools import chain

import qrcode
from PIL import ImageFont, ImageDraw, Image
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db.models import Sum, Q, Count, F, Func, IntegerField
from django.db.models.functions import TruncWeek, TruncMonth
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from fonction import token_required

from .models import Entreprise, Categorie, SousCategorie, Entrer, Sortie, FactSortie, Depense, FactEntre, \
    HistoriqueEntrer, HistoriqueSortie, Client, PaiementEntreprise, Avi
from utilisateur.models import Utilisateur, Licence

# from root.outil import get_order_id

from root.code_paiement import entreprise_order_id_len

from root.outil import get_order_id, verifier_numero, paiement_orange, paiement_moov, sama_pay, stripe_pay, \
    verifier_status, regenerate_qrcode
from .serializers import CategorieSerializer, EntrepriseSerializer, ClientSerializer, DepenseSerializer, \
    EntrerSerializer, SortieSerializer


def handel404(request, exception):
    return render(request, 'pag_404.html', status=404)


# Create your views here.

# Pour les avis

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_avis(request):
    response_data = {'message': "Requete invalide", 'etat': False}

    if request.method == "POST":

        try:
            form = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({'message': "Erreur lors de la lecture des donnees JSON", 'etat': False})

        libelle = form.get("libelle")
        description = form.get("description")
        admin_id = form.get("user_id")

        if admin_id:

            admin = Utilisateur.objects.all().filter(uuid=admin_id).first()

            if admin:
                # if admin.has_perm('entreprise.add_depense'):
                if admin.groups.filter(name="Admin").exists():

                    new_livre = Avi(description=description, libelle=libelle, utilisateur=admin)
                    new_livre.save()

                    response_data["etat"] = True
                    response_data["id"] = new_livre.id
                    response_data["message"] = "success"

                else:
                    # L'utilisateur n'a pas la permission d'ajouter une catégorie
                    response_data["message"] = "Vous n'avez pas la permission d'envoyer un avis."
            else:
                return JsonResponse({'message': "Admin non trouvee", 'etat': False})

        else:
            response_data["message"] = "ID de l'utilisateur manquant !"

    return JsonResponse(response_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_avis(request):
    response_data = {'message': "Requete invalide", 'etat': False, 'donnee': []}

    if request.method == "POST":
        try:
            form = json.loads(request.body.decode("utf-8"))
        except:
            return JsonResponse({'message': "Erreur lors de le lecture des donnees JSON", 'etat': False})

        all_livre = Sortie.objects.all()
        filtrer = False

        user_id = form.get("user_id")
        if user_id:

            user = Utilisateur.objects.filter(uuid=user_id).first()

            if user:
                if user.groups.filter(name="Admin").exists():

                    livre_all = form.get("all")
                    if livre_all:
                        all_livre = Avi.objects.all()
                        filtrer = True

                    if filtrer:
                        # print(filtrer)
                        data = []
                        for liv in all_livre:
                            data.append({
                                "id": liv.id,
                                "uuid": liv.uuid,
                                "libelle": liv.libelle,
                                "description": liv.description,
                                "date": str(liv.created_at),
                            })

                        if data:
                            response_data["etat"] = True
                            response_data["message"] = "success"
                            response_data["donnee"] = data
                        else:
                            response_data["message"] = "Aucun avis effectuer."
                else:
                    # L'utilisateur n'a pas la permission d'ajouter une catégorie
                    response_data["message"] = "Vous n'avez pas la permission de voir les avis."
            else:
                response_data["message"] = "Utilisateur non trouvé."
    return JsonResponse(response_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def del_avis(request):
    response_data = {'message': "Requete invalide", 'etat': False}

    if request.method == "POST":
        try:
            form = json.loads(request.body.decode("utf-8"))
            id = form.get("uuid")
            slug = form.get("slug")
            user_id = form.get("user_id")
        except json.JSONDecodeError:
            return JsonResponse({'message': "Erreur lors de la lecture des donnees JSON", 'etat': False})

        user = Utilisateur.objects.filter(uuid=user_id).first()

        if user:
            # if user.has_perm('entreprise.delete_depense'):
            if user.groups.filter(name="Admin").exists():
                if id or slug:
                    if id:
                        livre_from_database = Avi.objects.filter(uuid=id).first()
                    else:
                        livre_from_database = Avi.objects.filter(slug=slug).first()

                    if not livre_from_database:
                        response_data["message"] = "Depense non trouvée"
                    else:
                        livre_from_database.delete()
                        response_data["etat"] = True
                        response_data["message"] = "Success"
                else:
                    response_data["message"] = "ID ou slug de l'avis manquant"
            else:
                # L'utilisateur n'a pas la permission d'ajouter une catégorie
                response_data["message"] = "Vous n'avez pas la permission de supprimer un Avis."
        else:
            response_data["message"] = "Utilisateur non trouvé."
    return JsonResponse(response_data)


# Pour les Entreprise

# @csrf_exempt
# @token_required
# def add_entreprise(request):
#     response_data = {'message': "requête invalide", 'etat': False}
#
#     if request.method == "POST":
#         try:
#             form = json.loads(request.body.decode("utf-8"))
#         except json.JSONDecodeError:
#             return JsonResponse({'message': "Erreur lors de la lecture des données JSON", 'etat': False})
#
#         nom = form.get("nom")
#         adresse = form.get("adresse")
#         numero = form.get("numero")
#         email = form.get("email")
#         libelle = form.get("libelle")
#         user_id = form.get("user_id")
#         type_licence = form.get("type_licence", 1)  # Licence par défaut
#         user = Utilisateur.objects.filter(uuid=user_id).first()
#
#         if user:
#
#             if user.entreprises.count() >= 3:
#                 response_data["message"] = "Vous possédez déjà plus de 3 entreprises."
#                 return JsonResponse(response_data)
#
#             # Créer une licence associée à la entreprise
#             if type_licence == 1:
#                 date_expiration = datetime.now().date() + timedelta(days=30)  # Licence gratuite de 30 jours
#             elif type_licence == 2:
#                 date_expiration = datetime.now().date() + timedelta(days=180)  # Licence de 6 mois
#             elif type_licence == 3:
#                 date_expiration = datetime.now().date() + timedelta(days=365)  # Licence d'un an
#             else:
#                 response_data['message'] = "Type de licence invalide."
#                 return JsonResponse(response_data)
#
#             # Créer et associer la licence à la entreprise
#             licence = Licence.objects.create(type=type_licence, date_expiration=date_expiration)
#
#             # Vérification des permissions de l'utilisateur
#             # if user.has_perm('entreprise.add_entreprise'):
#             if user.groups.filter(name="Admin").exists():
#
#                 entreprise = Entreprise.objects.create(
#                     nom=nom,
#                     adresse=adresse,
#                     libelle=libelle,
#                     numero=numero,
#                     email=email,
#                     licence=licence
#                 )
#
#                 entreprise.utilisateurs.add(user)
#
#                 response_data["etat"] = True
#                 response_data["id"] = entreprise.id
#                 # response_data["slug"] = new_entreprise.slug
#                 response_data["message"] = "success"
#             else:
#                 # L'utilisateur n'a pas la permission d'ajouter une catégorie
#                 response_data["message"] = "Vous n'avez pas la permission d'ajouter une entreprise."
#         else:
#             response_data["message"] = "Utilisateur non trouvé."
#
#         # Autres cas d'erreurs...
#     return JsonResponse(response_data)

class AddEntrepriseView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = EntrepriseSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            entreprise = serializer.save()
            return Response({
                "etat": True,
                "id": entreprise.id,
                "message": "success"
            }, status=status.HTTP_201_CREATED)
        return Response({
            "etat": False,
            "message": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(["Get"])
@permission_classes([IsAuthenticated])
def get_entreprise_un(request, uuid):
    response_data = {'message': "requette invalide", 'etat': False}
    entreprise = Entreprise.objects.all().filter(uuid=uuid).first()

    if entreprise:
        if entreprise.licence:
            # Si la entreprise a une licence, récupérer ses informations
            licence_data = {
                "licence_active": entreprise.licence.active,
                "licence_type": entreprise.licence.get_type_display(),
                "licence_code": entreprise.licence.code,
                "licence_date_expiration": entreprise.licence.date_expiration,
            }
        else:
            # Si la entreprise n'a pas de licence
            licence_data = {
                "licence_active": None,
                "licence_type": None,
                "licence_code": None,
                "licence_date_expiration": None,
            }
        entreprise_data = {
            "id": entreprise.id,
            "uuid": entreprise.uuid,
            "nom": entreprise.nom,
            "adresse": entreprise.adresse,
            "libelle": entreprise.libelle,
            "ref": entreprise.ref,
            "email": entreprise.email,
            "pays": entreprise.pays,
            "coordonne": entreprise.coordonne,
            "numero": entreprise.numero,
            "image": entreprise.image.url if entreprise.image else None,
            # "slug": entreprise.slug,
            **licence_data  # Ajouter les informations de la licence
        }

        response_data["etat"] = True
        response_data["donnee"] = entreprise_data
        response_data["message"] = "success"
    else:
        response_data["message"] = "Entreprise non trouver"

    return JsonResponse(response_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def remove_user_from_entreprise(request):
    response_data = {'message': "Requête invalide", 'etat': False}

    if request.method == "POST":
        try:
            form = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({'message': "Erreur lors de la lecture des données JSON", 'etat': False})

        entreprise_id = form.get("entreprise_id")
        user_id = form.get("user_id")
        admin_id = form.get("admin_id")

        # Récupérer l'utilisateur
        admin = Utilisateur.objects.filter(uuid=admin_id).first()

        if admin:
            # Vérifier que l'utilisateur a la permission de modifier la entreprise
            if admin.groups.filter(name="Admin").exists():
                # if admin.has_perm('entreprise.change_entreprise'):
                # Récupérer la entreprise et l'utilisateur
                entreprise = Entreprise.objects.filter(uuid=entreprise_id).first()
                user = Utilisateur.objects.filter(uuid=user_id).first()

                if entreprise:
                    # Vérifier que l'utilisateur est bien associé à la entreprise
                    if entreprise.utilisateurs.filter(id=user.id).exists():
                        # Retirer l'utilisateur de la entreprise
                        entreprise.utilisateurs.remove(user)

                        response_data["etat"] = True
                        response_data["message"] = "L'utilisateur a été retiré de la entreprise avec succès."
                    else:
                        response_data["message"] = "Cet utilisateur n'est pas associé à cette entreprise."
                else:
                    response_data["message"] = "entreprise non trouvée."
            else:
                response_data["message"] = "Permission refusée pour cet utilisateur."
        else:
            response_data["message"] = "Utilisateur non trouvé."

    return JsonResponse(response_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def del_entreprise(request):
    response_data = {'message': "Requête invalide", 'etat': False}

    if request.method == "POST":
        try:
            form = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({'message': "Erreur lors de la lecture des données JSON", 'etat': False})

        id = form.get("uuid")
        slug = form.get("slug")
        user_id = form.get("user_id")

        if not user_id:
            response_data["message"] = "ID de l'utilisateur requis."
            return JsonResponse(response_data)

        user = Utilisateur.objects.filter(uuid=user_id).first()
        if not user:
            response_data["message"] = "Utilisateur non trouvé."
            return JsonResponse(response_data)

        if not user.groups.filter(name="Admin").exists():
            response_data["message"] = "Vous n'avez pas la permission de supprimer une entreprise."
            return JsonResponse(response_data)

        # Rechercher l'entreprise par UUID ou slug
        entreprise = None
        if id:
            entreprise = Entreprise.objects.filter(uuid=id).first()
        elif slug:
            entreprise = Entreprise.objects.filter(nom__iexact=slug).first()

        if not entreprise:
            response_data["message"] = "Entreprise non trouvée."
            return JsonResponse(response_data)

        # Vérifier les catégories associées
        categories = Categorie.objects.filter(entreprise=entreprise)
        utilisateurs = entreprise.utilisateurs.all()

        if categories.exists():
            response_data[
                "message"] = f"Impossible de supprimer : cette entreprise possède {categories.count()} catégorie(s)."
            return JsonResponse(response_data)

        # Vérifier les utilisateurs associés
        if utilisateurs.exists():
            response_data[
                "message"] = f"Impossible de supprimer : cette entreprise possède {utilisateurs.count()} utilisateur(s)."
            return JsonResponse(response_data)

        # Si aucune dépendance, supprimer l'entreprise
        entreprise.delete()
        response_data["etat"] = True
        response_data["message"] = "Entreprise supprimée avec succès."

    return JsonResponse(response_data)


# @csrf_exempt
# @token_required
# def del_entreprise(request):
#     response_data = {'message': "requette invalide", 'etat': False}
#
#     if request.method == "POST":
#         form = dict()
#         try:
#             form = json.loads(request.body.decode("utf-8"))
#         except:
#             return JsonResponse({'message': "Erreur lors de le lecture des donnees JSON", 'etat': False})
#
#         if "id" in form or "slug" in form and "user_id" in form:
#             id = form.get("uuid")
#             slug = form.get("slug")
#             user_id = form.get("user_id")
#             user = Utilisateur.objects.filter(uuid=user_id).first()
#
#             if user:
#                 if user.groups.filter(name="Admin").exists():
#                     # if user.has_perm('entreprise.delete_entreprise'):
#                     if id:
#                         entreprise_from_database = Entreprise.objects.all().filter(uuid=id).first()
#                     else:
#                         entreprise_from_database = Entreprise.objects.all().filter(slug=slug).first()
#
#                     if not entreprise_from_database:
#                         response_data["message"] = "categorie non trouvé"
#                     else:
#                         if len(entreprise_from_database.categorie) > 0:
#                             response_data[
#                                 "message"] = f"cette entreprise possède {len(entreprise_from_database.sous_categorie)} categorie"
#                         else:
#                             entreprise_from_database.delete()
#                             response_data["etat"] = True
#                             response_data["message"] = "success"
#                 else:
#                     # L'utilisateur n'a pas la permission d'ajouter une catégorie
#                     response_data["message"] = "Vous n'avez pas la permission de supprimer une entreprise."
#             else:
#                 response_data["message"] = "Utilisateur non trouvé."
#     return JsonResponse(response_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_entreprise(request):
    response_data = {'message': "requette invalide", 'etat': False}

    if request.method == "POST":
        form = dict()
        try:
            form = json.loads(request.body.decode("utf-8"))
        except:
            return JsonResponse({'message': "Erreur lors de le lecture des donnees JSON", 'etat': False})

        all_entreprise = Entreprise.objects.all()
        filtrer = False

        if "id" in form or "slug" in form or "all" in form and "user_id" in form:
            entreprise_id = form.get("id")
            slug = form.get("slug")
            entreprise_all = form.get("all")
            user_id = form.get("user_id")
            user = Utilisateur.objects.filter(id=user_id).first()

            if user:
                if user.groups.filter(name="Admin").exists():
                    # if user.has_perm('entreprise.view_entreprise'):

                    if entreprise_id:
                        all_entreprise = all_entreprise.filter(id=entreprise_id)
                        filtrer = True

                    if slug:
                        all_entreprise = all_entreprise.filter(slug=slug)
                        filtrer = True

                    if entreprise_all:
                        all_entreprise = Entreprise.objects.all()
                        filtrer = True

                    if filtrer:

                        entreprises = list()
                        for c in all_entreprise:
                            entreprises.append(
                                {
                                    "id": c.id,
                                    "nom": c.nom,
                                    "adresse": c.adresse,
                                    "libelle": c.libelle,
                                    "ref": c.ref,
                                    "email": c.email,
                                    "numero": c.numero,
                                    # "categorie_count": c.categorie.count(),
                                    # "image": c.image.url if c.image else None,
                                }
                            )
                        if entreprises:
                            response_data["etat"] = True
                            response_data["donnee"] = entreprises
                            response_data["message"] = "success"
                        else:
                            response_data["message"] = "Aucun entreprise trouver"
                else:
                    # L'utilisateur n'a pas la permission d'ajouter une catégorie
                    response_data["message"] = "Vous n'avez pas la permission de voir les entreprise."
            else:
                response_data["message"] = "Utilisateur non trouvé."
    return JsonResponse(response_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_entreprise(request):
    response_data = {'message': "requête invalide", 'etat': False}

    if request.method == "POST":
        form = request.POST
        image = request.FILES.get('image')

        if "id" in form or "slug" in form and "user_id" in form:
            entreprise_id = form.get("uuid")
            slug = form.get("slug")
            user_id = form.get("user_id")
            user = Utilisateur.objects.filter(uuid=user_id).first()

            if user:
                if user.groups.filter(name="Admin").exists() or user.groups.filter(name="Editor").exists():
                    # if user.has_perm('entreprise.change_categorie'):
                    if entreprise_id:
                        categorie_from_database = Entreprise.objects.all().filter(uuid=entreprise_id).first()
                    else:
                        categorie_from_database = Entreprise.objects.all().filter(slug=slug).first()

                    if not categorie_from_database:
                        response_data["message"] = "catégorie non trouvée"
                    else:
                        modifier = False

                        nom = form.get("nom")
                        if nom:
                            categorie_from_database.nom = nom
                            modifier = True

                        pays = form.get("pays")
                        if pays:
                            categorie_from_database.pays = pays
                            modifier = True

                        coordonne = form.get("coordonne")
                        if coordonne:
                            categorie_from_database.coordonne = coordonne
                            modifier = True

                        if image:
                            categorie_from_database.image = image
                            modifier = True

                        adresse = form.get("adresse")
                        if adresse:
                            categorie_from_database.adresse = adresse
                            modifier = True

                        libelle = form.get("libelle")
                        if libelle:
                            categorie_from_database.libelle = libelle
                            modifier = True

                        numero = form.get("numero")
                        if numero:
                            categorie_from_database.numero = numero
                            modifier = True

                        email = form.get("email")
                        if email:
                            categorie_from_database.email = email
                            modifier = True

                        code = form.get("code")
                        if code:
                            # Vérifier si une licence avec ce code existe dans la base de données
                            licence_from_database = Licence.objects.filter(code=code).first()
                            if licence_from_database:
                                # Vérifier si une autre entreprise utilise déjà cette licence
                                entreprise_with_same_licence = Entreprise.objects.filter(
                                    licence=licence_from_database).exclude(uuid=categorie_from_database.uuid).first()
                                if entreprise_with_same_licence:
                                    response_data["etat"] = False
                                    response_data[
                                        "message"] = "Le code est invalide"
                                    modifier = False
                                else:
                                    # Aucun conflit, on peut assigner la licence à l'entreprise
                                    categorie_from_database.licence = licence_from_database
                                    modifier = True
                            else:
                                response_data["etat"] = False
                                response_data["message"] = "Code non trouvé."
                                modifier = False

                        if modifier:
                            categorie_from_database.save()
                            response_data["etat"] = True
                            response_data["message"] = "success"
                else:
                    response_data["message"] = "Vous n'avez pas la permission de modifier les catégories."
            else:
                response_data["message"] = "Utilisateur non trouvé."

    return JsonResponse(response_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_utilisateur_entreprise(request, uuid):
    try:
        # Récupérer l'utilisateur avec l'ID donné
        utilisateur = Utilisateur.objects.get(uuid=uuid)

        # Récupérer les entreprises associées à cet utilisateur
        entreprises = utilisateur.entreprises.all()

        # Préparer les données de la réponse
        entreprises_data = []
        for entreprise in entreprises:
            if entreprise.licence:
                # Si la entreprise a une licence, récupérer ses informations
                licence_data = {
                    "licence_active": entreprise.licence.active,
                    "licence_type": entreprise.licence.get_type_display(),
                    "licence_code": entreprise.licence.code,
                    "licence_date_expiration": entreprise.licence.date_expiration,
                }
            else:
                # Si la entreprise n'a pas de licence
                licence_data = {
                    "licence_active": None,
                    "licence_type": None,
                    "licence_code": None,
                    "licence_date_expiration": None,
                }

            entreprise_data = {
                "id": entreprise.id,
                "uuid": entreprise.uuid,
                "nom": entreprise.nom,
                "adresse": entreprise.adresse,
                "ref": entreprise.ref,
                "numero": entreprise.numero,
                "email": entreprise.email,
                "coordonne": entreprise.coordonne,
                "libelle": entreprise.libelle,
                "image": entreprise.image.url if entreprise.image else None,
                # livre.facture.url if livre.facture else None
                **licence_data  # Ajouter les informations de la licence
            }
            entreprises_data.append(entreprise_data)

        # response_data = {
        #     "etat": True,
        #     "message": "entreprises récupérées avec succès",
        #     "donnee": entreprises_data
        # }
        response_data = {
            "etat": True,
            "message": "entreprises récupérées avec succès",
            "donnee": entreprises_data
        }

    except Utilisateur.DoesNotExist:
        response_data = {
            "etat": False,
            "message": "Utilisateur non trouvé"
        }

    return JsonResponse(response_data)


class EntrepriseUtilisateursView(APIView):
    def get(self, request, uuid):
        try:
            # Récupérer la entreprise avec l'ID donné
            entreprise = Entreprise.objects.get(uuid=uuid)

            # Récupérer tous les utilisateurs associés à cette entreprise
            utilisateurs = entreprise.utilisateurs.all()

            # Préparer les données de la réponse
            utilisateurs_data = [
                {
                    "id": utilisateur.id,
                    "uuid": utilisateur.uuid,
                    "username": utilisateur.username,
                    "email": utilisateur.email,
                    "first_name": utilisateur.first_name,
                    "last_name": utilisateur.last_name,
                    "role": utilisateur.get_role_display(),
                }
                for utilisateur in utilisateurs
            ]

            response_data = {
                "etat": True,
                "message": "Utilisateurs récupérés avec succès",
                "donnee": utilisateurs_data
            }
        except Entreprise.DoesNotExist:
            response_data = {
                "etat": False,
                "message": "Entreprise non trouvée"
            }

        return JsonResponse(response_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_somme_qte_pu_sortie(request, entreprise_id, user_id):
    try:
        utilisateur = Utilisateur.objects.get(uuid=user_id)
        entreprise = Entreprise.objects.get(uuid=entreprise_id, utilisateurs=utilisateur)

        categories = Categorie.objects.filter(entreprise=entreprise)
        souscategories = SousCategorie.objects.filter(categorie__in=categories)
        entrers = Entrer.objects.filter(souscategorie__in=souscategories)
        sorties = Sortie.objects.filter(entrer__in=entrers)

        # Totaux globaux
        total_sortie_qte = sorties.aggregate(total_qte=Sum('qte'))['total_qte'] or 0
        total_entrer_qte = entrers.aggregate(total_qte=Sum('qte'))['total_qte'] or 0
        total_sortie_pu = sum(sortie.prix_total for sortie in sorties)
        total_entrer_pu = sum(entrer.prix_total for entrer in entrers)

        count_entrer = entrers.count()
        count_sortie = sorties.count()

        # ➤ Nouveaux totaux groupés par mois pour les Entrées
        details_entrer_par_mois = {}
        for item in entrers.annotate(month=TruncMonth('created_at')).values('month').annotate(
                somme_qte=Sum('qte'),
                somme_prix_total=Sum('pu')
        ).order_by('month'):
            mois = item['month'].strftime("%B %Y")
            details_entrer_par_mois[mois] = {
                "somme_qte": item['somme_qte'],
                "somme_prix_total": item['somme_prix_total']
            }

        # ➤ Nouveaux totaux groupés par mois pour les Sorties
        details_sortie_par_mois = {}
        for item in sorties.annotate(month=TruncMonth('created_at')).values('month').annotate(
                somme_qte=Sum('qte'),
                somme_prix_total=Sum(F('pu') * F('qte'))
        ).order_by('month'):
            mois = item['month'].strftime("%B %Y")
            details_sortie_par_mois[mois] = {
                "somme_qte": item['somme_qte'],
                "somme_prix_total": item['somme_prix_total']
            }

        # Comptages par mois (enregistrements)
        count_entrer_par_mois = entrers.annotate(month=TruncMonth('created_at')).values('month').annotate(
            count=Count('id')
        ).order_by('month')

        count_sortie_par_mois = sorties.annotate(month=TruncMonth('created_at')).values('month').annotate(
            count=Count('id')
        ).order_by('month')

        data = {
            "somme_sortie_qte": total_sortie_qte,
            "somme_sortie_pu": total_sortie_pu,
            "somme_entrer_qte": total_entrer_qte,
            "somme_entrer_pu": total_entrer_pu,
            "nombre_entrer": count_entrer,
            "nombre_sortie": count_sortie,
            "details_entrer_par_mois": details_entrer_par_mois,
            "details_sortie_par_mois": details_sortie_par_mois,
            "count_entrer_par_mois": list(count_entrer_par_mois),
            "count_sortie_par_mois": list(count_sortie_par_mois),
        }

        response_data = {
            "etat": True,
            "message": "Quantité, prix et détails agrégés par mois récupérés avec succès",
            "donnee": data
        }

    except Utilisateur.DoesNotExist:
        response_data = {"etat": False, "message": "Utilisateur non trouvé"}
    except Entreprise.DoesNotExist:
        response_data = {"etat": False, "message": "Entreprise non trouvée pour cet utilisateur"}

    return JsonResponse(response_data)


# @csrf_exempt
# @token_required
# def api_count_sortie_par_utilisateur(request, entreprise_id):
#     try:
#         entreprise = Entreprise.objects.get(uuid=entreprise_id)
#     except Entreprise.DoesNotExist:
#         return JsonResponse({'etat': False, 'message': "Entreprise non trouvée"})
#
#     # Base queryset des sorties de l'entreprise
#     qs = Sortie.objects.filter(
#         entrer__souscategorie__categorie__entreprise=entreprise
#     ).select_related('created_by')
#
#     # ————————————————————————————
#     # 1) Total des qte vendues par utilisateur
#     # ————————————————————————————
#     total_par_user = (
#         qs
#         .values('created_by__username')
#         .annotate(total_qte=Sum('qte'))
#         .order_by('-total_qte')
#     )
#     # formaté en liste de { username, total_qte }
#     total_par_utilisateur = [
#         {'username': rec['created_by__username'], 'total_qte': rec['total_qte'] or 0}
#         for rec in total_par_user
#     ]
#
#     total_par_user = (
#         qs.values('created_by__id', 'created_by__username')
#         .annotate(total=Count('id'))
#         .order_by('-total')
#     )
#
#     # ————————————————————————————
#     # 2) Total des qte vendues par utilisateur **par mois**
#     # ————————————————————————————
#     qs_monthly = (
#         qs
#         .annotate(mois=TruncMonth('created_at'))
#         .values('created_by__username', 'mois')
#         .annotate(somme_qte=Sum('qte'))
#         .order_by('created_by__username', 'mois')
#     )
#
#     mensuel_par_utilisateur = [
#         {
#             'username': rec['created_by__username'] or "Inconnu",
#             'mois': rec['mois'].strftime("%B %Y"),
#             'total_qte': rec['somme_qte'] or 0
#         }
#         for rec in qs_monthly
#     ]
#
#     data = {
#         'total_par_utilisateur': total_par_utilisateur,
#         'total_nombre_vente': list(total_par_user),
#         # 'mensuel_par_utilisateur': mensuel_par_utilisateur,
#     }
#
#     return JsonResponse({
#         'etat': True,
#         'message': "Somme des quantités vendues par utilisateur (total et mensuel)",
#         'donnee': data
#     })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_count_sortie_par_utilisateur(request, entreprise_id):
    # Vérifier que l’entreprise existe
    try:
        entreprise = Entreprise.objects.get(uuid=entreprise_id)
    except Entreprise.DoesNotExist:
        return JsonResponse({'etat': False, 'message': "Entreprise non trouvée"}, status=404)

    # Base queryset des sorties liées à cette entreprise
    qs = Sortie.objects.filter(
        entrer__souscategorie__categorie__entreprise=entreprise
    ).select_related('created_by')

    # 1) Total des quantités vendues par utilisateur
    total_qte_par_user = (
        qs.values('created_by__id', 'created_by__username')
        .annotate(total_qte=Sum('qte'))
        .order_by('-total_qte')
    )

    total_par_utilisateur = [
        {
            'user_id': rec['created_by__id'],
            'username': rec['created_by__username'] or "Inconnu",
            'total_qte': rec['total_qte'] or 0
        }
        for rec in total_qte_par_user
    ]

    # 2) Nombre total de ventes (comptage des sorties) par utilisateur
    total_nombre_vente = (
        qs.values('created_by__id', 'created_by__username')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    # 3) Total des quantités vendues par utilisateur **par mois**
    qs_monthly = (
        qs.annotate(mois=TruncMonth('created_at'))
        .values('created_by__id', 'created_by__username', 'mois')
        .annotate(total_qte=Sum('qte'))
        .order_by('mois', 'created_by__username')
    )

    # Structurer les données par mois
    resultats_par_mois = []
    mois_groupes = defaultdict(list)

    for rec in qs_monthly:
        mois_str = rec['mois'].strftime('%B %Y').capitalize()
        mois_groupes[mois_str].append({
            'user_id': rec['created_by__id'],
            'username': rec['created_by__username'] or "Inconnu",
            'total_qte': rec['total_qte'] or 0
        })

    for mois, details in mois_groupes.items():
        resultats_par_mois.append({
            "month": mois,
            "details": details
        })

    # Résultats finaux
    data = {
        'total_par_utilisateur': total_par_utilisateur,
        'total_nombre_vente': list(total_nombre_vente),
        'mensuel_par_utilisateur': resultats_par_mois,
    }

    return JsonResponse({
        'etat': True,
        'message': "Somme des quantités vendues par utilisateur (total et mensuel)",
        'donnee': data
    })

# @csrf_exempt
# @token_required
# def api_somme_qte_pu_sortie(request, entreprise_id, user_id):
#     try:
#         # Récupérer l'utilisateur et l'entreprise
#         utilisateur = Utilisateur.objects.get(uuid=user_id)
#         entreprise = Entreprise.objects.get(uuid=entreprise_id, utilisateurs=utilisateur)
#
#         # Récupérer les catégories, sous-catégories, entrées et sorties
#         categories = Categorie.objects.filter(entreprise=entreprise)
#         souscategories = SousCategorie.objects.filter(categorie__in=categories)
#         entrers = Entrer.objects.filter(souscategorie__in=souscategories)
#         sorties = Sortie.objects.filter(entrer__in=entrers)
#
#         # Calculs des totaux
#         total_sortie_qte = sorties.aggregate(total_qte=Sum('qte'))['total_qte'] or 0
#         total_entrer_qte = entrers.aggregate(total_qte=Sum('qte'))['total_qte'] or 0
#         total_sortie_pu = sum(sortie.prix_total for sortie in sorties)
#         total_entrer_pu = sum(entrer.prix_total for entrer in entrers)
#
#         # Comptage des enregistrements
#         count_entrer = entrers.count()
#         count_sortie = sorties.count()
#
#         # Récupérer les entrées comptées par mois (enregistrements)
#         count_entrer_par_mois = entrers.annotate(
#             month=TruncMonth('created_at')
#         ).values('month').annotate(
#             count=Count('id')
#         ).order_by('month')
#
#         # Récupérer les sorties comptées par mois (enregistrements)
#         count_sortie_par_mois = sorties.annotate(month=TruncMonth('created_at')).values('month').annotate(
#             count=Count('id')).order_by('month')
#
#         # Récupérer les détails par mois pour les Entrées
#         details_entrer_par_mois = defaultdict(list)
#         for entrer in entrers.annotate(month=TruncMonth('created_at')):
#             month_name = datetime.strftime(entrer.month, "%B %Y")  # Ex: "December 2024"
#             details_entrer_par_mois[month_name].append({
#                 "id": entrer.id,
#                 "qte": entrer.qte,
#                 "pu": entrer.pu,
#                 "prix_total": entrer.prix_total,
#                 "created_at": entrer.created_at,
#                 # "souscategorie_nom": entrer.souscategorie.libelle
#             })
#
#         # Récupérer les détails par mois pour les Sorties
#         details_sortie_par_mois = defaultdict(list)
#         for sortie in sorties.annotate(month=TruncMonth('created_at')):
#             month_name = datetime.strftime(sortie.month, "%B %Y")  # Ex: "December 2024"
#             details_sortie_par_mois[month_name].append({
#                 "id": sortie.id,
#                 "qte": sortie.qte,
#                 "pu": sortie.pu,
#                 "prix_total": sortie.prix_total,
#                 "created_at": sortie.created_at,
#                 # "souscategorie_nom": sortie.entrer.souscategorie.libelle
#             })
#
#         # Construire la réponse avec les résultats
#         data = {
#             "somme_sortie_qte": total_sortie_qte,
#             "somme_sortie_pu": total_sortie_pu,
#             "somme_entrer_qte": total_entrer_qte,
#             "somme_entrer_pu": total_entrer_pu,
#             "nombre_entrer": count_entrer,
#             "nombre_sortie": count_sortie,
#             "details_entrer_par_mois": {
#                 str(month): details for month, details in details_entrer_par_mois.items()
#             },
#             "details_sortie_par_mois": {
#                 str(month): details for month, details in details_sortie_par_mois.items()
#             },
#             "count_entrer_par_mois": list(count_entrer_par_mois),
#             "count_sortie_par_mois": list(count_sortie_par_mois),
#         }
#
#         response_data = {
#             "etat": True,
#             "message": "Quantité, prix et détails récupérés avec succès",
#             "donnee": data
#         }
#
#     except Utilisateur.DoesNotExist:
#         response_data = {"etat": False, "message": "Utilisateur non trouvé"}
#     except Entreprise.DoesNotExist:
#         response_data = {"etat": False, "message": "Entreprise non trouvée pour cet utilisateur"}
#
#     return JsonResponse(response_data)


class ExtractWeek(Func):
    function = "EXTRACT"
    template = "%(function)s(WEEK FROM %(expressions)s)"
    output_field = IntegerField()  # Utilisez IntegerField pour la sortie


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sous_categories_sorties_par_mois(request, entreprise_uuid):
    try:
        date_actuelle = now()
        debut_annee = date_actuelle.replace(month=1, day=1)

        entreprise = Entreprise.objects.get(uuid=entreprise_uuid)

        sorties = Sortie.objects.filter(
            entrer__souscategorie__categorie__entreprise=entreprise,
            created_at__gte=debut_annee
        ).select_related('entrer__souscategorie')

        sorties_par_mois = sorties.annotate(
            mois=TruncMonth('created_at')
        ).values(
            'mois',
            'entrer__souscategorie__libelle'
        ).annotate(
            somme_qte=Sum('qte')  # ➤ Remplace Count par Sum ici
        ).order_by('mois')

        resultats_par_mois = []
        mois_actuel = None
        details = []

        for sortie in sorties_par_mois:
            mois = sortie['mois'].strftime("%B %Y")

            if mois_actuel and mois_actuel != mois:
                resultats_par_mois.append({
                    "month": mois_actuel,
                    "details": details
                })
                details = []

            details.append({
                "libelle": sortie['entrer__souscategorie__libelle'],
                "somme_qte": sortie['somme_qte']  # ➤ Nouveau champ
            })
            mois_actuel = mois

        if mois_actuel:
            resultats_par_mois.append({
                "month": mois_actuel,
                "details": details
            })

        data = {
            "annee": debut_annee.year,
            "sorties_par_mois": resultats_par_mois
        }

        response_data = {
            "etat": True,
            "message": "Données des quantités de sorties par mois récupérées avec succès",
            "donnee": data
        }

    except Entreprise.DoesNotExist:
        response_data = {"etat": False, "message": "Entreprise non trouvée"}
    except Exception as e:
        response_data = {"etat": False, "message": str(e)}

    return JsonResponse(response_data, safe=False)


class ClientCreateView(APIView):
    """
    Vue DRF pour créer un client
    """

    def post(self, request, *args, **kwargs):
        data = request.data

        # Champs obligatoires
        nom = data.get("nom")
        role = data.get("role")
        entreprise_id = data.get("entreprise_id")
        user_id = data.get("user_id")

        if not all([nom, role, entreprise_id]):
            return Response(
                {"etat": False, "message": "Les champs 'nom', 'role' et 'entreprise_id' sont obligatoires."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Vérification utilisateur
        user = request.user
        if not user:
            return Response({"etat": False, "message": "Utilisateur non trouvé."}, status=status.HTTP_404_NOT_FOUND)

        if not (user.groups.filter(name="Admin").exists() or user.groups.filter(name="Editor").exists()):
            return Response({"etat": False, "message": "Vous n'avez pas la permission d'ajouter un client."},
                            status=status.HTTP_403_FORBIDDEN)

        # Vérification entreprise
        entreprise = Entreprise.objects.filter(uuid=entreprise_id).first()
        if not entreprise:
            return Response({"etat": False, "message": "Entreprise non trouvée."}, status=status.HTTP_404_NOT_FOUND)

        # Sérialisation et création

        serializer = ClientSerializer(data=data)
        if serializer.is_valid():
            client = serializer.save(entreprise=entreprise)
            return Response(
                {"etat": True, "id": client.uuid, "message": "Client ajouté avec succès."},
                status=status.HTTP_201_CREATED,
            )

        return Response({"etat": False, "message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class ClientGetAPIView(APIView):
    def get(self, request, uuid):
        response_data = {'message': "requette invalide", 'etat': False}
        client = Client.objects.all().filter(uuid=uuid).first()

        if client:
            client_data = {
                "uuid": client.uuid,
                "nom": client.nom,
                "adresse": client.adresse,
                "email": client.email,
                "coordonne": client.coordonne,
                "role": client.role,
                "libelle": client.libelle,
                "numero": client.numero,
            }

            response_data["etat"] = True
            response_data["donnee"] = client_data
            response_data["message"] = "success"
        else:
            response_data["message"] = "client non trouver"

        return JsonResponse(response_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_client(request):
    response_data = {'message': "requête invalide", 'etat': False}

    if request.method == "POST":
        form = dict()
        try:
            form = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({'message': "Erreur lors de la lecture des données JSON", 'etat': False})

        if "uuid" in form or "slug" in form and "user_id" in form:
            entreprise_id = form.get("uuid")
            slug = form.get("slug")
            user_id = form.get("user_id")
            user = Utilisateur.objects.filter(uuid=user_id).first()

            if user:
                # if user.has_perm('entreprise.change_client'):
                if (user.groups.filter(name="Admin").exists()
                        or user.groups.filter(name="Editor").exists()
                        or user.groups.filter(name="Author").exists()
                ):
                    if entreprise_id:
                        categorie_from_database = Client.objects.all().filter(uuid=entreprise_id).first()
                    else:
                        categorie_from_database = Client.objects.all().filter(slug=slug).first()

                    if not categorie_from_database:
                        response_data["message"] = "catégorie non trouvée"
                    else:
                        modifier = False

                        nom = form.get("nom")
                        if nom:
                            categorie_from_database.nom = nom
                            modifier = True

                        adresse = form.get("adresse")
                        if adresse:
                            categorie_from_database.adresse = adresse
                            modifier = True

                        coordonne = form.get("coordonne")
                        if coordonne:
                            categorie_from_database.coordonne = coordonne
                            modifier = True

                        libelle = form.get("libelle")
                        if libelle:
                            categorie_from_database.libelle = libelle
                            modifier = True

                        entreprise_id = form.get("entreprise_id")
                        entreprise = Entreprise.objects.filter(uuid=entreprise_id).first()
                        if entreprise:
                            categorie_from_database.entreprise = entreprise
                            modifier = True
                        else:
                            response_data["message"] = "Ese n'est pas la."

                        numero = form.get("numero")
                        if numero:
                            categorie_from_database.numero = numero
                            modifier = True

                        email = form.get("email")
                        if email:
                            categorie_from_database.email = email
                            modifier = True

                        role = form.get("role")
                        if role:
                            categorie_from_database.role = role
                            modifier = True

                        if modifier:
                            categorie_from_database.save()
                            response_data["etat"] = True
                            response_data["message"] = "success"
                else:
                    response_data["message"] = "Vous n'avez pas la permission de modifier les catégories."
            else:
                response_data["message"] = "Utilisateur non trouvé."

    return JsonResponse(response_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def del_client(request):
    response_data = {'message': "requette invalide", 'etat': False}

    if request.method == "POST":
        form = dict()
        try:
            form = json.loads(request.body.decode("utf-8"))
        except:
            return JsonResponse({'message': "Erreur lors de le lecture des donnees JSON", 'etat': False})

        if "uuid" in form or "slug" in form and "user_id" in form:
            id = form.get("uuid")
            slug = form.get("slug")
            user_id = form.get("user_id")
            user = Utilisateur.objects.filter(uuid=user_id).first()

            if user:
                # if user.has_perm('entreprise.delete_client'):
                if (user.groups.filter(name="Admin").exists()
                        or user.groups.filter(name="Editor").exists()
                        or user.groups.filter(name="Author").exists()
                ):
                    if id:
                        categorie_from_database = Client.objects.all().filter(uuid=id).first()
                    else:
                        categorie_from_database = Client.objects.all().filter(slug=slug).first()

                    if not categorie_from_database:
                        response_data["message"] = "Client non trouvé"
                    else:
                        categorie_from_database.delete()
                        response_data["etat"] = True
                        response_data["message"] = "success"
                else:
                    # L'utilisateur n'a pas la permission d'ajouter une catégorie
                    response_data["message"] = "Vous n'avez pas la permission de supprimer une catégorie."
            else:
                response_data["message"] = "Utilisateur non trouvé."
    return JsonResponse(response_data)


# @csrf_exempt
# @token_required
# def api_client_all(request, uuid):
#     try:
#         # Récupérer l'utilisateur avec l'ID donné
#         utilisateur = Utilisateur.objects.filter(uuid=uuid).first()
#
#         if utilisateur:
#
#             if (utilisateur.groups.filter(name="Admin").exists()
#                     or utilisateur.groups.filter(name="Editor").exists()
#                     or utilisateur.groups.filter(name="Author").exists()
#             ):
#                 # Récupérer toutes les entreprises auxquelles l'utilisateur est associé
#                 entreprises = utilisateur.entreprises.all()
#
#                 # Récupérer tous les clients liés aux entreprises de l'utilisateur
#                 clients = Client.objects.filter(entreprise__in=entreprises)
#
#                 # Préparer les données des clients pour la réponse
#                 clients_data = [
#                     {
#                         "uuid": client.uuid,
#                         "nom": client.nom,
#                         "adresse": client.adresse,
#                         "role": client.role,
#                         "coordonne": client.coordonne,
#                         "numero": client.numero,
#                         "libelle": client.libelle,
#                         "email": client.email,
#                         "date": client.created_at.strftime("%Y-%m-%d"),
#                     }
#                     for client in clients
#                 ]
#
#                 response_data = {
#                     "etat": True,
#                     "message": "Clients récupérés avec succès",
#                     "donnee": clients_data
#                 }
#             else:
#                 response_data = {
#                     "etat": False,
#                     "message": "Vous etes pas autorisé"
#                 }
#         else:
#             response_data = {
#                 "etat": False,
#                 "message": "Utilisateur non trouvé ou non autorisé"
#             }
#     except Utilisateur.DoesNotExist:
#         response_data = {
#             "etat": False,
#             "message": "Utilisateur non trouvé"
#         }
#
#     return JsonResponse(response_data)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_client_all(request, uuid):
    try:
        # Vérifier si l'entreprise existe
        entreprise = Entreprise.objects.get(uuid=uuid)

        # Récupérer tous les clients associés à cette entreprise
        clients = Client.objects.filter(entreprise=entreprise)

        # Préparer les données des clients pour la réponse
        clients_data = [
            {
                "uuid": client.uuid,
                "id": client.id,
                "nom": client.nom,
                "adresse": client.adresse,
                "role": client.role,
                "coordonne": client.coordonne,
                "numero": client.numero,
                "libelle": client.libelle,
                "email": client.email,
                "date": client.created_at.strftime("%Y-%m-%d"),
            }
            for client in clients
        ]

        response_data = {
            "etat": True,
            "message": "Clients récupérés avec succès",
            "donnee": clients_data
        }

    except Entreprise.DoesNotExist:
        response_data = {
            "etat": False,
            "message": "Entreprise non trouvée"
        }
    except Exception as e:
        response_data = {
            "etat": False,
            "message": f"Erreur interne : {str(e)}"
        }

    return JsonResponse(response_data)


# Pour les Categorie

# @csrf_exempt
# @token_required
# def add_categorie(request):
#     response_data = {'message': "requête invalide", 'etat': False}
#
#     if request.method == "POST":
#         form = request.POST
#         image = request.FILES.get('image')
#         # try:
#         #     form = json.loads(request.body.decode("utf-8"))
#         # except json.JSONDecodeError:
#         #     return JsonResponse({'message': "Erreur lors de la lecture des données JSON", 'etat': False})
#
#         libelle = form.get("libelle")
#         user_id = form.get("user_id")
#         entreprise_id = form.get("entreprise_id")
#         user = Utilisateur.objects.filter(uuid=user_id).first()
#
#         if user:
#             # Vérification des permissions de l'utilisateur
#             # if user.has_perm('entreprise.add_categorie'):
#             if (user.groups.filter(name="Admin").exists()
#                     or user.groups.filter(name="Editor").exists()
#             ):
#                 bout = Entreprise.objects.filter(uuid=entreprise_id).first()
#                 new_categorie = Categorie(libelle=libelle, entreprise=bout, image=image)
#                 new_categorie.save()
#
#                 response_data["etat"] = True
#                 response_data["id"] = new_categorie.id
#                 response_data["slug"] = new_categorie.slug
#                 response_data["message"] = "success"
#             else:
#                 # L'utilisateur n'a pas la permission d'ajouter une catégorie
#                 response_data["message"] = "Vous n'avez pas la permission d'ajouter une catégorie."
#         else:
#             response_data["message"] = "Utilisateur non trouvé."
#
#         # Autres cas d'erreurs...
#     return JsonResponse(response_data)

class AddCategorieView(APIView):

    def post(self, request, *args, **kwargs):
        libelle = request.data.get("libelle")
        user_id = request.data.get("user_id")
        entreprise_id = request.data.get("entreprise_id")
        image = request.FILES.get("image")

        # Vérification utilisateur
        user = request.user
        if not user:
            return Response({"etat": False, "message": "Utilisateur non trouvé."}, status=status.HTTP_404_NOT_FOUND)

        # Vérification permissions
        if not (user.groups.filter(name="Admin").exists() or user.groups.filter(name="Editor").exists()):
            return Response({"etat": False, "message": "Vous n'avez pas la permission d'ajouter une catégorie."},
                            status=status.HTTP_403_FORBIDDEN)

        # Vérification entreprise
        entreprise = get_object_or_404(Entreprise, uuid=entreprise_id)

        # Création de la catégorie
        new_categorie = Categorie(libelle=libelle, entreprise=entreprise, image=image)
        new_categorie.save()

        serializer = CategorieSerializer(new_categorie)

        return Response({
            "etat": True,
            "message": "success",
            "donnee": serializer.data
        }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_categorie(request):
    response_data = {'message': "requette invalide", 'etat': False}

    if request.method == "POST":
        form = dict()
        try:
            form = json.loads(request.body.decode("utf-8"))
        except:
            return JsonResponse({'message': "Erreur lors de le lecture des donnees JSON", 'etat': False})

        all_categorie = Categorie.objects.all()
        filtrer = False

        if "slug" in form or "all" in form and "user_id" in form:

            slug = form.get("slug")
            categorie_all = form.get("all")
            user_id = form.get("user_id")
            user = Utilisateur.objects.filter(uuid=user_id).first()

            if user:
                # if user.has_perm('entreprise.view_categorie'):
                if (user.groups.filter(name="Admin").exists()
                        or user.groups.filter(name="Editor").exists()
                ):
                    if slug:
                        all_categorie = all_categorie.filter(uuid=slug)
                        filtrer = True

                    if categorie_all:
                        all_categorie = Categorie.objects.all()
                        filtrer = True

                    if filtrer:

                        categories = list()
                        for c in all_categorie:
                            categories.append(
                                {
                                    "uuid": c.uuid,
                                    "libelle": c.libelle,
                                    "slug": c.slug,
                                    "sous_categorie_count": c.sous_categorie.count(),
                                    "image": c.image.url if c.image else None,
                                    # "image": c.image.url if c.image else None,
                                }
                            )
                        if categories:
                            response_data["etat"] = True
                            response_data["donnee"] = categories
                            response_data["message"] = "success"
                        else:
                            response_data["message"] = "Aucun categorie trouver"
                else:
                    # L'utilisateur n'a pas la permission d'ajouter une catégorie
                    response_data["message"] = "Vous n'avez pas la permission de voir les catégorie."
            else:
                response_data["message"] = "Utilisateur non trouvé."
    return JsonResponse(response_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_categorie(request):
    response_data = {'message': "requette invalide", 'etat': False}

    if request.method == "POST":
        form = request.POST
        image = request.FILES.get('image')

        print("ii .. ", form)

        categorie_id = form.get("uuid")
        slug = form.get("slug")
        user_id = form.get("user_id")
        user = Utilisateur.objects.filter(uuid=user_id).first()

        if user:
            # if user.has_perm('boutique.change_categorie'):
            if (user.groups.filter(name="Admin").exists()
                    or user.groups.filter(name="Editor").exists()
            ):

                if categorie_id:
                    categorie_from_database = Categorie.objects.all().filter(uuid=categorie_id).first()
                else:
                    categorie_from_database = Categorie.objects.all().filter(slug=slug).first()

                if not categorie_from_database:
                    response_data["message"] = "categorie non trouvé"
                else:
                    modifier = False
                    if "libelle" in form:
                        libelle = form.get("libelle")

                        categorie_from_database.libelle = libelle
                        modifier = True

                    if image:
                        categorie_from_database.image = image
                        modifier = True

                    if modifier:
                        categorie_from_database.save()
                        response_data["etat"] = True
                        response_data["message"] = "success"
            else:
                # L'utilisateur n'a pas la permission d'ajouter une catégorie
                response_data["message"] = "Vous n'avez pas la permission de modifier les catégorie."
        else:
            response_data["message"] = "Utilisateur non trouvé."

    return JsonResponse(response_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def del_categorie(request):
    response_data = {'message': "requette invalide", 'etat': False}

    if request.method == "POST":
        form = dict()
        try:
            form = json.loads(request.body.decode("utf-8"))
        except:
            return JsonResponse({'message': "Erreur lors de le lecture des donnees JSON", 'etat': False})

        if "id" in form or "slug" in form and "user_id" in form:
            id = form.get("id")
            slug = form.get("slug")
            user_id = form.get("user_id")
            user = Utilisateur.objects.filter(uuid=user_id).first()

            if user:
                # if user.has_perm('entreprise.delete_categorie'):
                if (user.groups.filter(name="Admin").exists()
                        or user.groups.filter(name="Editor").exists()
                ):
                    if id:
                        categorie_from_database = Categorie.objects.all().filter(id=id).first()
                    else:
                        categorie_from_database = Categorie.objects.all().filter(slug=slug).first()

                    if not categorie_from_database:
                        response_data["message"] = "categorie non trouvé"
                    else:
                        if len(categorie_from_database.sous_categorie) > 0:
                            response_data[
                                "message"] = f"cette categorie possède {len(categorie_from_database.sous_categorie)} nom de produit"
                        else:
                            categorie_from_database.delete()
                            response_data["etat"] = True
                            response_data["message"] = "success"
                else:
                    # L'utilisateur n'a pas la permission d'ajouter une catégorie
                    response_data["message"] = "Vous n'avez pas la permission de supprimer une catégorie."
            else:
                response_data["message"] = "Utilisateur non trouvé."
    return JsonResponse(response_data)


class CategorieDetailView(APIView):

    def get(self, request, uuid):
        try:

            categorie = Categorie.objects.all().filter(uuid=uuid).first()

            categorie_data = {
                "id": categorie.id,
                "libelle": categorie.libelle,
                "image": categorie.image.url if categorie.image else None,
                "slug": categorie.slug,
                "uuid": categorie.uuid,
            }

            response_data = {
                "etat": True,
                "message": "Catégorie récupérées avec succès",
                "donnee": categorie_data
            }
        except Utilisateur.DoesNotExist:
            response_data = {
                "etat": False,
                "message": "Categorie non trouvé"
            }

        return JsonResponse(response_data)


# @csrf_exempt
# @token_required
# def get_categories_utilisateur(request, uuid):
#     try:
#         # Récupérer l'utilisateur avec l'ID donné
#         utilisateur = Utilisateur.objects.get(uuid=uuid)
#
#         # Récupérer toutes les entreprises associées à cet utilisateur
#         entreprises = utilisateur.entreprises.all()
#
#         # Récupérer toutes les catégories associées à ces entreprises
#         categories = Categorie.objects.filter(entreprise__in=entreprises)
#
#         # Préparer les données de la réponse
#         categories_data = [
#             {
#                 "libelle": categorie.libelle,
#                 "slug": categorie.slug,
#                 "uuid": categorie.uuid,
#                 "sous_categorie_count": categorie.sous_categorie.count(),
#                 # "entreprise": categorie.entreprise.nom
#             }
#             for categorie in categories
#         ]
#
#         response_data = {
#             "etat": True,
#             "message": "Catégories récupérées avec succès",
#             "donnee": categories_data
#         }
#     except Utilisateur.DoesNotExist:
#         response_data = {
#             "etat": False,
#             "message": "Utilisateur non trouvé"
#         }
#
#     return JsonResponse(response_data)
class CategoriesUserAPIView(APIView):

    def get(self, request, entreprise_uuid):
        """
        Récupère toutes les catégories liées à une entreprise spécifique d'un utilisateur donné.
        """

        try:
            # Récupérer l'utilisateur via l'UUID
            utilisateur = request.user

            # Vérifier que l'entreprise avec l'UUID donné appartient à l'utilisateur
            entreprise = utilisateur.entreprises.filter(uuid=entreprise_uuid).first()

            if not entreprise:
                return JsonResponse({
                    "etat": False,
                    "message": "Entreprise non trouvée ou non associée à cet utilisateur."
                })

            # Récupérer les catégories associées à cette entreprise
            categories = Categorie.objects.filter(entreprise=entreprise)

            if not categories.exists():
                return JsonResponse({
                    "etat": False,
                    "message": "Aucune catégorie trouvée pour cette entreprise."
                })

            # Préparer les données pour la réponse
            categories_data = [
                {
                    "libelle": categorie.libelle,
                    "slug": categorie.slug,
                    "uuid": categorie.uuid,
                    "sous_categorie_count": categorie.sous_categorie.count(),
                    "image": categorie.image.url if categorie.image else None,
                    # "entreprise": entreprise.nom, # Optionnel si vous voulez inclure le nom de l'entreprise
                }
                for categorie in categories
            ]

            return JsonResponse({
                "etat": True,
                "message": "Catégories récupérées avec succès.",
                "donnee": categories_data
            })

        except Utilisateur.DoesNotExist:
            return JsonResponse({
                "etat": False,
                "message": "Utilisateur non trouvé."
            })
        except Exception as e:
            return JsonResponse({
                "etat": False,
                "message": f"Erreur serveur : {str(e)}"
            }, status=500)


class AddSousCategorieAPIView(APIView):

    def post(self, request, *args, **kwargs):
        response_data = {'etat': False, 'message': "Requête invalide"}

        libelle = request.data.get("libelle")
        categorie_slug = request.data.get("categorie_slug")
        user_id = request.data.get("user_id")
        image = request.FILES.get("image")

        # Vérification utilisateur
        user = request.user
        if not user:
            response_data["message"] = "Utilisateur non trouvé."
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        # Vérification des permissions
        if not (user.groups.filter(name="Admin").exists() or user.groups.filter(name="Editor").exists()):
            response_data["message"] = "Vous n'avez pas la permission d'ajouter une sous-catégorie."
            return Response(response_data, status=status.HTTP_403_FORBIDDEN)

        # Vérification de la catégorie
        categorie = Categorie.objects.filter(uuid=categorie_slug).first()
        if not categorie:
            response_data["message"] = "Catégorie non trouvée."
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)

        # Création de la sous-catégorie
        sous_categorie = SousCategorie.objects.create(
            libelle=libelle,
            categorie=categorie,
            image=image
        )

        response_data.update({
            "etat": True,
            "id": sous_categorie.id,
            "slug": sous_categorie.slug,
            "message": "Sous-catégorie ajoutée avec succès."
        })

        return Response(response_data, status=status.HTTP_201_CREATED)


class SousCategoriesUtilisateurAPIView(APIView):

    def get(self, request, entreprise_id):
        try:
            # Récupérer l'utilisateur avec l'ID donné
            utilisateur = request.user

            # Récupérer toutes les entreprises associées à cet utilisateur
            entreprise = Entreprise.objects.get(uuid=entreprise_id)

            # Récupérer toutes les catégories associées à ces entreprises
            categories = Categorie.objects.filter(entreprise=entreprise)

            # Récupérer toutes les sous-catégories associées à ces catégories
            sous_categories = SousCategorie.objects.filter(categorie__in=categories)

            # Préparer les données de la réponse
            sous_categories_data = [
                {
                    "id": sous_categorie.id,
                    "libelle": sous_categorie.libelle,
                    "image": sous_categorie.image.url if sous_categorie.image else None,
                    "uuid": sous_categorie.uuid,
                    "slug": sous_categorie.slug,
                    # "categorie": sous_categorie.categorie.nom,
                    # "entreprise": sous_categorie.categorie.entreprise.nom
                }
                for sous_categorie in sous_categories
            ]

            response_data = {
                "etat": True,
                "message": "Sous-catégories récupérées avec succès",
                "donnee": sous_categories_data
            }
        except Utilisateur.DoesNotExist:
            response_data = {
                "etat": False,
                "message": "Utilisateur non trouvé"
            }

        return JsonResponse(response_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_sous_categorie(request):
    response_data = {'message': "requette invalide", 'etat': False}

    if request.method == "POST":
        form = dict()
        try:
            form = json.loads(request.body.decode("utf-8"))
        except:
            return JsonResponse({'message': "Erreur lors de le lecture des donnees JSON", 'etat': False})

        filter = False
        all_sous_categorie = SousCategorie.objects.all()

        if "user_id" in form:
            user_id = form.get("user_id")
            user = Utilisateur.objects.filter(uuid=user_id).first()

            if user:
                # if user.has_perm('entreprise.view_souscategorie'):
                if (user.groups.filter(name="Admin").exists()
                        or user.groups.filter(name="Editor").exists()
                ):
                    if "categorie_slug" in form:
                        categorie_slug = form.get("categorie_slug")

                        categorie_from_database = Categorie.objects.all().filter(uuid=categorie_slug).first()

                        if categorie_from_database:
                            all_sous_categorie = all_sous_categorie.filter(categorie=categorie_from_database)
                            filter = True
                        else:
                            response_data["message"] = "categorie non trouver"

                    elif "slug" in form:
                        slug = form.get("slug")
                        all_sous_categorie = all_sous_categorie.filter(uuid=slug)
                        filter = True

                    else:
                        filter = True
                        all_sous_categorie = SousCategorie.objects.all()

                    if filter:

                        sous_categorie = list()
                        for sc in all_sous_categorie:
                            sous_categorie.append(
                                {
                                    "id": sc.id,
                                    "libelle": sc.libelle,
                                    "slug": sc.slug,
                                    "uuid": sc.uuid,
                                    "categorie_slug": sc.categorie.id,
                                    "image": sc.image.url if sc.image else None,
                                    # "all_entrer": sc.all_entrer.count(),
                                }
                            )

                        if len(sous_categorie) > 0:

                            response_data["etat"] = True
                            response_data["donnee"] = sous_categorie
                            response_data["message"] = "success"
                        else:
                            response_data["message"] = "vide"
                else:
                    # L'utilisateur n'a pas la permission d'ajouter une catégorie
                    response_data["message"] = "Vous n'avez pas la permission de voir les souscatégorie."
            else:
                response_data["message"] = "Utilisateur non trouvé."
    return JsonResponse(response_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_sous_categorie(request):
    response_data = {'message': "requette invalide", 'etat': False}

    if request.method == "POST":
        form = request.POST
        image = request.FILES.get('image')

        id = form.get("uuid")
        slug = form.get("slug")
        user_id = form.get("user_id")
        user = Utilisateur.objects.filter(uuid=user_id).first()

        if user:
            # Vérification des permissions de l'utilisateur
            if user.groups.filter(name="Admin").exists() or user.groups.filter(name="Editor").exists():
                # if user.has_perm('boutique.change_souscategorie'):

                if id:
                    sous_categorie_from_database = SousCategorie.objects.all().filter(uuid=id).first()
                else:
                    sous_categorie_from_database = SousCategorie.objects.all().filter(slug=slug).first()

                if not sous_categorie_from_database:
                    response_data["message"] = "Sous categorie non trouve"
                else:
                    modifier = False
                    if "libelle" in form:
                        libelle = form.get("libelle")

                        sous_categorie_from_database.libelle = libelle
                        modifier = True

                    if image:
                        sous_categorie_from_database.image = image
                        modifier = True

                    if "categorie_slug" in form:
                        categorie_slug = form.get("categorie_slug")

                        categorie_from_database = Categorie.objects.all().filter(slug=categorie_slug).first()

                        if categorie_from_database:
                            sous_categorie_from_database.categorie = categorie_from_database
                            modifier = True
                        else:
                            response_data["etat"] = True
                            response_data["message"] = "categorie non trouve"

                    if modifier:
                        sous_categorie_from_database.save()
                        response_data["etat"] = True
                        response_data["message"] = "success"
            else:
                # L'utilisateur n'a pas la permission d'ajouter une catégorie
                response_data["message"] = "Vous n'avez pas la permission de modifier les souscatégorie."
        else:
            response_data["message"] = "Utilisateur non trouvé."
    return JsonResponse(response_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def del_sous_categorie(request):
    response_data = {'message': "requette invalide", 'etat': False}

    if request.method == "POST":
        form = dict()
        try:
            form = json.loads(request.body.decode("utf-8"))
        except:
            return JsonResponse({'message': "Erreur lors de le lecture des donnees JSON", 'etat': False})

        if "uuid" in form or "slug" in form and "user_id" in form:
            id = form.get("uuid")
            slug = form.get("slug")
            user_id = form.get("user_id")
            user = Utilisateur.objects.filter(uuid=user_id).first()

            if user:
                # if user.has_perm('boutique.delete_souscategorie'):
                if (user.groups.filter(name="Admin").exists()
                        or user.groups.filter(name="Editor").exists()
                ):
                    if id:
                        sous_categorie_from_database = SousCategorie.objects.all().filter(uuid=id).first()
                    else:
                        sous_categorie_from_database = SousCategorie.objects.all().filter(slug=slug).first()

                    if not sous_categorie_from_database:
                        response_data["message"] = "categorie non trouvé"
                    else:
                        if len(sous_categorie_from_database.all_entrer) > 0:
                            response_data[
                                "message"] = f"cet nom possède {len(sous_categorie_from_database.all_entrer)} entrer ou achat"
                        else:
                            sous_categorie_from_database.delete()
                            response_data["etat"] = True
                            response_data["message"] = "success"
                else:
                    # L'utilisateur n'a pas la permission d'ajouter une catégorie
                    response_data["message"] = "Vous n'avez pas la permission de supprimer une souscatégorie."
            else:
                response_data["message"] = "Utilisateur non trouvé."

    return JsonResponse(response_data)


class SousCategorieUnEntrepriseView(APIView):
    def get(self, request, uuid):
        response_data = {'message': "requette invalide", 'etat': False}

        sous_categorie = SousCategorie.objects.all().filter(uuid=uuid).first()

        if sous_categorie:
            sous_categorie_data = {
                "id": sous_categorie.id,
                "uuid": sous_categorie.uuid,
                "libelle": sous_categorie.libelle,
                "slug": sous_categorie.slug,
                "categorie_slug": sous_categorie.categorie.slug,
                "image": sous_categorie.image.url if sous_categorie.image else None,
            }

            response_data["etat"] = True
            response_data["message"] = "success"
            response_data["donnee"] = sous_categorie_data
        else:
            response_data["message"] = "sous categorie non trouver"

        return JsonResponse(response_data)


class SousCategoriesEntrepriseView(APIView):

    def get(self, request, uuid):
        try:
            # Récupérer la catégorie par son ID
            categorie = Categorie.objects.get(uuid=uuid)

            # Récupérer toutes les sous-catégories liées à cette catégorie
            sous_categories = SousCategorie.objects.filter(categorie=categorie)

            # Construire la réponse avec les sous-catégories
            response_data = {
                "etat": True,
                "message": "Sous-catégories récupérées avec succès",
                "donnee": [
                    {
                        "id": sous_categorie.id,
                        "libelle": sous_categorie.libelle,
                        "image": sous_categorie.image.url if sous_categorie.image else None,
                        "uuid": sous_categorie.uuid,
                    } for sous_categorie in sous_categories
                ]
            }

        except Categorie.DoesNotExist:
            response_data = {
                "etat": False,
                "message": "Catégorie non trouvée"
            }

        return JsonResponse(response_data)


# Depense

# @csrf_exempt
# @token_required
# def add_depense(request):
#     response_data = {'message': "Requete invalide", 'etat': False}
#
#     if request.method == "POST":
#         form = request.POST
#         facture = request.FILES.get('facture')
#
#         libelle = form.get("libelle")
#         entreprise_id = form.get("entreprise_id")
#         somme = form.get("somme")
#         date = form.get("date")
#         admin_id = form.get("user_id")
#         print(form)
#
#         if admin_id:
#
#             admin = Utilisateur.objects.all().filter(uuid=admin_id).first()
#
#             if admin:
#                 # if admin.has_perm('entreprise.add_depense'):
#                 if (admin.groups.filter(name="Admin").exists()
#                         or admin.groups.filter(name="Editor").exists()
#                 ):
#                     entreprise = Entreprise.objects.all().filter(uuid=entreprise_id).first()
#
#                     if entreprise:
#
#                         new_livre = Depense(somme=somme, date=date, libelle=libelle, facture=facture,
#                                             entreprise=entreprise)
#                         new_livre.save()
#
#                         response_data["etat"] = True
#                         response_data["id"] = new_livre.id
#                         response_data["slug"] = new_livre.slug
#                         response_data["message"] = "success"
#                     else:
#                         return JsonResponse({'message': "entreprise non trouvee", 'etat': False})
#                 else:
#                     # L'utilisateur n'a pas la permission d'ajouter une catégorie
#                     response_data["message"] = "Vous n'avez pas la permission d'ajouter un depense."
#             else:
#                 return JsonResponse({'message': "Admin non trouvee", 'etat': False})
#
#         else:
#             response_data["message"] = "ID de l'utilisateur manquant !"
#
#     return JsonResponse(response_data)

class DepenseCreateView(APIView):

    def post(self, request, format=None):
        data = request.data
        libelle = data.get("libelle")
        entreprise_id = data.get("entreprise_id")
        somme = data.get("somme")
        date = data.get("date")
        facture = request.FILES.get("facture")
        admin_id = data.get("user_id")

        if not admin_id:
            return Response({"message": "ID de l'utilisateur manquant !", "etat": False},
                            status=status.HTTP_400_BAD_REQUEST)

        admin = request.user
        if not admin:
            return Response({"message": "Admin non trouvé", "etat": False},
                            status=status.HTTP_404_NOT_FOUND)

        # Vérifier les permissions par groupes
        if not (admin.groups.filter(name="Admin").exists() or admin.groups.filter(name="Editor").exists()):
            return Response({"message": "Vous n'avez pas la permission d'ajouter une dépense.", "etat": False},
                            status=status.HTTP_403_FORBIDDEN)

        entreprise = Entreprise.objects.filter(uuid=entreprise_id).first()
        if not entreprise:
            return Response({"message": "Entreprise non trouvée", "etat": False},
                            status=status.HTTP_404_NOT_FOUND)

        # Créer la dépense
        depense = Depense(
            somme=somme,
            date=date,
            libelle=libelle,
            facture=facture,
            entreprise=entreprise
        )
        depense.save()

        serializer = DepenseSerializer(depense)

        return Response({
            "etat": True,
            "id": depense.id,
            "slug": depense.slug,
            "message": "success",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_depense(request):
    response_data = {'message': "Requete invalide", 'etat': False}

    if request.method == "POST":
        form = request.POST
        facture = request.FILES.get('facture')

        user_id = form.get("user_id")
        user = Utilisateur.objects.filter(uuid=user_id).first()
        if user:
            # if user.has_perm('entreprise.change_depense'):
            if (user.groups.filter(name="Admin").exists()
                    or user.groups.filter(name="Editor").exists()
            ):
                slug = form.get("slug")
                identifiant = form.get("uuid")
                if not (identifiant or slug):
                    return JsonResponse({'message': "ID ou slug de livre manquant", 'etat': False})

                livre_from_database = None
                if identifiant:
                    livre_from_database = Depense.objects.filter(uuid=identifiant).first()
                else:
                    livre_from_database = Depense.objects.filter(slug=slug).first()

                if livre_from_database:

                    modifier = False
                    if "somme" in form:
                        livre_from_database.somme = form["somme"]
                        modifier = True

                    if "libelle" in form:
                        livre_from_database.libelle = form["libelle"]
                        modifier = True

                    if "date" in form:
                        livre_from_database.date = form["date"]
                        modifier = True

                    if facture:
                        livre_from_database.facture = facture
                        modifier = True

                    if "libelle" in form:
                        livre_from_database.libelle = form["libelle"]
                        modifier = True

                    if modifier:
                        livre_from_database.save()
                        response_data["etat"] = True
                        response_data["message"] = "Success"

                else:
                    return JsonResponse({'message': "entrer non trouvee", 'etat': False})
            else:
                # L'utilisateur n'a pas la permission d'ajouter une catégorie
                response_data["message"] = "Vous n'avez pas la permission de modifier les souscatégorie."
        else:
            response_data["message"] = "Utilisateur non trouvé."
    return JsonResponse(response_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def del_depense(request):
    response_data = {'message': "Requete invalide", 'etat': False}

    if request.method == "POST":
        try:
            form = json.loads(request.body.decode("utf-8"))
            id = form.get("uuid")
            slug = form.get("slug")
            user_id = form.get("user_id")
        except json.JSONDecodeError:
            return JsonResponse({'message': "Erreur lors de la lecture des donnees JSON", 'etat': False})

        user = Utilisateur.objects.filter(uuid=user_id).first()

        if user:
            # if user.has_perm('entreprise.delete_depense'):
            if (user.groups.filter(name="Admin").exists()
                    or user.groups.filter(name="Editor").exists()
            ):
                if id or slug:
                    if id:
                        livre_from_database = Depense.objects.filter(uuid=id).first()
                    else:
                        livre_from_database = Depense.objects.filter(slug=slug).first()

                    if not livre_from_database:
                        response_data["message"] = "Depense non trouvée"
                    else:
                        livre_from_database.delete()
                        response_data["etat"] = True
                        response_data["message"] = "Success"
                else:
                    response_data["message"] = "ID ou slug du Depense manquant"
            else:
                # L'utilisateur n'a pas la permission d'ajouter une catégorie
                response_data["message"] = "Vous n'avez pas la permission de supprimer un Depense."
        else:
            response_data["message"] = "Utilisateur non trouvé."
    return JsonResponse(response_data)


@csrf_exempt
def get_depense_un(request, uuid):
    response_data = {'message': "requette invalide", 'etat': False}

    livre = Depense.objects.all().filter(uuid=uuid).first()

    if livre:
        livre_data = {
            "id": livre.id,
            "uuid": livre.uuid,
            "libelle": livre.libelle,
            "somme": livre.somme,
            "date": livre.date,
            "facture": livre.facture.url if livre.facture else None,
        }

        response_data["etat"] = True
        response_data["message"] = "success"
        response_data["donnee"] = livre_data
    else:
        response_data["message"] = "Depense non trouver"

    return JsonResponse(response_data)


class DepensesEntrepriseAPIView(APIView):

    def get(self, request, entreprise_id):
        try:
            # Récupérer l'utilisateur avec l'UUID donné
            utilisateur = request.user

            # Vérifier si l'entreprise existe et si elle est associée à l'utilisateur
            entreprise = Entreprise.objects.filter(uuid=entreprise_id, utilisateurs=utilisateur).first()

            if not entreprise:
                return JsonResponse({
                    "etat": False,
                    "message": "Entreprise non trouvée ou non associée à l'utilisateur"
                })

            # Récupérer toutes les dépenses liées à l'entreprise
            depenses = Depense.objects.filter(entreprise=entreprise)

            # Préparer les données des dépenses pour la réponse
            depenses_data = [
                {
                    "id": dep.id,
                    "uuid": dep.uuid,
                    "slug": dep.slug,
                    "libelle": dep.libelle,
                    "somme": dep.somme,
                    "date": dep.date.strftime("%Y-%m-%d"),
                }
                for dep in depenses
            ]

            response_data = {
                "etat": True,
                "message": "Dépenses récupérées avec succès",
                "donnee": depenses_data
            }
        except Utilisateur.DoesNotExist:
            response_data = {
                "etat": False,
                "message": "Utilisateur non trouvé"
            }

        return JsonResponse(response_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_depenses_somme(request, uuid, entreprise_id):
    try:
        utilisateur = Utilisateur.objects.get(uuid=uuid)
        entreprise = Entreprise.objects.filter(uuid=entreprise_id).first()

        if not entreprise:
            return JsonResponse({
                "etat": False,
                "message": "Entreprise non trouvée ou non associée à l'utilisateur"
            })

        # Groupement des dépenses par mois et somme des montants
        depenses_par_mois = (
            Depense.objects
            .filter(entreprise=entreprise)
            .annotate(mois=TruncMonth('date'))  # tronquer à l'année + mois
            .values('mois')
            .annotate(total=Sum('somme'))
            .order_by('mois')
        )

        # Préparer les données
        depenses_data = [
            {
                "mois": dep["mois"].strftime("%Y-%m"),  # format lisible
                "total": float(dep["total"]) if dep["total"] else 0
            }
            for dep in depenses_par_mois
        ]

        response_data = {
            "etat": True,
            "message": "Somme des dépenses par mois récupérée avec succès",
            "donnee": depenses_data
        }

    except Utilisateur.DoesNotExist:
        response_data = {
            "etat": False,
            "message": "Utilisateur non trouvé"
        }

    return JsonResponse(response_data)


# Entrer

class AddEntrerView(APIView):

    def post(self, request):
        data = request.data

        # Validation basique
        qte = int(data.get("qte", 0))
        qte_critique = int(data.get("qte_critique", 0))
        pu = data.get("pu")
        pu_achat = data.get("pu_achat", 0)
        libelle = data.get("libelle")
        date = data.get("date")
        cumuler_quantite = data.get("cumuler_quantite", False)
        is_sortie = data.get("is_sortie", True)
        is_prix = data.get("is_prix", True)
        client_id = data.get("client_id")
        categorie_slug = data.get("categorie_slug")

        user = request.user

        # Vérification permissions
        if not user.is_authenticated:
            return Response({"etat": False, "message": "Non authentifié"}, status=400)

        if not (user.groups.filter(name="Admin").exists() or user.groups.filter(name="Editor").exists()):
            return Response({"etat": False, "message": "Permission refusée"}, status=403)

        # Récupération catégorie
        categorie = SousCategorie.objects.filter(uuid=categorie_slug).first()
        if not categorie:
            return Response({"etat": False, "message": "Catégorie introuvable"}, status=400)

        # Récupération client
        client = None
        if client_id:
            client = Client.objects.filter(uuid=client_id).first()
            if not client:
                return Response({"etat": False, "message": "Client introuvable"}, status=400)

        # -----------------------------
        # 🔥 Logique de cumul déplacée ici
        # -----------------------------

        dernier = Entrer.objects.filter(souscategorie=categorie).order_by("-created_at").first()

        # Si on cumule → on modifie l'ancien produit
        if cumuler_quantite and dernier:
            # Client différent → reset
            if dernier.client != client:
                dernier.client = None

            ancien_qte = dernier.qte
            dernier.qte += qte
            dernier.pu = pu
            dernier.date = date
            dernier.ref = data.get("ref") or dernier.generate_unique_code()

            # Création historique
            HistoriqueEntrer.objects.create(
                entrer=dernier,
                ref=dernier.ref,
                libelle=f"Produit modifié par {user.first_name} {user.last_name}",
                categorie=categorie.libelle,
                qte=qte,
                ancien_qte=ancien_qte,
                cumuler_qe=cumuler_quantite,
                pu=pu,
                date=date,
                action="updated",
                reference=dernier.generate_unique_code()
            )
            dernier.save()

            return Response({"etat": True, "message": "Quantité cumulée", "id": dernier.id})

        # -----------------------------
        # 🔥 Sinon on crée un nouveau produit
        # -----------------------------

        entrer = Entrer.objects.create(
            souscategorie=categorie,
            qte=qte,
            qte_critique=qte_critique,
            pu=pu,
            pu_achat=pu_achat,
            libelle=libelle,
            date=date,
            is_sortie=is_sortie,
            is_prix=is_prix,
            client=client,
        )

        # Génération ref si absent
        entrer.ref = entrer.ref or entrer.generate_unique_code()
        entrer.save()

        # Génération Qrcode
        try:
            self.generate_qrcode(entrer)
        except:
            pass  # éviter crash si la police n'est pas trouvée

        # Historique création
        HistoriqueEntrer.objects.create(
            entrer=entrer,
            ref=entrer.ref,
            libelle=f"Produit ajouté par {user.first_name} {user.last_name}",
            categorie=f"{categorie.libelle} ({entrer.libelle})",
            qte=qte,
            pu=pu,
            date=date,
            action="created"
        )

        return Response({
            "etat": True,
            "id": entrer.id,
            "slug": entrer.slug,
            "message": "Produit créé"
        }, status=201)

    # -----------------------------
    # 🔥 Fonction QR code sortie du modèle
    # -----------------------------
    def generate_qrcode(self, entrer):
        ref = str(entrer.ref)

        qr = qrcode.QRCode(
            version=1,
            box_size=10,
            border=4,
            error_correction=qrcode.constants.ERROR_CORRECT_L
        )

        qr.add_data(ref)
        qr.make(fit=True)
        img_qr = qr.make_image().convert("RGB")

        # Police
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 20)
        except:
            font = ImageFont.load_default()

        draw = ImageDraw.Draw(img_qr)
        buffer = BytesIO()
        img_qr.save(buffer, format="PNG")
        buffer.seek(0)

        # Calcul des dimensions du texte avec textbbox
        draw = ImageDraw.Draw(img_qr)
        bbox = draw.textbbox((0, 0), ref, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Création d'une nouvelle image avec un espace en bas pour le texte
        new_width = max(img_qr.width, text_width)
        new_height = img_qr.height + text_height + 10  # 10 pixels de marge
        new_img = Image.new("RGB", (new_width, new_height), "white")

        # Positionner le QR code dans la nouvelle image
        x_offset = (new_width - img_qr.width) // 2
        new_img.paste(img_qr, (x_offset, 0))

        # Dessiner le texte en dessous du QR code, centré horizontalement
        draw = ImageDraw.Draw(new_img)
        text_x = (new_width - text_width) // 2
        text_y = img_qr.height + 5  # 5 pixels de marge
        draw.text((text_x, text_y), ref, fill="black", font=font)

        # Sauvegarder l'image finale dans un buffer
        buffer = BytesIO()
        new_img.save(buffer, format="PNG")
        buffer.seek(0)

        # Enregistrer l'image dans le champ ImageField
        entrer.barcode.save(f'{ref}.png', File(buffer), save=True)

        # entrer.barcode.save(f"{ref}.png", File(buffer), save=True)


class EntrerViewSet(viewsets.ModelViewSet):
    queryset = Entrer.objects.all().order_by('-created_at')
    serializer_class = EntrerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        user = self.request.user

        # Enregistrer dans l'historique AVANT la suppression
        HistoriqueEntrer.objects.create(
            entrer=instance,
            ref=instance.ref,
            libelle=f"Produit supprimé par {user.first_name} {user.last_name}" if user else "Produit supprimé",
            categorie=instance.souscategorie.libelle,
            qte=instance.qte,
            pu=instance.pu,
            date=instance.date,
            action="deleted",
            reference=instance.generate_unique_code(),  # code unique
        )

        # Puis supprimer définitivement
        instance.delete()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def del_entre(request):
    data = request.data
    user = request.user  # Utilisateur authentifié

    # Vérification permissions
    if not (user.groups.filter(name="Admin").exists() or user.groups.filter(name="Editor").exists()):
        return JsonResponse({"etat": False, "message": "Permission refusée"}, status=403)

    uuid = data.get("uuid")
    slug = data.get("slug")
    entreprise_id = data.get("entreprise_id")

    if not (uuid or slug):
        return JsonResponse({"etat": False, "message": "uuid ou slug manquant"}, status=400)

    # Récupération de l'objet
    entrer = Entrer.objects.filter(uuid=uuid).first() if uuid else Entrer.objects.filter(slug=slug).first()
    if not entrer:
        return JsonResponse({"etat": False, "message": "Produit introuvable"}, status=404)

    # Vérification entreprise si fournie
    entreprise = None
    if entreprise_id:
        entreprise = Entreprise.objects.filter(uuid=entreprise_id).first()

    # Empêcher la suppression si des sorties existent
    if entrer.all_sortie.exists():
        return JsonResponse({
            "etat": False,
            "message": "Impossible de supprimer : des sorties/ventes existent pour cet article."
        }, status=400)

    # Sauvegarde des données avant suppression
    ref_entrer = entrer.ref
    qte = entrer.qte
    pu = entrer.pu
    categorie_txt = f"{entrer.souscategorie.libelle} ({entrer.libelle})"

    # Ajout à l'historique
    HistoriqueEntrer.objects.create(
        entreprise=entreprise,
        entrer=entrer,
        ref=ref_entrer,
        libelle=f"Produit supprimé par {user.first_name} {user.last_name}",
        categorie=categorie_txt,
        qte=qte,
        pu=pu,
        action="deleted",
        utilisateur=user
    )

    # Suppression
    entrer.delete()

    return JsonResponse({"etat": True, "message": "Suppression réussie"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_entre(request):
    response_data = {'message': "Requête invalide", 'etat': False, 'donnee': []}

    if request.method == "POST":
        try:
            form = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({'message': "Erreur lors de la lecture des données JSON", 'etat': False, 'donnee': []})

        all_livre = Entrer.objects.all()
        filtrer = False

        user_id = form.get("user_id")
        if user_id:
            user = Utilisateur.objects.filter(uuid=user_id).first()

            if user:
                # if user.has_perm('entreprise.view_entrer'):
                if (user.groups.filter(name="Admin").exists()
                        or user.groups.filter(name="Editor").exists()
                ):
                    livre_id = form.get("id")
                    if livre_id:
                        all_livre = all_livre.filter(id=livre_id)
                        filtrer = True

                    client_id = form.get("client_id")
                    if client_id:
                        client = Client.objects.filter(uuid=client_id).first()
                        if client:
                            all_livre = all_livre.filter(client=client)
                            filtrer = True
                            # Si aucun enregistrement pour ce client, renvoyer un tableau vide dans 'donnee'
                            if not all_livre.exists():
                                return JsonResponse(
                                    {'message': "Aucun enregistrement trouvé pour ce client.", 'etat': True,
                                     'donnee': []})
                        else:
                            return JsonResponse({'message': "Client non trouvé.", 'etat': False, 'donnee': []})
                    else:
                        return JsonResponse({'message': "Aucun client_id fourni dans les données.", 'etat': False})

                    if filtrer:
                        data = []
                        for liv in all_livre:
                            data.append({
                                "id": liv.id,
                                "uuid": liv.uuid,
                                "categorie_libelle": liv.souscategorie.libelle,
                                "slug": liv.slug,
                                "libelle": liv.libelle,
                                "pu": liv.pu,
                                "is_sortie": liv.is_sortie,
                                "is_prix": liv.is_prix,

                                "pu_achat": liv.pu_achat,
                                "qte": liv.qte,
                                "price": liv.prix_total,
                                "image": liv.souscategorie.image.url if liv.souscategorie.image else None,
                                "date": str(liv.date),
                            })

                        response_data["etat"] = True
                        response_data["message"] = "success"
                        response_data["donnee"] = data
                        if not data:
                            response_data["message"] = "Aucune catégorie trouvée."
                else:
                    response_data["message"] = "Vous n'avez pas la permission de voir les entrées."
            else:
                response_data["message"] = "Utilisateur non trouvé."
        else:
            response_data["message"] = "Identifiant utilisateur manquant."

    return JsonResponse(response_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_entre(request):
    data = request.data
    user = request.user

    if not (user.groups.filter(name="Admin").exists() or user.groups.filter(name="Editor").exists()):
        return JsonResponse({"etat": False, "message": "Permission refusée"}, status=403)

    uuid = data.get("uuid")
    slug = data.get("slug")

    if not (uuid or slug):
        return JsonResponse({"etat": False, "message": "uuid ou slug manquant"}, status=400)

    entrer = Entrer.objects.filter(uuid=uuid).first() if uuid else Entrer.objects.filter(slug=slug).first()
    if not entrer:
        return JsonResponse({"etat": False, "message": "Produit introuvable"}, status=404)

    # ---- Tracking des modifications ----
    fields_changed = {}
    allowed_fields = ["qte", "qte_critique", "pu", "pu_achat", "is_sortie", "is_prix", "libelle"]

    for field in allowed_fields:
        if field in data:
            old_val = getattr(entrer, field)
            new_val = data[field]

            if str(old_val) != str(new_val):
                fields_changed[field] = {"ancien": old_val, "nouveau": new_val}

                # Capture ancien_qte si qte change
                if field == "qte":
                    ancien_qte = old_val

                setattr(entrer, field, new_val)

    if not fields_changed:
        return JsonResponse({"etat": False, "message": "Aucune modification détectée"}, status=200)

    entrer.save()

    # ---- Historique ----
    HistoriqueEntrer.objects.create(
        entrer=entrer,
        ref=entrer.ref,
        libelle=f"Produit modifié par {user.first_name} {user.last_name}",
        categorie=f"{entrer.souscategorie.libelle} ({entrer.libelle})",
        qte=data.get("qte", entrer.qte),
        description=data.get("description"),
        ancien_qte=fields_changed["qte"]["ancien"] if "qte" in fields_changed else None,
        pu=data.get("pu", entrer.pu),
        action="updated"
    )

    if "pu" in fields_changed or "ref" in fields_changed:
        regenerate_qrcode(entrer)

    return JsonResponse({
        "etat": True,
        "message": "Modification effectuée",
        "changes": fields_changed
    })


# @csrf_exempt
# @token_required
# def get_entre(request):
#     response_data = {'message': "Requête invalide", 'etat': False, 'donnee': []}
#
#     if request.method == "POST":
#         try:
#             form = json.loads(request.body.decode("utf-8"))
#         except json.JSONDecodeError:
#             return JsonResponse({'message': "Erreur lors de la lecture des données JSON", 'etat': False, 'donnee': []})
#
#         # Récupérer toutes les entrées
#         all_entrer = Entrer.objects.all()
#         filtrer = False
#
#         # Récupérer l'utilisateur
#         user_id = form.get("user_id")
#         if user_id:
#             user = Utilisateur.objects.filter(uuid=user_id).first()
#
#             if user:
#                 # Vérifier les permissions ou le rôle
#                 if user.groups.filter(name__in=["Admin", "Editor"]).exists():
#                     # Filtrer par UUID de l'entreprise
#                     entreprise_uuid = form.get("entreprise_uuid")
#                     if entreprise_uuid:
#                         entreprise = Entreprise.objects.filter(uuid=entreprise_uuid).first()
#                         if entreprise:
#                             all_entrer = all_entrer.filter(souscategorie__categorie__entreprise=entreprise)
#                             filtrer = True
#                         else:
#                             return JsonResponse({'message': "Entreprise non trouvée.", 'etat': False, 'donnee': []})
#
#                     # Filtrer par ID spécifique de l'entrée
#                     entrer_id = form.get("id")
#                     if entrer_id:
#                         all_entrer = all_entrer.filter(id=entrer_id)
#                         filtrer = True
#
#                     # Filtrer par client
#                     client_id = form.get("client_id")
#                     if client_id:
#                         client = Client.objects.filter(uuid=client_id).first()
#                         if client:
#                             all_entrer = all_entrer.filter(client=client)
#                             filtrer = True
#                         else:
#                             return JsonResponse({'message': "Client non trouvé.", 'etat': False, 'donnee': []})
#
#                     # Structurer la réponse si des filtres ont été appliqués
#                     if filtrer:
#                         data = [
#                             {
#                                 "id": entrer.id,
#                                 "uuid": entrer.uuid,
#                                 "categorie_libelle": entrer.souscategorie.categorie.libelle,
#                                 "souscategorie_libelle": entrer.souscategorie.libelle,
#                                 "slug": entrer.slug,
#                                 "libelle": entrer.libelle,
#                                 "pu": entrer.pu,
#                                 "qte": entrer.qte,
#                                 "price": entrer.prix_total,
#                                 "date": str(entrer.date),
#                             }
#                             for entrer in all_entrer
#                         ]
#
#                         response_data["etat"] = True
#                         response_data["message"] = "Succès"
#                         response_data["donnee"] = data
#                         if not data:
#                             response_data["message"] = "Aucune entrée trouvée."
#                 else:
#                     response_data["message"] = "Vous n'avez pas la permission de voir les entrées."
#             else:
#                 response_data["message"] = "Utilisateur non trouvé."
#         else:
#             response_data["message"] = "Identifiant utilisateur manquant."
#
#     return JsonResponse(response_data)

@csrf_exempt
def get_entre_un(request, uuid):
    response_data = {'message': "requette invalide", 'etat': False}

    livre = Entrer.objects.all().filter(uuid=uuid).first()

    if livre:
        livre_data = {
            "id": livre.id,
            "uuid": livre.uuid,
            "libelle": livre.libelle,
            "pu": livre.pu,
            "pu_achat": livre.pu_achat,
            "is_sortie": livre.is_sortie,
            "is_prix": livre.is_prix,
            "qte": livre.qte,
            "qte_critique": livre.qte_critique,
            "image": livre.souscategorie.image.url if livre.souscategorie.image else None,
            "categorie_slug": livre.souscategorie.libelle,
        }

        response_data["etat"] = True
        response_data["message"] = "success"
        response_data["donnee"] = livre_data
    else:
        response_data["message"] = "Entrer non trouver"

    return JsonResponse(response_data)


# @csrf_exempt
# @token_required
# def get_entrers_entreprise(request, uuid):
#     try:
#         # Récupérer l'utilisateur avec l'ID donné
#         utilisateur = Utilisateur.objects.get(uuid=uuid)
#
#         # Récupérer toutes les entreprises associées à cet utilisateur
#         entreprises = utilisateur.entreprises.all()
#
#         # Récupérer toutes les catégories associées à ces entreprises
#         categories = Categorie.objects.filter(entreprise__in=entreprises)
#         souscategories = SousCategorie.objects.filter(categorie__in=categories)
#
#         entrers = Entrer.objects.filter(souscategorie__in=souscategories)
#
#         # Préparer les données de la réponse
#         categories_data = [
#             {
#                 "id": liv.id,
#                 "categorie_libelle": liv.souscategorie.libelle,
#                 "uuid": liv.uuid,
#                 "libelle": liv.libelle,
#                 "pu": liv.pu,
#                 "client": liv.client.nom if liv.client else None,
#                 "qte": liv.qte,
#                 "price": liv.prix_total,
#                 "date": liv.date.strftime("%Y-%m-%d"),
#
#             }
#             for liv in entrers
#         ]
#
#         response_data = {
#             "etat": True,
#             "message": "Catégories récupérées avec succès",
#             "donnee": categories_data
#         }
#     except Utilisateur.DoesNotExist:
#         response_data = {
#             "etat": False,
#             "message": "Utilisateur non trouvé"
#         }
#
#     return JsonResponse(response_data)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_entrers_entreprise(request, uuid, entreprise_id):
    try:
        # Vérifier si l'entreprise existe
        utilisateur = Utilisateur.objects.get(uuid=uuid)
        if utilisateur.groups.filter(name__in=["Admin", "Editor", "Author"]).exists():
            entreprise = Entreprise.objects.get(uuid=entreprise_id)

            # Récupérer toutes les sous-catégories associées à cette entreprise
            souscategories = SousCategorie.objects.filter(categorie__entreprise=entreprise)

            # Récupérer toutes les entrées liées à ces sous-catégories
            entrers = Entrer.objects.filter(souscategorie__in=souscategories)

            # Préparer les données pour la réponse
            entrers_data = [
                {
                    "id": entrer.id,
                    "categorie_libelle": entrer.souscategorie.libelle,
                    "uuid": entrer.uuid,
                    "libelle": entrer.libelle,
                    "pu": entrer.pu,
                    "pu_achat": entrer.pu_achat,
                    "ref": entrer.ref,
                    "client": entrer.client.nom if entrer.client else None,
                    "qte": entrer.qte,
                    "is_sortie": entrer.is_sortie,
                    "is_prix": entrer.is_prix,
                    "price": entrer.prix_total,
                    "image": entrer.souscategorie.image.url if entrer.souscategorie.image else None,
                    "code_barre": entrer.barcode.url if entrer.barcode else None,
                    "date": entrer.date.strftime("%Y-%m-%d"),
                }
                for entrer in entrers
            ]

            response_data = {
                "etat": True,
                "message": "Entrées récupérées avec succès",
                "donnee": entrers_data
            }
        else:
            response_data = {
                "etat": False,
                "message": "Vous avez pas la permission"
            }
    except Entreprise.DoesNotExist:
        response_data = {
            "etat": False,
            "message": "Entreprise non trouvée"
        }
    except Exception as e:
        response_data = {
            "etat": False,
            "message": f"Erreur interne : {str(e)}"
        }

    return JsonResponse(response_data)


# Sortie

# @csrf_exempt
# @token_required
# def add_sortie(request):
#     response_data = {'message': "Requete invalide", 'etat': False}
#
#     if request.method == "POST":
#         try:
#             form = json.loads(request.body.decode("utf-8"))
#         except:
#             return JsonResponse({'message': "Erreur lors de la lecture des donnees JSON", 'etat': False})
#
#         qte = form.get("qte")
#         pu = form.get("pu")
#         admin_id = form.get("user_id")
#         entrer_id = form.get("entre_id")
#         client_id = form.get("client_id")
#
#         if admin_id:
#
#             admin = Utilisateur.objects.all().filter(uuid=admin_id).first()
#
#             if admin:
#                 # if admin.has_perm('entreprise.add_sortie'):
#                 if (admin.groups.filter(name="Admin").exists()
#                         or admin.groups.filter(name="Editor").exists()
#                         or admin.groups.filter(name="Author").exists()
#                 ):
#
#                     entrer = Entrer.objects.all().filter(uuid=entrer_id).first()
#
#                     if entrer:
#
#                         new_livre = Sortie(qte=qte, pu=pu, entrer=entrer)
#
#                         # Ajout du client si client_id est fourni et valide
#                         if client_id:
#                             client = Client.objects.filter(uuid=client_id).first()
#                             if client:
#                                 new_livre.client = client
#                             else:
#                                 return JsonResponse({'message': "Client non trouvé", 'etat': False})
#
#                         new_livre.save()
#
#                         response_data["etat"] = True
#                         response_data["id"] = new_livre.id
#                         response_data["slug"] = new_livre.slug
#                         response_data["message"] = "success"
#                     else:
#                         return JsonResponse({'message': "Categorie non trouvee", 'etat': False})
#                 else:
#                     # L'utilisateur n'a pas la permission d'ajouter une catégorie
#                     response_data["message"] = "Vous n'avez pas la permission d'ajouter une souscatégorie."
#             else:
#                 return JsonResponse({'message': "Admin non trouvee", 'etat': False})
#
#         else:
#             response_data["message"] = "Nom de livre ou image ou description manquant"
#
#     return JsonResponse(response_data)
class SortieCreateView(APIView):
    def post(self, request):
        data = request.data

        qte = data.get("qte")
        pu = data.get("pu")
        admin = request.user
        entrer_id = data.get("entre_id")
        client_id = data.get("client_id")

        # Vérification admin
        if not admin or not admin.groups.filter(name__in=["Admin", "Editor", "Author"]).exists():
            return Response({'etat': False, 'message': "Permission refusée"},
                            status=status.HTTP_403_FORBIDDEN)

        # Vérification entrée
        entrer = Entrer.objects.filter(uuid=entrer_id).first()
        if not entrer:
            return Response({'etat': False, 'message': "Entrée non trouvée"},
                            status=status.HTTP_404_NOT_FOUND)

        # Vérification stock
        if entrer.qte - int(qte) < 0:
            return Response({'etat': False, 'message': "Stock insuffisant"},
                            status=status.HTTP_400_BAD_REQUEST)

        # Création sortie
        sortie = Sortie(
            qte=qte,
            pu=pu,
            entrer=entrer,
            created_by=admin
        )

        # Client (optionnel)
        if client_id:
            try:
                client_uuid = uuid.UUID(client_id)
            except ValueError:
                return Response({'etat': False, 'message': "Client non valide"},
                                status=status.HTTP_400_BAD_REQUEST)

            client = Client.objects.filter(uuid=client_uuid).first()
            if not client:
                return Response({'etat': False, 'message': "Client non trouvé"},
                                status=status.HTTP_404_NOT_FOUND)
            sortie.client = client

        # Enregistrer la sortie
        sortie.save()

        # 🔥 Mise à jour stock
        entrer.qte -= int(qte)
        entrer.save()

        # 🔥 Enregistrer HistoriqueSortie
        HistoriqueSortie.objects.create(
            sortie=sortie,
            ref=sortie.ref,
            qte=sortie.qte,
            pu=sortie.pu,
            action="created",
            libelle=f"Produit sorti par {admin.first_name} {admin.last_name}",
            categorie=f"{entrer.souscategorie.libelle} ({entrer.libelle})",
            utilisateur=admin,
            entreprise=admin.entreprise if hasattr(admin, "entreprise") else None
        )

        serializer = SortieSerializer(sortie)
        return Response({
            "etat": True,
            "message": "success",
            "donnee": serializer.data
        }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_sortie(request):
    response_data = {'message': "Requete invalide", 'etat': False, 'donnee': []}

    if request.method == "POST":
        try:
            form = json.loads(request.body.decode("utf-8"))
        except:
            return JsonResponse({'message': "Erreur lors de le lecture des donnees JSON", 'etat': False})

        all_livre = Sortie.objects.all()
        filtrer = False

        user_id = form.get("user_id")
        if user_id:

            user = Utilisateur.objects.filter(uuid=user_id).first()

            if user:
                if (user.groups.filter(name="Admin").exists()
                        or user.groups.filter(name="Editor").exists()
                        or user.groups.filter(name="Author").exists()
                ):
                    # if user.has_perm('entreprise.view_entrer'):
                    livre_id = form.get("id")
                    if livre_id:
                        all_livre = all_livre.filter(id=livre_id)
                        filtrer = True

                    livre_slug = form.get("slug")
                    if livre_slug:
                        all_livre = all_livre.filter(uuid=livre_slug)
                        filtrer = True

                    client_id = form.get("client_id")
                    if client_id:
                        client = Client.objects.filter(uuid=client_id).first()
                        if client:
                            all_livre = all_livre.filter(client=client)
                            filtrer = True
                            # Si aucun enregistrement pour ce client, renvoyer un tableau vide dans 'donnee'
                            if not all_livre.exists():
                                return JsonResponse(
                                    {'message': "Aucun enregistrement trouvé pour ce client.", 'etat': True,
                                     'donnee': []})
                        else:
                            return JsonResponse({'message': "Client non trouvé.", 'etat': False, 'donnee': []})
                    # else:
                    #     return JsonResponse(
                    #         {'message': "Aucun client_id fourni dans les données.", 'etat': False, 'donnee': []})

                    livre_all = form.get("all")
                    if livre_all:
                        all_livre = Sortie.objects.all()
                        filtrer = True

                    if filtrer:
                        # print(filtrer)
                        data = []
                        for liv in all_livre:
                            data.append({
                                "id": liv.id,
                                "uuid": liv.uuid,
                                "slug": liv.slug,
                                "pu": liv.pu,
                                "ref": liv.ref,
                                "qte": liv.qte,
                                "is_remise": liv.is_remise,
                                "categorie_libelle": liv.entrer.souscategorie.libelle,
                                "libelle": liv.entrer.libelle,
                                "prix_total": liv.prix_total,
                                "somme_total": liv.somme_total,
                                "prix_sortie": liv.entrer.qte,
                                "image": liv.entrer.souscategorie.image.url if liv.entrer.souscategorie.image else None,
                                "date": str(liv.created_at),
                            })

                        if data:
                            response_data["etat"] = True
                            response_data["message"] = "success"
                            response_data["donnee"] = data
                        else:
                            response_data["message"] = "Aucune sortie effectuer."
                else:
                    # L'utilisateur n'a pas la permission d'ajouter une catégorie
                    response_data["message"] = "Vous n'avez pas la permission de voir les souscatégorie."
            else:
                response_data["message"] = "Utilisateur non trouvé."
    return JsonResponse(response_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_sorties(request):
    """
    Met à jour le champ `is_remise` à True pour les sorties sélectionnées.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"message": "Erreur lors de la lecture des données JSON", "etat": False}, status=400)

        # Gestion des différents formats de données JSON
        if isinstance(data, dict):
            sortie_ids = data.get("ids", [])
        elif isinstance(data, list):
            # Si la liste contient un seul élément qui est lui-même une liste, on la déplie
            if len(data) == 1 and isinstance(data[0], list):
                sortie_ids = data[0]
            else:
                sortie_ids = data
        else:
            return JsonResponse(
                {"message": "Le format des données JSON doit être un objet ou une liste", "etat": False}, status=400)

        # Vérification que sortie_ids est une liste non vide
        if not sortie_ids or not isinstance(sortie_ids, list):
            return JsonResponse({"message": "Aucun ID valide fourni", "etat": False}, status=400)

        updated_count = Sortie.objects.filter(id__in=sortie_ids).update(is_remise=True)
        return JsonResponse({
            "message": f"{updated_count} enregistrements mis à jour.",
            "etat": True
        })

    return JsonResponse({"message": "Méthode non autorisée", "etat": False}, status=405)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_fac_sorties(request):
    """
    Met à jour le champ `is_remise` à True pour les sorties sélectionnées.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"message": "Erreur lors de la lecture des données JSON", "etat": False}, status=400)

        # Gestion des différents formats de données JSON
        if isinstance(data, dict):
            sortie_ids = data.get("ids", [])
        elif isinstance(data, list):
            # Si la liste contient un seul élément qui est lui-même une liste, on la déplie
            if len(data) == 1 and isinstance(data[0], list):
                sortie_ids = data[0]
            else:
                sortie_ids = data
        else:
            return JsonResponse(
                {"message": "Le format des données JSON doit être un objet ou une liste", "etat": False}, status=400)

        # Vérification que sortie_ids est une liste non vide
        if not sortie_ids or not isinstance(sortie_ids, list):
            return JsonResponse({"message": "Aucun ID valide fourni", "etat": False}, status=400)

        updated_count = Sortie.objects.filter(id__in=sortie_ids).update(is_remise=False)
        return JsonResponse({
            "message": f"{updated_count} enregistrements mis à jour.",
            "etat": True
        })

    return JsonResponse({"message": "Méthode non autorisée", "etat": False}, status=405)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def del_sortie(request):
    response_data = {'message': "Requete invalide", 'etat': False}

    if request.method == "POST":
        try:
            form = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({'message': "Erreur lors de la lecture des données JSON", 'etat': False})

        sortie_id = form.get("uuid")
        action_type = form.get("action")  # "cancel" ou "delete"
        user_id = form.get("user_id")
        entreprise_id = form.get("entreprise_id")
        description = form.get("description")

        user = Utilisateur.objects.filter(uuid=user_id).first()

        if not user:
            return JsonResponse({"etat": False, "message": "Utilisateur non trouvé."})

        # Permissions
        if not (user.groups.filter(name__in=["Admin", "Editor"]).exists()):
            return JsonResponse({"etat": False, "message": "Vous n'avez pas la permission."})

        # Vérif sortie
        sortie = Sortie.objects.filter(uuid=sortie_id).first()
        if not sortie:
            return JsonResponse({"etat": False, "message": "Sortie non trouvée."})

        entreprise = Entreprise.objects.filter(uuid=entreprise_id).first()

        # Données historiques
        ref = sortie.ref
        qte = sortie.qte
        pu = sortie.pu
        entrer = sortie.entrer
        libelle = entrer.libelle
        categorie = entrer.souscategorie.libelle
        utilisateur = request.user

        # -----------------------------
        # 🔥 1. ANNULATION (on remet la quantité)
        # -----------------------------
        if action_type == "cancel":

            # On remet la quantité initiale
            entrer.qte += int(qte)
            entrer.save()

            # Historique
            HistoriqueSortie.objects.create(
                ref=ref,
                entreprise=entreprise,
                action="annuller",
                categorie=f"{categorie} ({libelle})",
                libelle=f"Sortie annulée par {utilisateur.first_name} {utilisateur.last_name}",
                qte=qte,
                description=description,
                pu=pu,
                utilisateur=utilisateur,
                sortie=sortie
            )

            # Suppression réelle
            sortie.delete()

            response_data["etat"] = True
            response_data["message"] = "Sortie annulée avec succès"
            return JsonResponse(response_data)

        # -----------------------------
        # 🔥 2. SUPPRESSION DÉFINITIVE
        # -----------------------------
        elif action_type == "delete":

            # Historique
            HistoriqueSortie.objects.create(
                ref=ref,
                entreprise=entreprise,
                action="deleted",
                categorie=f"{categorie} ({libelle})",
                libelle=f"Produit supprimé par {utilisateur.first_name} {utilisateur.last_name}",
                qte=qte,
                pu=pu,
                description=description,
                utilisateur=utilisateur,
                sortie=sortie
            )

            # Suppression réelle
            sortie.delete()

            response_data["etat"] = True
            response_data["message"] = "Sortie supprimée définitivement"
            return JsonResponse(response_data)

        else:
            return JsonResponse({"etat": False, "message": "Action invalide (cancel/delete attendu)"})

    return JsonResponse(response_data)


@csrf_exempt
def get_sortie_un(request, uuid):
    response_data = {'message': "requette invalide", 'etat': False}

    livre = Sortie.objects.all().filter(uuid=uuid).first()

    if livre:
        livre_data = {
            "id": livre.id,
            "uuid": livre.uuid,
            "qte": livre.qte,
            "pu": livre.pu,
            "ref": livre.ref,
            "image": livre.entrer.souscategorie.image.url if livre.entrer.souscategorie.image else None,
            "categorie_libelle": livre.entrer.souscategorie.libelle,
            # "entre_id": livre.inventaire.slug,
        }

        response_data["etat"] = True
        response_data["message"] = "success"
        response_data["donnee"] = livre_data
    else:
        response_data["message"] = "livre non trouver"

    return JsonResponse(response_data)


# @csrf_exempt
# @token_required
# def get_sorties_entreprise(request, uuid):
#     try:
#         # Récupérer l'utilisateur avec l'ID donné
#         utilisateur = Utilisateur.objects.get(uuid=uuid)
#
#         # Récupérer toutes les entreprises associées à cet utilisateur
#         entreprises = utilisateur.entreprises.all()
#
#         # Récupérer toutes les catégories associées à ces entreprises
#         categories = Categorie.objects.filter(entreprise__in=entreprises)
#         souscategories = SousCategorie.objects.filter(categorie__in=categories)
#
#         entrers = Entrer.objects.filter(souscategorie__in=souscategories)
#
#         sorties = Sortie.objects.filter(entrer__in=entrers)
#
#         # Préparer les données de la réponse
#         categories_data = [
#             {
#                 "id": liv.id,
#                 "uuid": liv.uuid,
#                 "slug": liv.slug,
#                 "pu": liv.pu,
#                 "qte": liv.qte,
#                 "categorie_libelle": liv.entrer.souscategorie.libelle,
#                 "client": liv.client.nom if liv.client else None,
#                 "libelle": liv.entrer.libelle,
#                 "prix_total": liv.prix_total,
#                 "somme_total": liv.somme_total,
#                 "prix_sortie": liv.entrer.qte,
#                 "date": str(liv.created_at),
#                 # "slug": categorie.slug,
#                 # "sous_categorie_count": categorie.sous_categorie.count(),
#                 # "entreprise": categorie.entreprise.nom
#             }
#             for liv in sorties
#         ]
#
#         response_data = {
#             "etat": True,
#             "message": "Catégories récupérées avec succès",
#             "donnee": categories_data
#         }
#     except Utilisateur.DoesNotExist:
#         response_data = {
#             "etat": False,
#             "message": "Utilisateur non trouvé"
#         }
#
#     return JsonResponse(response_data)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_sorties_entreprise(request, uuid):
    try:
        # Vérifier si l'entreprise existe
        entreprise = Entreprise.objects.get(uuid=uuid)

        # Récupérer toutes les sous-catégories associées à cette entreprise
        souscategories = SousCategorie.objects.filter(categorie__entreprise=entreprise)

        # Récupérer toutes les entrées liées à ces sous-catégories
        entrers = Entrer.objects.filter(souscategorie__in=souscategories)

        # Récupérer toutes les sorties liées à ces entrées
        sorties = Sortie.objects.filter(entrer__in=entrers)

        # Préparer les données pour la réponse
        sorties_data = [
            {
                "id": sortie.id,
                "uuid": sortie.uuid,
                "slug": sortie.slug,
                "pu": sortie.pu,
                "ref": sortie.ref,
                "qte": sortie.qte,
                "is_remise": sortie.is_remise,
                "categorie_libelle": sortie.entrer.souscategorie.libelle,
                "client": sortie.client.nom if sortie.client else None,
                "libelle": sortie.entrer.libelle,
                "prix_total": sortie.prix_total,
                "somme_total": sortie.somme_total,
                "prix_sortie": sortie.entrer.qte,
                "image": sortie.entrer.souscategorie.image.url if sortie.entrer.souscategorie.image else None,
                "date": sortie.created_at.strftime("%Y-%m-%d"),
            }
            for sortie in sorties
        ]

        response_data = {
            "etat": True,
            "message": "Sorties récupérées avec succès",
            "donnee": sorties_data
        }

    except Entreprise.DoesNotExist:
        response_data = {
            "etat": False,
            "message": "Entreprise non trouvée"
        }
    except Exception as e:
        response_data = {
            "etat": False,
            "message": f"Erreur interne : {str(e)}"
        }

    return JsonResponse(response_data)


# Facture Entrer


class AddFactureEntreView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        facture = request.FILES.get('facture')

        libelle = data.get("libelle")
        ref = data.get("ref")
        date = data.get("date")
        admin_id = data.get("user_id")
        entreprise_id = data.get("entreprise_id")

        if not admin_id:
            return Response({"etat": False, "message": "user_id manquant"}, status=status.HTTP_400_BAD_REQUEST)

        admin = request.user
        if not admin:
            return Response({"etat": False, "message": "Admin non trouvé"}, status=status.HTTP_400_BAD_REQUEST)

        # Vérification permission
        if not (admin.groups.filter(name="Admin").exists() or admin.groups.filter(name="Editor").exists()):
            return Response({"etat": False, "message": "Permission refusée"}, status=status.HTTP_403_FORBIDDEN)

        entreprise = Entreprise.objects.filter(uuid=entreprise_id).first()
        if not entreprise:
            return Response({"etat": False, "message": "Entreprise non trouvée"}, status=status.HTTP_400_BAD_REQUEST)

        # Création facture
        new_livre = FactEntre(
            ref=ref,
            facture=facture,
            libelle=libelle,
            date=date,
            entreprise=entreprise
        )
        new_livre.save()

        return Response({
            "etat": True,
            "id": new_livre.id,
            "slug": new_livre.slug,
            "message": "success"
        }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_facture_entre(request):
    response_data = {'message': "requête invalide", 'etat': False}

    if request.method == "POST":
        form = request.POST
        facture = request.FILES.get('facture')

        if "uuid" in form or "slug" in form and "user_id" in form:
            entreprise_id = form.get("uuid")
            slug = form.get("slug")
            user_id = form.get("user_id")
            user = Utilisateur.objects.filter(uuid=user_id).first()

            if user:
                # if user.has_perm('entreprise.change_categorie'):
                if (user.groups.filter(name="Admin").exists()
                        or user.groups.filter(name="Editor").exists()
                        or user.groups.filter(name="Author").exists()
                ):
                    if entreprise_id:
                        categorie_from_database = FactEntre.objects.all().filter(uuid=entreprise_id).first()
                    else:
                        categorie_from_database = FactEntre.objects.all().filter(slug=slug).first()

                    if not categorie_from_database:
                        response_data["message"] = "catégorie non trouvée"
                    else:
                        modifier = False

                        libelle = form.get("libelle")
                        if libelle:
                            categorie_from_database.libelle = libelle
                            modifier = True

                        ref = form.get("ref")
                        if ref:
                            categorie_from_database.ref = ref
                            modifier = True

                        date = form.get("date")
                        if date:
                            categorie_from_database.date = date
                            modifier = True

                        if facture:
                            categorie_from_database.facture = facture
                            modifier = True

                        if modifier:
                            categorie_from_database.save()
                            response_data["etat"] = True
                            response_data["message"] = "success"
                else:
                    response_data["message"] = "Vous n'avez pas la permission de modifier les catégories."
            else:
                response_data["message"] = "Utilisateur non trouvé."

    return JsonResponse(response_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def del_facture_entre(request):
    response_data = {'message': "Requete invalide", 'etat': False}

    if request.method == "POST":
        try:
            form = json.loads(request.body.decode("utf-8"))
            id = form.get("uuid")
            slug = form.get("slug")
            user_id = form.get("user_id")
        except json.JSONDecodeError:
            return JsonResponse({'message': "Erreur lors de la lecture des donnees JSON", 'etat': False})

        user = Utilisateur.objects.filter(uuid=user_id).first()

        if user:
            # if user.has_perm('entreprise.delete_entrer'):
            if (user.groups.filter(name="Admin").exists()
                    or user.groups.filter(name="Editor").exists()
                    or user.groups.filter(name="Author").exists()
            ):
                if id or slug:
                    if id:
                        livre_from_database = FactEntre.objects.filter(uuid=id).first()
                    else:
                        livre_from_database = FactEntre.objects.filter(slug=slug).first()

                    if not livre_from_database:
                        response_data["message"] = "FactEntre non trouvée"
                    else:
                        livre_from_database.delete()
                        response_data["etat"] = True
                        response_data["message"] = "Success"
                else:
                    response_data["message"] = "ID ou slug de la catégorie manquant"
            else:
                # L'utilisateur n'a pas la permission d'ajouter une catégorie
                response_data["message"] = "Vous n'avez pas la permission de supprimer une souscatégorie."
        else:
            response_data["message"] = "Utilisateur non trouvé."
    return JsonResponse(response_data)


@csrf_exempt
def get_facture_entre_un(request, uuid):
    response_data = {'message': "requette invalide", 'etat': False}

    livre = FactEntre.objects.all().filter(uuid=uuid).first()

    if livre:
        livre_data = {
            "id": livre.id,
            "uuid": livre.uuid,
            "slug": livre.slug,
            "libelle": livre.libelle,
            "ref": livre.ref,
            "facture": livre.facture.url if livre.facture else None,
            "date": livre.date
        }

        response_data["etat"] = True
        response_data["message"] = "success"
        response_data["donnee"] = livre_data
    else:
        response_data["message"] = "Entrer non trouver"

    return JsonResponse(response_data)


# @csrf_exempt
# @token_required
# def get_facEntres_utilisateur(request, uuid):
#     try:
#         # Récupérer l'utilisateur avec l'ID donné
#         utilisateur = Utilisateur.objects.get(uuid=uuid)
#
#         entreprises = utilisateur.entreprises.all()
#
#         factEntres = FactEntre.objects.filter(entreprise__in=entreprises)
#
#         # Préparer les données de la réponse
#         categories_data = [
#             {
#                 "id": liv.id,
#                 "uuid": liv.uuid,
#                 "slug": liv.slug,
#                 "libelle": liv.libelle,
#                 "ref": liv.ref,
#                 "facture": liv.facture.url if liv.facture else None,
#                 "date": liv.date.strftime("%d-%m-%Y"),
#             }
#             for liv in factEntres
#         ]
#
#         response_data = {
#             "etat": True,
#             "message": "FactEntrer récupérées avec succès",
#             "donnee": categories_data
#         }
#     except Utilisateur.DoesNotExist:
#         response_data = {
#             "etat": False,
#             "message": "Utilisateur non trouvé"
#         }
#
#     return JsonResponse(response_data)

class FacEntresUserAPIView(APIView):
    def get(self, request, entreprise_id):
        try:
            # Récupérer l'utilisateur avec l'UUID donné
            utilisateur = request.user

            # Vérifier si l'entreprise existe et si elle est associée à l'utilisateur
            entreprise = Entreprise.objects.filter(uuid=entreprise_id, utilisateurs=utilisateur).first()
            if not entreprise:
                return JsonResponse({
                    "etat": False,
                    "message": "Entreprise non trouvée ou non associée à l'utilisateur"
                })

            # Récupérer les factures d'entrée liées à l'entreprise
            factEntres = FactEntre.objects.filter(entreprise=entreprise)

            # Préparer les données des factures pour la réponse
            factures_data = [
                {
                    "id": fac.id,
                    "uuid": fac.uuid,
                    "slug": fac.slug,
                    "libelle": fac.libelle,
                    "ref": fac.ref,
                    "facture": fac.facture.url if fac.facture else None,
                    "date": fac.date.strftime("%Y-%m-%d"),
                }
                for fac in factEntres
            ]

            response_data = {
                "etat": True,
                "message": "Factures d'entrée récupérées avec succès",
                "donnee": factures_data
            }
        except Utilisateur.DoesNotExist:
            response_data = {
                "etat": False,
                "message": "Utilisateur non trouvé"
            }

        return JsonResponse(response_data)


# Facture Sortie

class AddFactureSortieView(APIView):

    def post(self, request):
        libelle = request.POST.get("libelle")
        ref = request.POST.get("ref")
        date = request.POST.get("date")
        facture = request.FILES.get("facture")
        admin_id = request.POST.get("user_id")
        entreprise_id = request.POST.get("entreprise_id")

        if not admin_id:
            return Response({"etat": False, "message": "Admin requis"}, status=status.HTTP_400_BAD_REQUEST)

        admin = Utilisateur.objects.filter(uuid=admin_id).first()
        if not admin:
            return Response({"etat": False, "message": "Admin non trouvé"}, status=status.HTTP_404_NOT_FOUND)

        if not (admin.groups.filter(name="Admin").exists() or
                admin.groups.filter(name="Editor").exists() or
                admin.groups.filter(name="Author").exists()):
            return Response({"etat": False, "message": "Permission refusée"}, status=status.HTTP_403_FORBIDDEN)

        entreprise = Entreprise.objects.filter(uuid=entreprise_id).first()
        if not entreprise:
            return Response({"etat": False, "message": "Entreprise non trouvée"}, status=status.HTTP_404_NOT_FOUND)

        facture_obj = FactSortie(ref=ref, facture=facture, libelle=libelle, date=date, entreprise=entreprise)
        facture_obj.save()

        return Response({
            "etat": True,
            "message": "success",
            "id": facture_obj.id,
            "slug": facture_obj.slug
        }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_facture_sortie(request):
    response_data = {'message': "requête invalide", 'etat': False}

    if request.method == "POST":
        form = request.POST
        facture = request.FILES.get('facture')

        if "id" in form or "slug" in form and "user_id" in form:
            entreprise_id = form.get("uuid")
            slug = form.get("slug")
            user_id = form.get("user_id")
            user = Utilisateur.objects.filter(uuid=user_id).first()

            if user:
                # if user.has_perm('entreprise.change_categorie'):
                if (user.groups.filter(name="Admin").exists()
                        or user.groups.filter(name="Editor").exists()
                        or user.groups.filter(name="Author").exists()
                ):
                    if entreprise_id:
                        categorie_from_database = FactSortie.objects.all().filter(uuid=entreprise_id).first()
                    else:
                        categorie_from_database = FactSortie.objects.all().filter(slug=slug).first()

                    if not categorie_from_database:
                        response_data["message"] = "catégorie non trouvée"
                    else:
                        modifier = False

                        libelle = form.get("libelle")
                        if libelle:
                            categorie_from_database.libelle = libelle
                            modifier = True

                        ref = form.get("ref")
                        if ref:
                            categorie_from_database.ref = ref
                            modifier = True

                        date = form.get("date")
                        if date:
                            categorie_from_database.date = date
                            modifier = True

                        if facture:
                            categorie_from_database.facture = facture
                            modifier = True

                        if modifier:
                            categorie_from_database.save()
                            response_data["etat"] = True
                            response_data["message"] = "success"
                else:
                    response_data["message"] = "Vous n'avez pas la permission de modifier les catégories."
            else:
                response_data["message"] = "Utilisateur non trouvé."

    return JsonResponse(response_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def del_facture_sortie(request):
    response_data = {'message': "Requete invalide", 'etat': False}

    if request.method == "POST":
        try:
            form = json.loads(request.body.decode("utf-8"))
            id = form.get("uuid")
            slug = form.get("slug")
            user_id = form.get("user_id")
        except json.JSONDecodeError:
            return JsonResponse({'message': "Erreur lors de la lecture des donnees JSON", 'etat': False})

        user = Utilisateur.objects.filter(uuid=user_id).first()

        if user:
            # if user.has_perm('entreprise.delete_entrer'):
            if (user.groups.filter(name="Admin").exists()
                    or user.groups.filter(name="Editor").exists()
                    or user.groups.filter(name="Author").exists()
            ):
                if id or slug:
                    if id:
                        livre_from_database = FactSortie.objects.filter(uuid=id).first()
                    else:
                        livre_from_database = FactSortie.objects.filter(slug=slug).first()

                    if not livre_from_database:
                        response_data["message"] = "Catégorie non trouvée"
                    else:
                        livre_from_database.delete()
                        response_data["etat"] = True
                        response_data["message"] = "Success"
                else:
                    response_data["message"] = "ID ou slug de la catégorie manquant"
            else:
                # L'utilisateur n'a pas la permission d'ajouter une catégorie
                response_data["message"] = "Vous n'avez pas la permission de supprimer une souscatégorie."
        else:
            response_data["message"] = "Utilisateur non trouvé."
    return JsonResponse(response_data)


@csrf_exempt
def get_facture_sortie_un(request, uuid):
    response_data = {'message': "requette invalide", 'etat': False}

    livre = FactSortie.objects.all().filter(uuid=uuid).first()

    if livre:
        livre_data = {
            "id": livre.id,
            "uuid": livre.uuid,
            "slug": livre.slug,
            "libelle": livre.libelle,
            "ref": livre.ref,
            "facture": livre.facture.url if livre.facture else None,
            "date": livre.date
            # "date": livre.date.strftime("%d-%m-%Y"),
        }

        response_data["etat"] = True
        response_data["message"] = "success"
        response_data["donnee"] = livre_data
    else:
        response_data["message"] = "Entrer non trouver"

    return JsonResponse(response_data)


class FacSortiesUserAPIView(APIView):

    def get(self, request, entreprise_id):
        try:
            # Récupérer l'utilisateur avec l'ID donné
            utilisateur = request.user

            # entreprises = utilisateur.entreprises.all()
            entreprise = Entreprise.objects.filter(uuid=entreprise_id, utilisateurs=utilisateur).first()
            if not entreprise:
                return JsonResponse({
                    "etat": False,
                    "message": "Entreprise non trouvée ou non associée à l'utilisateur"
                })

            entrers = FactSortie.objects.filter(entreprise=entreprise)

            # Préparer les données de la réponse
            categories_data = [
                {
                    "id": liv.id,
                    "uuid": liv.uuid,
                    # "categorie_libelle": liv.souscategorie.libelle,
                    "slug": liv.slug,
                    "libelle": liv.libelle,
                    "ref": liv.ref,
                    "facture": liv.facture.url if liv.facture else None,
                    "date": liv.date.strftime("%Y-%m-%d"),
                }
                for liv in entrers
            ]

            response_data = {
                "etat": True,
                "message": "FactEntrer récupérées avec succès",
                "donnee": categories_data
            }
        except Utilisateur.DoesNotExist:
            response_data = {
                "etat": False,
                "message": "Utilisateur non trouvé"
            }

        return JsonResponse(response_data)


# Autre

class InfoSousCatView(APIView):

    def post(self, request, *args, **kwargs):
        slug = request.data.get("slug")

        if not slug:
            return Response(
                {"etat": False, "message": "slug non fourni"},
                status=status.HTTP_400_BAD_REQUEST
            )

        entrers = Sortie.objects.filter(entrer__souscategorie__uuid=slug)
        invents = Entrer.objects.filter(souscategorie__uuid=slug)

        if not entrers.exists():
            return Response(
                {"etat": False, "message": "vide"},
                status=status.HTTP_200_OK
            )

        # Sorties
        sortie_data = [
            {
                "id": entrer.entrer.id,
                "libelle": entrer.entrer.libelle,
                "client": entrer.client.nom if entrer.client else None,
                "pu": entrer.pu,
                "qte": entrer.qte,
                "date": entrer.created_at,
                "prix_total": entrer.prix_total,
            }
            for entrer in entrers
        ]

        # Inventaires
        inventaire_data = [
            {
                "prix_total": entrer.prix_total,
                "libelle": entrer.libelle,
                "pu": entrer.pu,
                "pu_achat": entrer.pu_achat,
                "date": entrer.created_at,
                "client": entrer.client.nom if entrer.client else None,
                "qte": entrer.qte,
            }
            for entrer in invents
        ]

        sortie_data.append({"sortie": inventaire_data})

        return Response(
            {"etat": True, "message": "success", "donnee": sortie_data},
            status=status.HTTP_200_OK
        )


class UtilisateurEntrepriseHistoriqueView(APIView):

    def get(self, request):
        try:
            # Récupérer l'utilisateur avec l'ID donné
            utilisateur = request.user

            # Récupérer les entreprises associées à cet utilisateur
            entreprises = utilisateur.entreprises.all()

            # Préparer les données de la réponse
            entreprises_data = []
            for entreprise in entreprises:
                # Récupérer tous les historiques d'entrer de cette entreprise
                historiques_entrer = HistoriqueEntrer.objects.filter(
                    entrer__souscategorie__categorie__entreprise=entreprise
                )

                # Récupérer tous les historiques de sortie de cette entreprise
                historiques_sortie = HistoriqueSortie.objects.filter(
                    sortie__entrer__souscategorie__categorie__entreprise=entreprise
                )

                # Combiner les deux ensembles d'historiques et les trier par date
                historiques_combines = list(chain(historiques_entrer, historiques_sortie))
                historiques_combines.sort(key=lambda x: x.created_at, reverse=True)

                # Préparer les données d'historique pour la entreprise
                historiques_data = []
                for historique in historiques_combines:
                    if hasattr(historique, 'entrer'):
                        historique_data = {
                            "type": "entrer",
                            "ref": historique.entrer.ref,
                            "action": historique.action,
                            "qte": historique.qte,
                            "ancien_qte": historique.ancien_qte,
                            "cumuler_qe": historique.cumuler_qe,
                            "description": historique.description,
                            "pu": historique.pu,
                            "libelle": historique.libelle,
                            "categorie": historique.categorie,
                            "date": historique.created_at,
                        }
                    elif hasattr(historique, 'sortie'):
                        historique_data = {
                            "type": "sortie",
                            "ref": historique.sortie.ref,
                            "action": historique.action,
                            "qte": historique.qte,
                            "pu": historique.pu,
                            "libelle": historique.libelle,
                            "categorie": historique.categorie,
                            "date": historique.created_at,
                        }
                    historiques_data.append(historique_data)

                # Ajouter les informations de la entreprise et son historique
                entreprise_data = {
                    "id": entreprise.id,
                    "nom": entreprise.nom,
                    "adresse": entreprise.adresse,
                    "numero": entreprise.numero,
                    "email": entreprise.email,
                    "historique": historiques_data
                }

                entreprises_data.append(entreprise_data)

            response_data = {
                "etat": True,
                "message": "entreprises et historiques récupérés avec succès",
                "donnee": entreprises_data
            }

        except Utilisateur.DoesNotExist:
            response_data = {
                "etat": False,
                "message": "Utilisateur non trouvé"
            }

        return JsonResponse(response_data)


class UtilisateurEntrepriseHistoriqueSuppView(APIView):

    def get(self, request, entreprise_uuid):
        try:
            # Récupérer l'utilisateur avec l'ID donné
            utilisateur = request.user
            entreprise = Entreprise.objects.get(uuid=entreprise_uuid)

            # Récupérer tous les historiques d'entrer de cette entreprise
            historiques_entrer = HistoriqueEntrer.objects.filter(
                entreprise=entreprise
            )

            # Récupérer tous les historiques de sortie de cette entreprise
            historiques_sortie = HistoriqueSortie.objects.filter(
                entreprise=entreprise
            )

            # Combiner les deux ensembles d'historiques et les trier par date
            historiques_combines = list(chain(historiques_entrer, historiques_sortie))
            historiques_combines.sort(key=lambda x: x.created_at, reverse=True)

            # Préparer les données d'historique pour la entreprise
            historiques_data = []
            for historique in historiques_combines:
                if hasattr(historique, 'entrer'):
                    historique_data = {
                        "type": "entrer",
                        # "ref": historique.entrer.ref,
                        "action": historique.action,
                        "qte": historique.qte,
                        "pu": historique.pu,
                        "libelle": historique.libelle,
                        "description": historique.description,
                        "categorie": historique.categorie,
                        "date": historique.created_at,
                    }
                elif hasattr(historique, 'sortie'):
                    historique_data = {
                        "type": "sortie",
                        # "ref": historique.sortie.ref,
                        "action": historique.action,
                        "qte": historique.qte,
                        "pu": historique.pu,
                        "libelle": historique.libelle,
                        "description": historique.description,
                        "categorie": historique.categorie,
                        "date": historique.created_at,
                    }
                historiques_data.append(historique_data)

            response_data = {
                "etat": True,
                "message": "entreprises et historiques récupérés avec succès",
                "donnee": historiques_data
            }

        except Utilisateur.DoesNotExist:
            response_data = {
                "etat": False,
                "message": "Utilisateur non trouvé"
            }

        return JsonResponse(response_data)


@csrf_exempt
def ordre_paiement(request):
    response_data = {'message': "requette invalide", 'etat': False}

    if request.method == "POST":
        form = dict()
        try:
            form = json.loads(request.body.decode("utf-8"))
        except:
            ...

        if "moyen_paiement" in form and "entreprise_id" in form and "client_id":

            moyen_paiement = form.get("moyen_paiement")
            entreprise_id = form.get("entreprise_id")
            client_id = form.get("client_id")

            entreprise = Entreprise.objects.all().filter(uuid=entreprise_id).first()
            if entreprise:
                client = Utilisateur.objects.all().filter(uuid=client_id).first()

                if client:

                    ordre_donner = False
                    order_id = get_order_id(entreprise_order_id_len)

                    while PaiementEntreprise.objects.all().filter(order_id=order_id).first():
                        order_id = get_order_id(entreprise_order_id_len)

                    montant = form.get("montant") if "montant" in form else entreprise.prix

                    strip_link = None
                    description = form.get("description")

                    tm = reverse('ordre_paiement', kwargs={'order_id': "seyba"})
                    notify_url = f"{request.scheme}://{request.get_host()}{tm}"

                    operation = None

                    # TODO verifier si le montant est supperieur à un minimum ?

                    numero = form.get("numero")

                    if moyen_paiement == "Orange Money":
                        # paiement orange
                        if numero and verifier_numero(numero):
                            operation = paiement_orange(
                                montant=montant,
                                numero=numero,
                                order_id=order_id,
                                notify_url=notify_url
                            )

                            if operation:
                                if operation["etat"] == "OK":
                                    ordre_donner = True
                                    response_data["etat"] = True
                                    response_data["message"] = operation["message"]
                            else:
                                response_data["message"] = response_data["message"] = operation["message"]
                        else:
                            response_data["message"] = "numero invalide"

                    elif moyen_paiement == "Moov Money":

                        if numero and verifier_numero(numero):
                            operation = paiement_moov(montant=montant,
                                                      numero=numero,
                                                      order_id=order_id,
                                                      description=f"{description}",
                                                      remarks="remarks",
                                                      notify_url=notify_url)

                            if operation and operation["status"] == 0 and operation["etat"] == "OK":
                                ordre_donner = True
                                response_data["etat"] = True
                                response_data["message"] = operation["message"]
                            else:
                                response_data["message"] = "Une erreur s'est produite"
                                try:
                                    if "message" in operation:
                                        response_data["message"] = operation["message"]
                                except:
                                    ...

                        else:
                            response_data["message"] = "numero invalide"

                    elif moyen_paiement == "Sama Money":

                        if numero and verifier_numero(numero):
                            operation = sama_pay(montant=montant,
                                                 order_id=order_id,
                                                 numero=numero,
                                                 description=f"{description}",
                                                 notify_url=notify_url)
                            if operation and operation["etat"] == "OK" and operation["status"] == 1:
                                ordre_donner = True
                                response_data["etat"] = True
                                response_data["message"] = operation["msg"]
                            else:
                                response_data["message"] = operation["message"]
                        else:
                            response_data["message"] = "numero invalide"


                    elif moyen_paiement == "Carte Visa":
                        if "return_url" in form and "name" in form:
                            return_url = form.get("return_url")
                            name = form.get("name")

                            description = f"{description}"

                            name = f"{name}"  # TODO

                            operation = stripe_pay(montant=montant,
                                                   name=name,
                                                   description=description,
                                                   return_url=return_url,
                                                   order_id=order_id,
                                                   notify_url=notify_url)

                            if operation and operation["etat"] == "OK":
                                response_data["url"] = operation["url"]
                                strip_link = operation["url"]
                                ordre_donner = True
                            else:
                                response_data["message"] = operation["message"]


                    else:
                        response_data["message"] = "moyen de paiement invalide"

                    if not ordre_donner:
                        # verification
                        operation = verifier_status(order_id)

                        if "message" in operation and "operator" in operation:
                            ordre_donner = True

                    if ordre_donner:
                        new_paiement = PaiementEntreprise(order_id=order_id,
                                                          moyen_paiement=moyen_paiement,
                                                          montant=montant,
                                                          entreprise=entreprise,
                                                          client=client,
                                                          numero=numero)

                        if strip_link:
                            new_paiement.strip_link = strip_link

                        new_paiement.save()

                        response_data["message"] = "Paiement enregistré, en attente de confirmation du client"
                        response_data["etat"] = True
                        response_data["order_id"] = order_id
                    else:
                        ...
                        # response_data["message"] = "une erreur s'est produit."

                else:
                    response_data["message"] = "utilisateur non trouver"
            else:
                response_data["message"] = "formation non trouver"

    return HttpResponse(json.dumps(response_data), content_type="application/json")


@csrf_exempt
def pay_entreprise_get_historique(request):
    response_data = {'message': "requette invalide", 'etat': False}

    if request.method == "POST":
        form = dict()
        try:
            form = json.loads(request.body.decode("utf-8"))
        except:
            ...

        filtrer = False
        historique = PaiementEntreprise.objects.all()
        if "entreprise_id" in form:
            entreprise_id = form.get("entreprise_id")

            entreprise = Entreprise.objects.all().filter(uuid=entreprise_id).first()

            if entreprise:
                historique = historique.filter(entreprise=entreprise)
                filtrer = True

            else:
                response_data["message"] = "vide"

        if "utilisateur_id" in form:
            utilisateur_id = form.get("utilisateur_id")

            client = Utilisateur.objects.all().filter(uuid=utilisateur_id).first()

            if client:
                historique = historique.filter(client=client)
                filtrer = True
            else:
                response_data["message"] = "utilisateur non trouver"

        if "all" in form:
            filtrer = True

        historique_data = list()

        for h in historique:
            historique_data.append(
                {
                    "order_id": h.order_id,
                    "payer": h.payer,
                    "moyen_paiement": h.moyen_paiement,
                    "date_soumission": str(h.date_soumission),
                    "date_validation": str(h.date_validation),
                    "montant": h.montant,
                    "entreprise": {
                        "slug": h.entreprise.slug,
                        "id": h.entreprise.uuid,
                        "nom": h.entreprise.nom,
                    },
                    "client_id": h.client.id,
                    "numero": h.numero,
                    "strip_link": h.strip_link,
                }
            )
        if len(historique_data) > 0:
            response_data["etat"] = True
            response_data["message"] = "success"
            response_data["donnee"] = historique_data
        else:
            response_data["message"] = "vide"

    return HttpResponse(json.dumps(response_data), content_type="application/json")


# @csrf_exempt
# def pay_formation_verifier(request):
#     response_data = {'message': "requette invalide", 'etat': False}
#
#     if request.method == "POST":
#         form = dict()
#         try:
#             form = json.loads(request.body.decode("utf-8"))
#         except:
#             ...
#
#         if "order_id" in form:
#             order_id = form.get("order_id")
#
#             paiement_formation = PaiementEntreprise.objects.all().filter(order_id=order_id).first()
#
#             if paiement_formation:
#                 operation = verifier_status(order_id)
#
#                 if not paiement_formation.payer:
#                     if operation and operation["etat"] == "OK":
#                         new_cour = Cour(apprenant=paiement_formation.client,
#                                         formation=paiement_formation.formation,
#                                         montant=paiement_formation.montant)
#                         new_cour.save()
#
#                         paiement_formation.payer = True
#                         paiement_formation.date_validation = str(datetime.datetime.now())
#
#                         paiement_formation.save()
#
#                         response_data["etat"] = True
#                         response_data["message"] = "success"
#                         response_data["id"] = new_cour.id
#
#                     else:
#                         response_data["message"] = operation["message"]
#
#                 else:
#                     response_data["message"] = "operation deja ternimer"
#
#             else:
#                 response_data["message"] = "opertion non trouver"
#
#     return HttpResponse(json.dumps(response_data), content_type="application/json")


@csrf_exempt
def paiement_entreprise_callback(request, order_id):
    response_data = {'message': "requette invalide", 'etat': False}

    if request.method == "POST":
        form = dict()
        try:
            form = json.loads(request.body.decode("utf-8"))
        except:
            ...

        response_data["message"] = "opertion non trouver"

    return HttpResponse(json.dumps(response_data), content_type="application/json")
