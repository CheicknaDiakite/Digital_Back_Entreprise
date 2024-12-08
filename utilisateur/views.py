import codecs
import json

from django.contrib.auth import authenticate, logout
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import csrf_exempt

from .models import Token, Utilisateur
from fonction import token_required

from entreprise.models import Entreprise

from root.mailer import send


# Create your views here.
@csrf_exempt
def api_user_login(request):
    response_data = {'message': "requête invalide", 'etat': False}

    if request.method == "POST":
        try:
            form = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({'message': "Erreur lors de la lecture des données JSON", 'etat': False})

        # if "username" in form and "password" in form:
        #     username = form.get("username")
        #     password = form.get("password")
        #
        #     user = authenticate(request, username=username, password=password)
        #     if user is not None:
        #         # Supprimer le token existant (si présent) et en créer un nouveau
        #         Token.objects.filter(user=user).delete()
        #         token = Token.objects.create(user=user)
        #
        #         response_data["etat"] = True
        #         response_data["id"] = user.uuid
        #         response_data["token"] = str(token.token)
        #         response_data["message"] = "Connexion réussie"
        #     else:
        #         user = Utilisateur.objects.filter(username=username).first()
        #         if user is not None:
        #             response_data["message"] = "Utilisateur ou mot de passe incorrect"
        #         else:
        #             response_data["message"] = "Utilisateur ou mot de passe incorrect."
        # else:
        #     response_data["message"] = "Nom d'utilisateur ou mot de passe manquant"
        if "username" in form and "password" in form:
            login_input = form.get("username").strip()  # Peut être un numéro de téléphone ou un username
            password = form.get("password").strip()

            # Tentez de trouver l'utilisateur par le nom d'utilisateur ou le téléphone
            user = Utilisateur.objects.filter(username=login_input).first() or \
                   Utilisateur.objects.filter(numero=login_input).first()

            if user:
                # Validez le mot de passe
                if check_password(password, user.password):
                    # Authentifiez et créez un nouveau token
                    Token.objects.filter(user=user).delete()
                    token = Token.objects.create(user=user)

                    response_data["etat"] = True
                    response_data["id"] = user.uuid
                    response_data["token"] = str(token.token)
                    response_data["message"] = "Connexion réussie"
                else:
                    response_data["message"] = "Utilisateur ou mot de passe incorrect"
            else:
                response_data["message"] = "Utilisateur introuvable"
        else:
            response_data["message"] = "Nom d'utilisateur ou mot de passe manquant"
    return JsonResponse(response_data)


@csrf_exempt
def api_user_register(request):
    response_data = {'message': "Requête invalide", 'etat': False, 'id': ""}

    if request.method == "POST":
        try:
            form = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse(response_data)

        required_fields = ["password", "first_name", "last_name", "email"]
        if all(field in form for field in required_fields):
            password = form.get("password")
            first_name = form.get("first_name")
            numero = form.get("numero")
            pays = form.get("pays")
            last_name = form.get("last_name")
            email = form.get("email")

            # Génération du nom d'utilisateur unique
            base_username = f"{first_name[:2].lower()}0001{last_name[:2].lower()}"
            username = base_username
            counter = 1
            while Utilisateur.objects.filter(username=username).exists():
                counter += 1
                username = f"{first_name[:2].lower()}{counter:04d}{last_name[:2].lower()}"

            # Vérification de l'existence de l'email
            if Utilisateur.objects.filter(email=email).exists():
                response_data["message"] = "Cet email est déjà utilisé"
            elif Utilisateur.objects.filter(numero=numero).exists():
                response_data["message"] = "Cet numero est déjà utilisé"
            else:
                try:
                    # Préparation de l'e-mail de confirmation
                    html_text = render_to_string('mail.html', context={
                        "sujet": "Inscription reçu chez Diakite Digital",
                        "message": (
                            f"Bonjour <b>{first_name} {last_name}</b>,<br><br>"
                            "Votre inscription est réussi.<br><br>"
                            "Merci d'avoir choisi Diakite Digital ! <br><br> Vous pouvez maintenant utiliser tous nos services apres la verification par un de nos administrateur."
                            "l'intérêt que vous portez à notre entreprise. Nous allons étudier votre incription<br><br>"
                            # "et nous vous contacterons dans les meilleurs délais.<br><br>"
                            f"Votre Nom d'utilisateur est: <b>{username}</b>"
                        )
                    })

                    # Envoi de l'e-mail de confirmation
                    email_sent = send(
                        sujet="Inscription reçu chez Diakite Digital",
                        message="",
                        email_liste=[email],
                        html_message=html_text,
                    )

                    if email_sent:
                        # Création de l'utilisateur uniquement si l'e-mail est envoyé
                        utilisateur = Utilisateur.objects.create_user(
                            first_name=first_name,
                            last_name=last_name,
                            username=username,
                            pays=pays,
                            numero=numero,
                            email=email,
                            password=password
                        )

                        # Authentification de l'utilisateur
                        new_utilisateur = authenticate(request, username=username, password=password)
                        if new_utilisateur is not None:
                            response_data["etat"] = True
                            response_data["id"] = utilisateur.id
                            response_data["message"] = "Utilisateur créé et authentifié avec succès"
                        else:
                            response_data["message"] = "Échec de l'authentification après création"
                    else:
                        response_data[
                            "message"] = "Échec de l'envoi de l'e-mail, verifier votre connexion. Inscription annulée."
                except Exception as e:
                    response_data["message"] = f"Erreur lors du traitement : {str(e)}"
        else:
            response_data["message"] = "Tous les champs obligatoires ne sont pas fournis"

    return JsonResponse(response_data)


