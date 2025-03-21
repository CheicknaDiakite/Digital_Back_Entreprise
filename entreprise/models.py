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


class Avis(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)

    libelle = models.CharField(max_length=200, null=True, blank=True)

    description = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return self.libelle


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
    pu = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    pu_achat = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=False, blank=False)
    # Champ booléen pour déterminer si on doit cumuler ou non la quantité
    cumuler_quantite = models.BooleanField(default=False)
    is_sortie = models.BooleanField(default=True, null=False, blank=False)

    slug = models.SlugField(editable=False, blank=True)

    date = models.DateTimeField(null=True, blank=True)
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
        return self.pu * self.qte

    def _get_unique_slug(self):
        slug = slugify(self.pu)
        unique_slug = slug
        num = 1
        while Entrer.objects.filter(slug=unique_slug).exists():
            unique_slug = "{}-{}".format(slug, num)
            num += 1
        return unique_slug

    def save(self, *args, user=None, **kwargs):
        # Générer un slug unique s'il n'existe pas
        # code_str = ''.join(random.choices(string.digits, k=12))
        # EAN = barcode.get_barcode_class('ean13')
        # ean = EAN(code_str, writer=ImageWriter())
        # buffer = BytesIO()
        # ean.write(buffer)
        # self.barcode.save('barcode.png', File(buffer), save=False)

        if not self.slug:
            self.slug = self._get_unique_slug()

        # Vérifie si un produit avec la même sous-catégorie existe déjà
        dernier_produit = Entrer.objects.filter(souscategorie=self.souscategorie).order_by('-created_at').first()

        # Si le booléen cumuler_quantite est vrai, on cumule les quantités
        if self.cumuler_quantite and dernier_produit:
            # Vérifie si le client est le même
            if dernier_produit.client != self.client:
                dernier_produit.client = None  # Réinitialise le client à null si différent

            dernier_produit.qte += int(self.qte)  # Cumule la quantité
            dernier_produit.pu = int(self.pu)
            dernier_produit.date = self.date
            dernier_produit.ref = self.ref
            # Sauvegarde la mise à jour du produit existant
            dernier_produit.save()

            HistoriqueEntrer.objects.create(
                entrer=dernier_produit,
                ref=self.ref,
                libelle=f"Produit modifié par {user.first_name} {user.last_name}" if user else "Produit modifié",
                categorie=self.souscategorie.libelle,
                qte=self.qte,
                pu=self.pu,
                date=self.date,
                action="updated",
                reference=self.generate_unique_code()  # Ajoutez une référence unique ici
            )

            # Retourner ici pour éviter de créer un nouvel enregistrement d'inventaire
            return

        # Si cumuler_quantite est faux ou aucun produit existant, on sauvegarde normalement
        if not self.ref:
            self.ref = self.generate_unique_code()

        # Sauvegarde d'abord l'inventaire (crée ou met à jour l'enregistrement)
        super(Entrer, self).save(*args, **kwargs)

        # Ne crée un historique que si cumuler_quantite est false (ou si aucun produit n'a été trouvé)
        if not self.cumuler_quantite:
            if user:

                # ref = str(self.ref)
                # BarcodeClass = barcode.get_barcode_class('code128')  # Code128 supporte les caractères alphanumériques
                # barcode_instance = BarcodeClass(ref, writer=ImageWriter())
                # buffer = BytesIO()
                # barcode_instance.write(buffer)
                # # Utiliser l'UUID dans le nom du fichier pour éviter les conflits
                # self.barcode.save(f'{ref}.png', File(buffer), save=True)

                # Génération du QR code
                ref = str(self.ref)
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(ref)
                qr.make(fit=True)
                img_qr = qr.make_image(fill_color="black", back_color="white").convert("RGB")

                # Définition du texte et de la police
                font_size = 20
                try:
                    # Utilise une police TrueType si disponible (adaptez le chemin si nécessaire)
                    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)
                except IOError:
                    font = ImageFont.load_default()

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
                self.barcode.save(f'{ref}.png', File(buffer), save=True)

            HistoriqueEntrer.objects.create(
                entrer=self,
                ref=self.ref,
                libelle=f"Produit ajouté par {user.first_name} {user.last_name}" if user else "Produit Mis a jour",
                categorie=f"{self.souscategorie.libelle} ({self.libelle})",
                qte=self.qte,
                pu=self.pu,
                date=self.date,
                action="created"  # Ajuste l'action en fonction de l'état initial
            )

    def generate_unique_code(self):
        date_str = datetime.datetime.now().strftime("%m%d")
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"{date_str}{random_str}"


class HistoriqueEntrer(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    entrer = models.ForeignKey(Entrer, on_delete=models.SET_NULL, null=True, blank=True)
    ref = models.CharField(max_length=150)
    qte = models.IntegerField()
    pu = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    reference = models.CharField(max_length=150, unique=True, null=False, blank=False)
    date = models.DateTimeField(null=True, blank=True)
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
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    entrer = models.ForeignKey(Entrer, on_delete=models.CASCADE)

    ref = models.CharField(max_length=150, unique=True, null=False, blank=False)

    qte = models.IntegerField(default=0)
    pu = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    is_remise = models.BooleanField(default=False, null=False, blank=False)

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

    def save(self, *args, user=None, **kwargs):
        # Si la quantité de l'inventaire après soustraction est 0 ou moins, lever une erreur
        if self.prix_stock < 0:
            raise ValidationError(
                "Impossible de faire la sortie : la quantité est demander n'est pas disponible !"
            )

        # Générer un slug unique s'il n'existe pas
        if not self.slug:
            self.slug = self._get_unique_slug()

        # Générer une référence unique s'il n'y en a pas
        if not self.ref:
            self.ref = self.generate_unique_code()

        # Sauvegarde initiale du stock
        super(Sortie, self).save(*args, **kwargs)

        # Mise à jour correcte de la quantité de l'inventaire après l'ajout du stock
        self.entrer.qte -= int(self.qte)
        self.entrer.save()

        # Crée un historique après la mise à jour du stock
        HistoriqueSortie.objects.create(
            sortie=self,
            ref=self.ref,
            # libelle=self.entrer.libelle,
            libelle=f"Produit sortie par {user.first_name} {user.last_name}" if user else "Produit sortie",
            # categorie=self.entrer.souscategorie.libelle,
            categorie=f"{self.entrer.souscategorie.libelle} ({self.entrer.libelle})",
            qte=self.qte,
            pu=self.pu,
            action="created"
            # Vérifie si c'est un nouvel enregistrement ou une mise à jour
        )

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
