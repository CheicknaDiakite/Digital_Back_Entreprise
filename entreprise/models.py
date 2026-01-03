import datetime
import random
import string
import uuid
from io import BytesIO

import barcode
import qrcode
from PIL import ImageFont, ImageDraw, Image
from barcode.writer import ImageWriter
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import models
from django.db.models import Sum
from django.utils.text import slugify

from utilisateur.models import Utilisateur, Licence

from fonction import get_facture_upload_to, get_image_upload_to

from root.outil import MOYEN_PAIEMENT


# Create your models here.
class Entreprise(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    nom = models.CharField(max_length=100)
    adresse = models.TextField(blank=True, null=True)

    coordonne = models.TextField(blank=True, null=True)
    numero = models.CharField(max_length=20)
    pays = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    ref = models.CharField(max_length=150, unique=True, null=False, blank=False)
    libelle = models.TextField(blank=True, null=True)

    image = models.ImageField(null=True, blank=True, upload_to=get_facture_upload_to)

    utilisateurs = models.ManyToManyField(Utilisateur, related_name='entreprises', blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    # Ajout d'un champ Licence
    licence = models.OneToOneField(Licence, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.nom

    def assign_to_user(self, utilisateur):
        """Attribue cette entreprise à un utilisateur donné"""
        self.utilisateurs.add(utilisateur)

    def save(self, *args, **kwargs):
        if not self.ref:
            self.ref = self.generate_unique_code()
        super(Entreprise, self).save(*args, **kwargs)

    def generate_unique_code(self):
        date_str = datetime.datetime.now().strftime("%d%m%Y")
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"{date_str}{random_str}"

class Avi(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)

    libelle = models.CharField(max_length=200, null=True, blank=True)

    description = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return self.libelle


class PaiementEntreprise(models.Model):
    order_id = models.CharField(max_length=512, unique=True)
    payer = models.BooleanField(default=False)

    moyen_paiement = models.CharField(max_length=50, choices=MOYEN_PAIEMENT)

    date_soumission = models.DateTimeField(auto_now_add=True)
    date_validation = models.DateTimeField(null=True)

    montant = models.FloatField()
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE)
    client = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)

    numero = models.CharField(max_length=30, null=True)

    strip_link = models.URLField(null=True)


class Client(models.Model):
    CLIENT = 1
    FOURNISSEUR = 2
    AUTRE = 3

    choice = (
        (CLIENT, "Client"),
        (FOURNISSEUR, "Fournisseur"),
        (AUTRE, "Autre"),
    )

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    nom = models.CharField(max_length=500)
    adresse = models.TextField(blank=True, null=True)
    coordonne = models.TextField(blank=True, null=True)
    numero = models.CharField(max_length=20, blank=True, null=True)
    libelle = models.CharField(max_length=500, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    role = models.PositiveSmallIntegerField(choices=choice, null=True, blank=True)

    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return self.nom


class Categorie(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE)

    libelle = models.CharField(max_length=500, null=False, blank=False)
    image = models.ImageField(null=True, blank=True, upload_to=get_image_upload_to)
    slug = models.SlugField(editable=False, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return self.libelle

    @property
    def sous_categorie(self):
        return self.souscategorie_set.all()

    def _get_unique_slug(self):
        slug = slugify(self.libelle)
        unique_slug = slug
        num = 1
        while Categorie.objects.filter(slug=unique_slug).exists():
            unique_slug = "{}-{}".format(slug, num)
            num += 1
        return unique_slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._get_unique_slug()
        super().save()


class SousCategorie(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    categorie = models.ForeignKey(Categorie, on_delete=models.CASCADE)

    libelle = models.CharField(max_length=200)
    image = models.ImageField(null=True, blank=True, upload_to=get_image_upload_to)
    slug = models.SlugField()

    created_at = models.DateTimeField(auto_now_add=True, null=True)

    @property
    def all_entrer(self):
        return self.entrer_set.all()

    def _get_unique_slug(self):
        slug = slugify(self.libelle)
        unique_slug = slug
        num = 1
        while SousCategorie.objects.filter(slug=unique_slug).exists():
            unique_slug = "{}-{}".format(slug, num)
            num += 1
        return unique_slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._get_unique_slug()
        super().save()


class Commande(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    souscategorie = models.ForeignKey(SousCategorie, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)

    libelle = models.CharField(max_length=200, null=True, blank=True)
    qte = models.IntegerField(default=0)
    pu = models.IntegerField(default=0)

    date = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True)

    @property
    def all_entrer(self):
        return self.entrer_set.all()


class Depense(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE)

    ref = models.CharField(max_length=150, unique=True, null=False, blank=False)

    libelle = models.CharField(max_length=200, null=True, blank=True)
    # somme = models.IntegerField(default=0)
    somme = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    facture = models.FileField(null=True, blank=True, upload_to=get_facture_upload_to)

    slug = models.SlugField(editable=False, blank=True)
    date = models.DateTimeField(null=True, blank=True)
    # date = models.DateTimeField(auto_now_add=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return self.libelle

    def _get_unique_slug(self):
        slug = slugify(self.libelle)
        unique_slug = slug
        num = 1
        while Depense.objects.filter(slug=unique_slug).exists():
            unique_slug = "{}-{}".format(slug, num)
            num += 1
        return unique_slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._get_unique_slug()
        super().save()

        if not self.ref:
            self.ref = self.generate_unique_code()
        super(Depense, self).save(*args, **kwargs)

    def generate_unique_code(self):
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"{date_str}{random_str}"


class Entrer(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    souscategorie = models.ForeignKey(SousCategorie, on_delete=models.CASCADE)
    ref = models.CharField(max_length=150, unique=True, null=False, blank=False)
    libelle = models.CharField(max_length=200, null=False)
    qte = models.IntegerField(default=0)
    qte_critique = models.IntegerField(default=0, null=False, blank=False)
    pu = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    pu_achat = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=False, blank=False)
    # Champ booléen pour déterminer si on doit cumuler ou non la quantité
    cumuler_quantite = models.BooleanField(default=False)
    is_sortie = models.BooleanField(default=True, null=False, blank=False)
    is_prix = models.BooleanField(default=True, null=False, blank=False)

    slug = models.SlugField(editable=False, blank=True)

    date = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)

    barcode = models.ImageField(null=True, blank=True, upload_to=get_image_upload_to)
    country_id = models.CharField(max_length=1, null=True)
    manufacturer_id = models.CharField(max_length=6, null=True)
    number_id = models.CharField(max_length=5, null=True)

    def __str__(self):
        return self.ref

    @property
    def all_sortie(self):
        return self.sortie_set.all()

    @property
    def prix_total(self):
        return self.pu_achat * self.qte

    def _get_unique_slug(self):
        slug = slugify(self.pu)
        unique_slug = slug
        num = 1
        while Entrer.objects.filter(slug=unique_slug).exists():
            unique_slug = "{}-{}".format(slug, num)
            num += 1
        return unique_slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._get_unique_slug()
        super().save(*args, **kwargs)

    def generate_unique_code(self):
        date_str = datetime.datetime.now().strftime("%m%d")
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"{date_str}{random_str}"


class HistoriqueEntrer(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    entrer = models.ForeignKey(Entrer, on_delete=models.SET_NULL, null=True, blank=True)
    ref = models.CharField(max_length=150)
    qte = models.IntegerField()

    ancien_qte = models.IntegerField(null=True, blank=True)
    cumuler_qe = models.BooleanField(default=False, null=True, blank=True)

    description = models.TextField(blank=True, null=True)

    pu = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    reference = models.CharField(max_length=150, unique=True, null=False, blank=False)
    date = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    action = models.CharField(max_length=50)  # "created", "updated", "deleted"
    libelle = models.CharField(max_length=150, null=True, blank=True)  # "created", "updated", "deleted"
    categorie = models.CharField(max_length=150, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True, blank=True)
    entreprise = models.ForeignKey(Entreprise, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Historique de {self.ref} - {self.action}"

    def save(self, *args, **kwargs):
        # Assurez-vous que `reference` est unique
        if not self.reference:
            self.reference = self.generate_unique_code()

            # Vérifiez l'unicité dans la base de données
            while HistoriqueEntrer.objects.filter(reference=self.reference).exists():
                self.reference = self.generate_unique_code()

        # Sauvegarde initiale
        super(HistoriqueEntrer, self).save(*args, **kwargs)

    def generate_unique_code(self):
        date_str = datetime.datetime.now().strftime("%d%m%Y%H%M%S%f")  # Inclut les microsecondes
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"{date_str}{random_str}"


class Sortie(models.Model):
    created_by = models.ForeignKey(
        Utilisateur,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sorties_creees'
    )
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    entrer = models.ForeignKey(Entrer, on_delete=models.CASCADE)

    ref = models.CharField(max_length=150, unique=True, null=False, blank=False)

    qte = models.IntegerField(default=0)
    pu = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    is_remise = models.BooleanField(default=False, null=False, blank=False)
    remise_code = models.CharField(max_length=50, null=True, blank=True)

    slug = models.SlugField(editable=False, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.ref

    @property
    def prix_total(self):
        return self.pu * self.qte

    @property
    def somme_total(self):
        return Sortie.objects.all().aggregate(total_qte=Sum('qte'))['total_qte']

    @property
    def prix_stock(self):
        return int(self.entrer.qte) - int(self.qte)

    def _get_unique_slug(self):
        slug = slugify(self.entrer)
        unique_slug = slug
        num = 1
        while Sortie.objects.filter(slug=unique_slug).exists():
            unique_slug = "{}-{}".format(slug, num)
            num += 1
        return unique_slug

    def save(self, *args, **kwargs):
        # Vérifier stock
        if self.entrer.qte - int(self.qte) < 0:
            raise ValidationError("Impossible : quantité demandée indisponible.")

        # Générer slug si besoin
        if not self.slug:
            self.slug = self._get_unique_slug()

        # Générer ref si besoin
        if not self.ref:
            self.ref = self.generate_unique_code()

        super().save(*args, **kwargs)
    
    def generate_unique_code(self):
        date_str = datetime.datetime.now().strftime("%m%d")
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"{date_str}{random_str}"


class HistoriqueSortie(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    sortie = models.ForeignKey(Sortie, on_delete=models.SET_NULL, null=True, blank=True)
    ref = models.CharField(max_length=150)
    qte = models.IntegerField()
    pu = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    action = models.CharField(max_length=50)  # "created", "updated", "deleted"
    libelle = models.CharField(max_length=150, null=True, blank=True)
    categorie = models.CharField(max_length=150, null=True, blank=True)

    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True, blank=True)
    entreprise = models.ForeignKey(Entreprise, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Historique de {self.sortie.ref} - {self.action}"

    def save(self, *args, user=None, **kwargs):
        # Générer une référence unique s'il n'y en a pas
        if not self.ref:
            self.ref = self.generate_unique_code()

        # Sauvegarde initiale du stock
        super(HistoriqueSortie, self).save(*args, **kwargs)

    def generate_unique_code(self):
        date_str = datetime.datetime.now().strftime("%d%m%Y")
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"{date_str}{random_str}"


class FactEntre(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE)

    libelle = models.CharField(max_length=200)
    ref = models.CharField(max_length=200)
    facture = models.FileField(null=True, blank=True, upload_to=get_facture_upload_to)

    slug = models.SlugField()

    date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def _get_unique_slug(self):
        slug = slugify(self.libelle)
        unique_slug = slug
        num = 1
        while FactEntre.objects.filter(slug=unique_slug).exists():
            unique_slug = "{}-{}".format(slug, num)
            num += 1
        return unique_slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._get_unique_slug()
        super().save()


class FactSortie(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE)

    libelle = models.CharField(max_length=200)
    ref = models.CharField(max_length=200)
    facture = models.FileField(null=True, blank=True, upload_to=get_facture_upload_to)

    slug = models.SlugField()

    date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def _get_unique_slug(self):
        slug = slugify(self.libelle)
        unique_slug = slug
        num = 1
        while FactSortie.objects.filter(slug=unique_slug).exists():
            unique_slug = "{}-{}".format(slug, num)
            num += 1
        return unique_slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._get_unique_slug()
        super().save()

    # def save(self, *args, **kwargs):
    #     self.slug = slugify(self.title)
    #     super(GeeksModel, self).save(*args, **kwargs)