@csrf_exempt
@token_required
def api_user_admin_register(request):
    response_data = {'message': "requête invalide", 'etat': False, 'id': ""}

    if request.method == "POST":
        try:
            form = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse(response_data)

        required_fields = ["username", "password", "first_name", "last_name", "email_user", "entreprise_id"]
        if all(field in form for field in required_fields):
            password = form.get("password")
            first_name = form.get("first_name")
            numero = form.get("numero")
            role = form.get("role")
            last_name = form.get("last_name")
            email_user = form.get("email_user")
            entreprise_id = form.get("entreprise_id")

            admin_user = request.user  # L'administrateur en cours
            created_users_count = Utilisateur.objects.filter(created_by=admin_user).count()

            if created_users_count >= 5:
                response_data["message"] = "Vous avez atteint la limite de 5 utilisateurs créés."
                return JsonResponse(response_data)

            if entreprise_id:
                # user_from_data_base.travail = travail
                entreprise = Entreprise.objects.get(uuid=entreprise_id)
            else:
                response_data["message"] = "Entreprise non selectionner"

            # Vérification de l'existence de l'utilisateur avec le même username ou email

            if Utilisateur.objects.filter(email_user=email_user).exists():
                response_data["message"] = "cet email est déjà utilisé"
            else:
                # Génération du nom d'utilisateur unique
                base_username = f"{first_name[:2].lower()}0001{last_name[:2].lower()}"
                username = base_username
                counter = 1
                while Utilisateur.objects.filter(username=username).exists():
                    counter += 1
                    username = f"{first_name[:2].lower()}{counter:04d}{last_name[:2].lower()}"

                try:
                    # Préparation de l'e-mail de confirmation
                    html_text = render_to_string('mail.html', context={
                        "sujet": "Inscription reçu chez Diakite Digital",
                        "message": (
                            f"Bonjour <b>{first_name} {last_name}</b>,<br><br>"
                            "Nous avons bien reçu votre inscription et nous vous remercions de "
                            "l'intérêt que vous portez à notre entreprise. Nous allons étudier votre demande "
                            "et nous vous contacterons dans les meilleurs délais.<br><br>"
                            f"Votre Nom d'utilisateur est: <b>{username}</b>"
                        )
                    })

                    # Envoi de l'e-mail de confirmation
                    email_sent = send(
                        sujet="Inscription reçu chez Diakite Digital",
                        message="",
                        email_liste=[request.user.email],
                        html_message=html_text,
                    )

                    if email_sent:

                        # Création de l'utilisateur avec le champ created_by
                        new_user = Utilisateur.objects.create_user(
                            first_name=first_name,
                            last_name=last_name,
                            username=username,
                            numero=numero,
                            role=role,
                            email_user=email_user,
                            password=password,
                            created_by=request.user  # L'administrateur qui a créé l'utilisateur
                        )
                        Utilisateur.objects.filter(username=username).first().entreprises.add(entreprise)
                        # Authentification de l'utilisateur
                        if new_user is not None:
                            response_data["etat"] = True
                            response_data["id"] = new_user.id
                            response_data["message"] = "success"
                        else:
                            response_data["message"] = "Échec de la création"
                    else:
                        response_data[
                            "message"] = "Échec de l'envoi de l'e-mail, verifier votre connexion. Inscription annulée."
                except Exception as e:
                    response_data["message"] = f"Erreur lors du traitement : {str(e)}"

    return JsonResponse(response_data)


