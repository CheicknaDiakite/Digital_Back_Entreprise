from django.db.models import Sum, F, Count
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from rest_framework import generics, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework import serializers
from rest_framework.views import APIView

from utilisateur.models import Utilisateur
from .models import Categorie, Entreprise, Sortie, Entrer, SousCategorie, Depense, Client
from .serializers import CategorieSerializer, EntrepriseDetailSerializer, DepenseSerializer, SortieEntrepriseSerializer, \
    ClientSerializer


class CategorieListCreateView(generics.ListCreateAPIView):
    queryset = Categorie.objects.all()
    serializer_class = CategorieSerializer
    permission_classes = [permissions.IsAuthenticated]  # JWT obligatoire

    def perform_create(self, serializer):
        user = self.request.user  # récupéré via JWT
        entreprise_uuid = self.request.data.get("entreprise_uuid")

        # Vérifier que l'entreprise existe
        try:
            entreprise = Entreprise.objects.get(uuid=entreprise_uuid)
        except Entreprise.DoesNotExist:
            raise serializers.ValidationError({"entreprise_uuid": "Entreprise introuvable."})

        # Vérifier que l'utilisateur est Admin ou Editor
        if not (user.groups.filter(name="Admin").exists() or user.groups.filter(name="Editor").exists()):
            raise serializers.ValidationError({"permission": "Vous n'avez pas la permission d'ajouter une catégorie."})

        # Sauvegarde de la catégorie
        serializer.save(entreprise=entreprise)

    def create(self, request, *args, **kwargs):
        """
        Personnalisation de la réponse pour garder ton format {etat, message, id, slug}
        """
        try:
            response = super().create(request, *args, **kwargs)
            data = response.data
            return Response({
                "etat": True,
                "id": data.get("uuid"),
                "slug": data.get("slug", ""),
                "message": "success"
            }, status=status.HTTP_201_CREATED)
        except serializers.ValidationError as e:
            return Response({
                "etat": False,
                "message": e.detail
            }, status=status.HTTP_400_BAD_REQUEST)


class UtilisateurEntreprisesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        utilisateur = request.user  # L'utilisateur connecté via JWT

        entreprises_data = []
        for entreprise in utilisateur.entreprises.all():
            if entreprise.licence:
                licence_data = {
                    "licence_active": entreprise.licence.active,
                    "licence_type": entreprise.licence.get_type_display(),
                    "licence_code": entreprise.licence.code,
                    "licence_date_expiration": entreprise.licence.date_expiration,
                }
            else:
                licence_data = {
                    "licence_active": None,
                    "licence_type": None,
                    "licence_code": None,
                    "licence_date_expiration": None,
                }

            entreprises_data.append({
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
                **licence_data
            })

        return Response({
            "etat": True,
            "message": "Entreprises récupérées avec succès",
            "donnee": entreprises_data
        })


class EntrepriseCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # JWT ou autre auth

    def post(self, request):
        serializer = EntrepriseDetailSerializer(data=request.data)
        if serializer.is_valid():
            try:
                entreprise = serializer.save()
                return Response({
                    "etat": True,
                    "message": "Entreprise créée avec succès",
                    "donnee": {
                        "id": entreprise.id,
                        "uuid": entreprise.uuid,
                        "nom": entreprise.nom
                    }
                }, status=status.HTTP_201_CREATED)
            except serializers.ValidationError as e:
                return Response({
                    "etat": False,
                    "message": e.detail
                }, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            "etat": False,
            "message": "Erreur de validation",
            "erreurs": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class EntrepriseDetailView(APIView):

    def get(self, request, uuid):

        entreprise = Entreprise.objects.filter(uuid=uuid).first()

        if not entreprise:
            return Response({
                "etat": False,
                "message": "Entreprise non trouvée"
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = EntrepriseDetailSerializer(entreprise)
        return Response({
            "etat": True,
            "message": "success",
            "donnee": serializer.data
        }, status=status.HTTP_200_OK)


class EntresEntrepriseAPIView(APIView):

    def get(self, request, entreprise_id):
        try:
            # Vérifier si l'entreprise existe
            utilisateur = request.user
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
                        "unite": entrer.unite,
                        "pu_achat": entrer.pu_achat,
                        "ref": entrer.ref,
                        "client": entrer.client.nom if entrer.client else None,
                        "qte": entrer.qte,
                        "qte_critique": entrer.qte_critique,
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

        return Response(response_data)


class SortiesEntrepriseAPIView(APIView):
    """
    Récupère toutes les sorties liées à une entreprise donnée via son UUID.
    """
    def get(self, request, uuid):
        try:
            # Vérifier si l'entreprise existe
            entreprise = get_object_or_404(Entreprise, uuid=uuid)

            # Récupérer toutes les sous-catégories associées
            souscategories = SousCategorie.objects.filter(categorie__entreprise=entreprise)

            # Récupérer toutes les entrées liées à ces sous-catégories
            entrers = Entrer.objects.filter(souscategorie__in=souscategories)

            # Récupérer toutes les sorties liées à ces entrées
            sorties = Sortie.objects.filter(entrer__in=entrers)

            # Filtrage optionnel sur is_remise
            is_remise_param = request.query_params.get('is_remise')
            if is_remise_param is not None:
                # Convertir la chaîne en booléen (ex: "true" -> True, "false" -> False)
                is_remise = is_remise_param.lower() in ['true', '1', 'yes']
                sorties = sorties.filter(is_remise=is_remise)

            # Préparer la réponse
            sorties_data = [
                {
                    "id": sortie.id,
                    "uuid": sortie.uuid,
                    "slug": sortie.slug,
                    "pu": sortie.pu,
                    "unite": sortie.unite,
                    "ref": sortie.ref,
                    "qte": sortie.qte,
                    "is_remise": sortie.is_remise,
                    "remise_code": sortie.remise_code,
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

            return Response({
                "etat": True,
                "message": "Sorties récupérées avec succès",
                "donnee": sorties_data
            }, status=status.HTTP_200_OK)

        except Entreprise.DoesNotExist:
            return Response({
                "etat": False,
                "message": "Entreprise non trouvée"
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({
                "etat": False,
                "message": f"Erreur interne : {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SommeQtePuSortieView(APIView):

    def get(self, request, entreprise_id):
        try:
            utilisateur = request.user

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

            # ➤ Totaux groupés par mois (Entrées)
            details_entrer_par_mois = {}
            for item in entrers.annotate(month=TruncMonth('created_at')).values('month').annotate(
                somme_qte=Sum('qte'),
                somme_prix_total=Sum(F('qte') * F('pu_achat')),
            ).order_by('month'):
                mois = item['month'].strftime("%B %Y")
                details_entrer_par_mois[mois] = {
                    "somme_qte": item['somme_qte'],
                    "somme_prix_total": item['somme_prix_total'],
                }

            # ➤ Totaux groupés par mois (Sorties)
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

            # Comptages par mois
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

            return Response({
                "etat": True,
                "message": "Quantité, prix et détails agrégés par mois récupérés avec succès",
                "donnee": data
            }, status=status.HTTP_200_OK)

        except Utilisateur.DoesNotExist:
            return Response({"etat": False, "message": "Utilisateur non trouvé"}, status=status.HTTP_404_NOT_FOUND)
        except Entreprise.DoesNotExist:
            return Response({"etat": False, "message": "Entreprise non trouvée pour cet utilisateur"}, status=status.HTTP_404_NOT_FOUND)


from collections import defaultdict
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

class CountSortieParUtilisateurView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # Active l’authentification

    def get(self, request, entreprise_id):
        # Vérifier que l’entreprise existe
        try:
            entreprise = Entreprise.objects.get(uuid=entreprise_id)
        except Entreprise.DoesNotExist:
            return Response(
                {'etat': False, 'message': "Entreprise non trouvée"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Récupérer l'éventuel paramètre de filtrage par utilisateur et par date
        user_uuid = request.query_params.get('user_uuid')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        # QuerySet des sorties de l’entreprise
        qs = Sortie.objects.filter(
            entrer__souscategorie__categorie__entreprise=entreprise
        ).select_related('created_by', 'entrer__souscategorie')

        if user_uuid:
            qs = qs.filter(created_by__uuid=user_uuid)

        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)

        # 1) Total des quantités et montants vendus par utilisateur
        total_qte_par_user = (
            qs.values('created_by__id', 'created_by__username', 'created_by__uuid')
            .annotate(
                total_qte=Sum('qte'),
                total_montant=Sum(F('qte') * F('pu'))
            )
            .order_by('-total_qte')
        )

        total_par_utilisateur = [
            {
                'user_id': rec['created_by__id'],
                'user_uuid': rec['created_by__uuid'],
                'username': rec['created_by__username'] or "Inconnu",
                'total_qte': rec['total_qte'] or 0,
                'total_montant': float(rec['total_montant']) if rec['total_montant'] else 0
            }
            for rec in total_qte_par_user
        ]

        # 2) Nombre total de ventes (sorties) par utilisateur
        total_nombre_vente = (
            qs.values('created_by__id', 'created_by__username', 'created_by__uuid')
            .annotate(total=Count('id'))
            .order_by('-total')
        )

        # 3) Quantités et montants vendus par utilisateur **par mois**
        qs_monthly = (
            qs.annotate(mois=TruncMonth('created_at'))
            .values('created_by__id', 'created_by__username', 'created_by__uuid', 'mois')
            .annotate(
                total_qte=Sum('qte'),
                total_montant=Sum(F('qte') * F('pu'))
            )
            .order_by('mois', 'created_by__username')
        )

        # Regrouper les données par mois
        mois_groupes = defaultdict(list)
        for rec in qs_monthly:
            mois_str = rec['mois'].strftime('%B %Y').capitalize()
            mois_groupes[mois_str].append({
                'user_id': rec['created_by__id'],
                'user_uuid': rec['created_by__uuid'],
                'username': rec['created_by__username'] or "Inconnu",
                'total_qte': rec['total_qte'] or 0,
                'total_montant': float(rec['total_montant']) if rec['total_montant'] else 0
            })

        resultats_par_mois = [
            {"month": mois, "details": details}
            for mois, details in mois_groupes.items()
        ]

        # 4) Détails des dernières ventes si un utilisateur est spécifique
        derniere_ventes = []
        if user_uuid:
            derniere_ventes = [
                {
                    'uuid': s.uuid,
                    'libelle': s.entrer.libelle,
                    'produit': s.entrer.souscategorie.categorie.libelle,
                    'qte': s.qte,
                    'pu': float(s.pu),
                    'total': float(s.qte * s.pu),
                    'date': s.created_at.strftime('%Y-%m-%d %H:%M')
                }
                for s in qs.order_by('-created_at')[:20]
            ]

        # Données finales
        data = {
            'total_par_utilisateur': total_par_utilisateur,
            'total_nombre_vente': [
                {
                    'user_id': rec['created_by__id'],
                    'user_uuid': rec['created_by__uuid'],
                    'username': rec['created_by__username'] or "Inconnu",
                    'total': rec['total']
                }
                for rec in total_nombre_vente
            ],
            'mensuel_par_utilisateur': resultats_par_mois,
            'derniere_ventes': derniere_ventes,
        }

        return Response({
            'etat': True,
            'message': "Somme des quantités et montants vendus par utilisateur",
            'donnee': data
        }, status=status.HTTP_200_OK)



class DepensesSommeParMoisView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # Authentification requise

    def get(self, request, entreprise_id):
        try:
            # Vérifier l'utilisateur

            # Vérifier l'entreprise
            entreprise = Entreprise.objects.filter(uuid=entreprise_id).first()
            if not entreprise:
                return Response({
                    "etat": False,
                    "message": "Entreprise non trouvée ou non associée à l'utilisateur"
                }, status=status.HTTP_404_NOT_FOUND)

            # Groupement des dépenses par mois avec somme des montants
            depenses_par_mois = (
                Depense.objects
                .filter(entreprise=entreprise)
                .annotate(mois=TruncMonth('date'))
                .values('mois')
                .annotate(total=Sum('somme'))
                .order_by('mois')
            )

            # Formatage des données
            depenses_data = [
                {
                    "mois": dep["mois"].strftime("%Y-%m"),
                    "total": float(dep["total"]) if dep["total"] else 0
                }
                for dep in depenses_par_mois
            ]

            return Response({
                "etat": True,
                "message": "Somme des dépenses par mois récupérée avec succès",
                "donnee": depenses_data
            }, status=status.HTTP_200_OK)

        except Utilisateur.DoesNotExist:
            return Response({
                "etat": False,
                "message": "Utilisateur non trouvé"
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({
                "etat": False,
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DepensesEntrepriseView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # Auth obligatoire

    def get(self, request, entreprise_id):
        try:
            # Vérification utilisateur
            utilisateur = request.user

            # Vérification entreprise associée à l'utilisateur
            entreprise = Entreprise.objects.filter(uuid=entreprise_id, utilisateurs=utilisateur).first()
            if not entreprise:
                return Response({
                    "etat": False,
                    "message": "Entreprise non trouvée ou non associée à l'utilisateur"
                }, status=status.HTTP_404_NOT_FOUND)

            # Récupération des dépenses de l'entreprise
            depenses = Depense.objects.filter(entreprise=entreprise)

            # Sérialisation
            serializer = DepenseSerializer(depenses, many=True)

            return Response({
                "etat": True,
                "message": "Dépenses récupérées avec succès",
                "donnee": serializer.data
            }, status=status.HTTP_200_OK)

        except Utilisateur.DoesNotExist:
            return Response({
                "etat": False,
                "message": "Utilisateur non trouvé"
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({
                "etat": False,
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SousCategoriesSortiesParMoisView(APIView):

    def get(self, request, entreprise_uuid):
        try:
            # Année demandée (optionnelle)
            annee = request.GET.get("annee")

            if annee:
                annee = int(annee)
            else:
                annee = now().year

            debut_annee = now().replace(year=annee, month=1, day=1)
            fin_annee = now().replace(year=annee, month=12, day=31, hour=23, minute=59, second=59)

            entreprise = Entreprise.objects.get(uuid=entreprise_uuid)

            sorties = Sortie.objects.filter(
                entrer__souscategorie__categorie__entreprise=entreprise,
                created_at__range=(debut_annee, fin_annee)
            ).select_related('entrer__souscategorie')

            sorties_par_mois = sorties.annotate(
                mois=TruncMonth('created_at')
            ).values(
                'mois',
                'entrer__souscategorie__libelle'
            ).annotate(
                somme_qte=Sum('qte')
            ).order_by('mois')

            resultats_par_mois = []
            mois_actuel = None
            details = []

            for sortie in sorties_par_mois:
                mois_format = sortie['mois'].strftime("%B %Y")

                if mois_actuel and mois_actuel != mois_format:
                    resultats_par_mois.append({
                        "month": mois_actuel,
                        "details": details
                    })
                    details = []

                details.append({
                    "libelle": sortie['entrer__souscategorie__libelle'],
                    "somme_qte": sortie['somme_qte']
                })

                mois_actuel = mois_format

            if mois_actuel:
                resultats_par_mois.append({
                    "month": mois_actuel,
                    "details": details
                })

            return Response({
                "etat": True,
                "message": "Données récupérées avec succès",
                "donnee": {
                    "annee": annee,
                    "sorties_par_mois": resultats_par_mois
                }
            }, status=status.HTTP_200_OK)

        except Entreprise.DoesNotExist:
            return Response(
                {"etat": False, "message": "Entreprise non trouvée"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"etat": False, "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ClientListAPIView(APIView):

    def get(self, request, uuid):
        # Récupération de l'entreprise ou erreur 404
        entreprise = get_object_or_404(Entreprise, uuid=uuid)

        # Récupérer les clients de l'entreprise
        clients = Client.objects.filter(entreprise=entreprise)

        # Sérialisation
        serializer = ClientSerializer(clients, many=True)

        return Response({
            "etat": True,
            "message": "Clients récupérés avec succès",
            "donnee": serializer.data
        }, status=status.HTTP_200_OK)