@csrf_exempt
@token_required
def api_user_set_profil(request):
    response_data = {'message': "requette invalide", 'etat': False}

    if request.method == "POST":
        form = list()
        try:
            form = json.loads(request.body.decode("utf-8"))
        except:
            ...

        user_all = Utilisateur.objects.all()
        user_id = form.get("user_id")

        user_conect = user_all.filter(uuid=user_id).first()

        modifier = False
        if user_conect:

            if (user_conect.groups.filter(name="Admin").exists()
                    or user_conect.groups.filter(name="Editor").exists()
                    or user_conect.groups.filter(name="Editor").exists()
                    or user_conect.groups.filter(name="Visitor").exists()):
                # if user_conect.has_perm('entreprise.change_utilisateur'):
                id = form.get("uuid")

                user_from_data_base = user_all.filter(uuid=id).first()
                if user_from_data_base:

                    first_name = form.get("first_name")
                    if first_name:
                        user_from_data_base.first_name = first_name
                        modifier = True

                        # user_from_data_base.save()

                    last_name = form.get("last_name")
                    if last_name:
                        user_from_data_base.last_name = last_name
                        modifier = True

                    role = form.get("role")
                    if role:
                        user_from_data_base.role = role
                        modifier = True

                    pays = form.get("pays")
                    if role:
                        user_from_data_base.pays = pays
                        modifier = True

                    if "mail_verifier" in form:
                        user_from_data_base.mail_verifier = True
                        modifier = True

                    entreprise_id = form.get("entreprise_id")
                    if entreprise_id:
                        # user_from_data_base.travail = travail
                        entreprise = Entreprise.objects.get(uuid=entreprise_id)
                        user_from_data_base.entreprises.add(entreprise)  # Ajout de la entreprise à l'utilisateur
                        modifier = True

                    numero = form.get("numero")
                    if numero:

                        if user_from_data_base.numero != numero:
                            tmp_user = user_all.filter(numero=numero).first()
                            tmp_user1 = user_all.filter(username=numero).first()
                            if tmp_user or tmp_user1:
                                response_data["etat"] = False
                                response_data["message"] = "ce numéro est déjà utilisé"
                            else:
                                user_from_data_base.numero = numero
                                modifier = True
                        else:
                            response_data["message"] = "ce numéro est déjà utilisé"

                    email = form.get("email")
                    if email:

                        if user_from_data_base.email != email:
                            tmp_user = user_all.filter(email=email).first()
                            tmp_user1 = user_all.filter(username=email).first()

                            if tmp_user or tmp_user1:
                                response_data["etat"] = False
                                response_data["message"] = "cet email est déjà utilisé"
                            else:
                                user_from_data_base.email = email
                                modifier = True
                        else:
                            response_data["message"] = "cet email est déjà utilisé"

                    username = form.get("username")
                    if username:

                        if user_from_data_base.username != username:
                            tmp_user = user_all.filter(username=username).first()
                            tmp_user1 = user_all.filter(numero=username).first()

                            utiliser = False

                            if tmp_user or tmp_user1 or utiliser:
                                response_data["etat"] = False
                                response_data["message"] = "ce nom d'utilisateur est déjà utilisé"
                                # print(context)

                            else:
                                user_from_data_base.username = username
                                modifier = True
                        else:
                            response_data["message"] = "ce nom d'utilisateur est déjà utilisé"

                    if "new_password" in form and "old_password" in form:
                        new_password = form.get("new_password")
                        old_password = form.get("old_password")
                        username = user_from_data_base.username

                        user = authenticate(request, username=username, password=old_password)
                        if user:
                            user_from_data_base.set_password(new_password)
                            modifier = True

                        else:
                            response_data["etat"] = False
                            response_data["message"] = "Mot de passe incorrect"

                    password = form.get("password")
                    repassword = form.get("repassword")
                    if password and repassword:
                        if password == repassword:

                            # Validation du mot de passe
                            # validate_password(password, user_from_data_base)
                            user_from_data_base.set_password(password)
                            modifier = True
                            # user.save()

                        else:
                            response_data['message'] = "Les deux mots de passe ne correspondent pas"
                    else:
                        response_data['message'] = "Les champs de mot de passe sont requis"

                    if modifier:
                        user_from_data_base.save()
                        response_data["etat"] = True
                        response_data["message"] = "success"
                    else:
                        ...
                    # TODO requette invalide

                else:
                    # L'utilisateur n'a pas la permission d'ajouter une catégorie
                    response_data["message"] = "Utilisateur non trouvé. ???"
            else:
                # L'utilisateur n'a pas la permission d'ajouter une catégorie
                response_data["message"] = "Vous n'avez pas la permission."
        else:
            response_data["message"] = "Utilisateur non trouvé."

    else:
        response_data["etat"] = False
        response_data["message"] = "requette invalide"

    return JsonResponse(response_data)


@csrf_exempt
@token_required
def del_user(request):
    response_data = {'message': "requette invalide", 'etat': False}

    if request.method == "POST":
        form = dict()
        try:
            form = json.loads(request.body.decode("utf-8"))
        except:
            return JsonResponse({'message': "Erreur lors de le lecture des donnees JSON", 'etat': False})

        print(form)

        id = form.get("uuid")
        slug = form.get("slug")
        user_id = form.get("user_id")
        user = Utilisateur.objects.filter(uuid=user_id).first()

        if user:
            if user.groups.filter(name="Admin").exists():
                # if user.has_perm('boutique.delete_boutique'):
                if id:
                    boutique_from_database = Utilisateur.objects.all().filter(uuid=id).first()
                else:
                    boutique_from_database = Utilisateur.objects.all().filter(slug=slug).first()

                if not boutique_from_database:
                    response_data["message"] = "utilisateur non trouvé"
                else:

                    boutique_from_database.delete()
                    response_data["etat"] = True
                    response_data["message"] = "success"
            else:
                # L'utilisateur n'a pas la permission d'ajouter une catégorie
                response_data["message"] = "Vous n'avez pas la permission de supprimer une boutique."
        else:
            response_data["message"] = "Utilisateur non trouvé."
    return JsonResponse(response_data)


@csrf_exempt
def api_update_password(request):
    response_data = {'etat': False, 'message': "Requête invalide"}

    if request.method == "POST":
        try:
            form = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            response_data['message'] = "Erreur lors de la lecture des données JSON"
            return JsonResponse(response_data)

        uuid = form.get("user_id")
        password = form.get("password")
        repassword = form.get("repassword")
        # Décoder l'UID
        try:
            # user_id = urlsafe_base64_decode(uid)
            # decode_uid = codecs.decode(user_id, "utf-8")
            user = Utilisateur.objects.get(uuid=uuid)
        except (Utilisateur.DoesNotExist, ValueError):
            response_data['message'] = "Utilisateur introuvable ou UID invalide"
            return JsonResponse(response_data, status=403)

        # Vérifier la validité du token
        # if not default_token_generator.check_token(user, token):
        #     response_data['message'] = "Token invalide ou expiré"
        #     return JsonResponse(response_data, status=403)

        # Vérification des mots de passe

        if password and repassword:
            if password == repassword:
                try:
                    # Validation du mot de passe
                    validate_password(password, user)
                    user.set_password(password)
                    user.save()

                    response_data['etat'] = True
                    response_data['message'] = "Votre mot de passe a été modifié avec succès"
                except ValidationError as e:
                    response_data['message'] = str(e)
            else:
                response_data['message'] = "Les deux mots de passe ne correspondent pas"
        else:
            response_data['message'] = "Les champs de mot de passe sont requis"

    return JsonResponse(response_data)


@csrf_exempt
@token_required
def api_user_all(request, uuid):
    try:
        # Récupérer l'utilisateur avec l'ID donné
        utilisateur = Utilisateur.objects.filter(uuid=uuid).first()

        if utilisateur and utilisateur.is_superuser:
            # Filtrer les utilisateurs sans `created_by`
            all_use = Utilisateur.objects.filter(created_by__isnull=True)

            utilisateurs_data = [
                {
                    "avatar": user.avatar.url if user.avatar else None,
                    "role": user.role,
                    "id": user.id,
                    "uuid": user.uuid,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "is_admin": user.is_admin,
                    "is_superuser": user.is_superuser,
                    "numero": user.numero,
                }
                for user in all_use
            ]

            response_data = {
                "etat": True,
                "message": "Utilisateurs récupérés avec succès",
                "donnee": utilisateurs_data
            }
        else:
            response_data = {
                "etat": False,
                "message": "Utilisateur non trouvé ou non autorisé"
            }
    except Utilisateur.DoesNotExist:
        response_data = {
            "etat": False,
            "message": "Utilisateur non trouvé"
        }

    return JsonResponse(response_data)


# @csrf_exempt
# @token_required
# def api_user_get(request):
#     response_data = {'message': "requête invalide", 'etat': False}
#
#     if request.method == "POST":
#         try:
#             form = json.loads(request.body.decode("utf-8"))
#         except json.JSONDecodeError:
#             return JsonResponse(response_data)
#
#         filter_applied = False
#         all_utilisateur = list()
#         all_user = Utilisateur.objects.all()
#
#         user_id = form.get("user_id")
#         user = Utilisateur.objects.filter(uuid=user_id).first()
#
#         # Récupérer l'utilisateur connecté
#         current_user = request.user
#
#         # Filtrer uniquement les utilisateurs créés par l'administrateur connecté
#         if current_user.groups.filter(name="Admin").exists():
#         # if current_user.is_superuser:
#             all_use = all_user.filter(created_by=current_user)
#             if all_use:
#                 all_user = all_use
#             else:
#                 all_user = Utilisateur.objects.filter(uuid=user_id)
#
#         if user:
#             # if user.has_perm('entreprise.view_utilisateur'):
#             if user.groups.filter(name="Admin").exists():
#                 if "all" in form:
#                     all_utilisateur = all_user
#                     filter_applied = True
#
#                 elif "id" in form:
#                     id = form.get("id")
#                     all_utilisateur = all_user.filter(id=id)
#                     filter_applied = True
#
#                 elif "role" in form:
#                     role = form.get("role")
#                     all_utilisateur = all_user.filter(role=role)
#                     filter_applied = True
#
#                 if filter_applied:
#                     utilisateurs = list()
#                     for c in all_utilisateur:
#                         utilisateurs.append(
#                             {
#                                 "avatar": c.avatar.url if user.avatar else None,
#                                 "role": c.role,
#                                 "uuid": c.uuid,
#                                 "username": c.username,
#                                 "user_id": c.id,
#                                 "first_name": c.first_name,
#                                 "last_name": c.last_name,
#                                 "email": c.email,
#                                 "is_admin": user.is_admin,
#                                 "is_superuser": user.is_superuser,
#                                 "numero": c.numero,
#                             }
#                             # for user in all_utilisateur
#                         )
#
#                     if utilisateurs:
#                         response_data['etat'] = True
#                         response_data['message'] = "success"
#                         response_data['donnee'] = utilisateurs
#                     else:
#                         response_data["etat"] = False
#                         response_data["message"] = "vide"
#             else:
#                 response_data["message"] = "Vous n'avez pas la permission de voir les utilisateurs."
#         else:
#             response_data["message"] = "Utilisateur non trouvé."
#
#     return JsonResponse(response_data)

@csrf_exempt
@token_required
def api_user_get(request):
    response_data = {'message': "Requête invalide", 'etat': False}

    if request.method == "POST":
        try:
            form = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse(response_data)

        filter_applied = False
        all_utilisateur = list()
        all_user = Utilisateur.objects.all()

        user_id = form.get("user_id")
        entreprise_uuid = form.get("entreprise_id")
        user = Utilisateur.objects.filter(uuid=user_id).first()

        # Récupérer l'utilisateur connecté
        current_user = request.user

        # Filtrer uniquement les utilisateurs créés par l'administrateur connecté
        if current_user.groups.filter(name="Admin").exists():
            all_use = all_user.filter(created_by=current_user)
            if all_use:
                all_user = all_use
            else:
                all_user = Utilisateur.objects.filter(uuid=user_id)

        if user:
            # Vérifier les permissions de l'utilisateur
            if user.groups.filter(name="Admin").exists():
                if entreprise_uuid:
                    # Filtrer les utilisateurs par entreprise
                    entreprise = Entreprise.objects.filter(uuid=entreprise_uuid).first()
                    if entreprise:
                        all_utilisateur = all_user.filter(entreprises=entreprise)
                        filter_applied = True
                    else:
                        response_data["message"] = "Entreprise non trouvée."
                        return JsonResponse(response_data)

                elif "id" in form:
                    id = form.get("id")
                    all_utilisateur = all_user.filter(id=id)
                    filter_applied = True

                elif "role" in form:
                    role = form.get("role")
                    all_utilisateur = all_user.filter(role=role)
                    filter_applied = True

                if filter_applied:
                    utilisateurs = list()
                    for c in all_utilisateur:
                        utilisateurs.append(
                            {
                                "avatar": c.avatar.url if c.avatar else None,
                                "role": c.role,
                                "uuid": c.uuid,
                                "username": c.username,
                                "user_id": c.id,
                                "first_name": c.first_name,
                                "last_name": c.last_name,
                                "email": c.email,
                                "is_admin": c.is_admin,
                                "is_superuser": c.is_superuser,
                                "numero": c.numero,
                            }
                        )

                    if utilisateurs:
                        response_data['etat'] = True
                        response_data['message'] = "Succès"
                        response_data['donnee'] = utilisateurs
                    else:
                        response_data["etat"] = False
                        response_data["message"] = "Aucun utilisateur trouvé."
            else:
                response_data["message"] = "Vous n'avez pas la permission de voir les utilisateurs."
        else:
            response_data["message"] = "Utilisateur non trouvé."

    return JsonResponse(response_data)


@csrf_exempt
@token_required
def api_user_get_profil(request, uuid):
    message = "requette invalide"
    donnee = dict()
    etat = False

    user_form_data_base = Utilisateur.objects.all().filter(uuid=uuid).first()

    if user_form_data_base:

        donnee["first_name"] = user_form_data_base.first_name
        donnee["uuid"] = user_form_data_base.uuid
        donnee["email"] = user_form_data_base.email
        donnee["email_user"] = user_form_data_base.email_user
        donnee["role"] = user_form_data_base.role
        donnee["numero"] = user_form_data_base.numero
        donnee["pays"] = user_form_data_base.pays
        donnee["last_name"] = user_form_data_base.last_name
        donnee["username"] = user_form_data_base.username
        donnee["is_admin"] = user_form_data_base.is_admin
        donnee["is_superuser"] = user_form_data_base.is_superuser

        if user_form_data_base.avatar:
            donnee["avatar"] = user_form_data_base.avatar.url
        else:
            donnee["avatar"] = None

        donnee["role"] = user_form_data_base.role
        donnee["numero"] = user_form_data_base.numero

        donnee["email"] = user_form_data_base.email

        etat = True
        message = "success"
    else:
        message = "utilisateur non trouvé"

    response_data = {'message': message, 'etat': etat, "donnee": donnee}
    return JsonResponse(response_data)


@csrf_exempt
def api_forgot_password(request):
    response_data = {'message': "requête invalide", 'etat': False}

    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            response_data['message'] = "Erreur dans le format des données"
            return JsonResponse(response_data)

        email = data.get("email")
        # frontend_domain = data.get("frontend_domain")  # Recevoir le domaine du frontend

        if not email:
            response_data['message'] = "L'e-mail est requis"
            return JsonResponse(response_data)

        # if not frontend_domain:
        #     response_data['message'] = "Le domaine du frontend est requis"
        #     return JsonResponse(response_data)

        # Rechercher l'utilisateur par e-mail
        user = Utilisateur.objects.filter(email=email).first()

        if user:
            # Générer le token et uid
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.id))

            # Récupérer le domaine courant
            current_site = request.META.get("HTTP_HOST", "localhost")
            context = {
                "token": token,
                "uid": uid,
                "domaine": f"http://{current_site}"
                # "domaine": f"http://{frontend_domain}"  # Utiliser le domaine du frontend
            }
            # send_mail(
            #     'Contcat Form',
            #     token,
            #     'settings.EMAIL_HOST_USER',
            #     [user.email]
            # )
            # Charger le template de l'e-mail

            html_text = render_to_string("email.html", context)
            try:
                msg = EmailMessage(
                    "Réinitialisation de mot de passe",
                    html_text,
                    "DiakiteDigital <cheicknadiakite99@gmail.com>",
                    [user.email],
                )

                msg.content_subtype = "html"
                msg.send()
                response_data['message'] = "E-mail de réinitialisation envoyé"
                response_data['etat'] = True
            except Exception as e:
                response_data['message'] = f"Erreur lors de l'envoi de l'e-mail: {str(e)}"
        else:
            response_data['message'] = "Utilisateur non trouvé"

    return JsonResponse(response_data)


# def update_password(request, token, uid):
#     try:
#         user_id = urlsafe_base64_decode(uid)
#         decode_uid = codecs.decode(user_id, "utf-8")
#         user = Utilisateur.objects.get(id=decode_uid)
#     except:
#         return HttpResponseForbidden(
#             "Vous n'aviez pas la permission de modifier ce mot de pass. Utilisateur introuvable"
#         )
#
#     check_token = default_token_generator.check_token(user, token)
#     if not check_token:
#         return HttpResponseForbidden(
#             "Vous n'aviez pas la permission de modifier ce mot de pass. Votre Token est invalid ou a espiré"
#         )
#
#     error = False
#     success = False
#     message = ""
#     if request.method == "POST":
#         password = request.POST.get("password")
#         repassword = request.POST.get("repassword")
#
#         if repassword == password:
#             try:
#                 validate_password(password, user)
#                 user.set_password(password)
#                 user.save()
#
#                 success = True
#                 message = "votre mot de pass a été modifié avec succès!"
#             except ValidationError as e:
#                 error = True
#                 message = str(e)
#         else:
#             error = True
#             message = "Les deux mot de pass ne correspondent pas"
#
#     context = {"error": error, "success": success, "message": message}
#
#     return render(request, "update_password.html", context)

def update_password(request, token, uid):
    try:
        user_id = urlsafe_base64_decode(uid)
        decode_uid = user_id.decode("utf-8")  # Convertir le byte en string
        user = Utilisateur.objects.get(id=decode_uid)
    except:
        return HttpResponseForbidden(
            "Vous n'avez pas la permission de modifier ce mot de passe. Utilisateur introuvable."
        )

    check_token = default_token_generator.check_token(user, token)
    if not check_token:
        return HttpResponseForbidden(
            "Vous n'avez pas la permission de modifier ce mot de passe. Votre token est invalide ou a expiré."
        )

    error = False
    success = False
    message = ""

    if request.method == "POST":
        password = request.POST.get("password")
        repassword = request.POST.get("repassword")

        if repassword == password:
            if len(password) >= 6:  # Vérification de la longueur
                try:
                    user.set_password(password)
                    user.save()
                    success = True
                    message = "Votre mot de passe a été modifié avec succès !"
                except Exception as e:
                    error = True
                    message = f"Une erreur s'est produite : {str(e)}"
            else:
                error = True
                message = "Le mot de passe doit contenir au moins 6 caractères."
        else:
            error = True
            message = "Les deux mots de passe ne correspondent pas."

    context = {"error": error, "success": success, "message": message}

    return render(request, "update_password.html", context)


def deconnxion(request):
    logout(request)

    response_data = {'message': 'Vous ete deconnecter', 'etat': True}
    return JsonResponse(response_data)
