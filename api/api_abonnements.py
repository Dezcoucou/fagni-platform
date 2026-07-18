"""
API endpoints pour la gestion des abonnements par OPS.
POST /api/ops/abonnements - creer un abonnement pour un client existant
GET /api/ops/abonnements - lister les abonnements
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from accounts.jwt_utils import require_role
from dossiers.models import Dossier
from abonnements.models import Abonnement
from abonnements.services import creer_abonnement, generer_commande_depuis_abonnement, DossierNonUtilisable, PrixAbonnementNonConfigure


@api_view(['GET', 'POST'])
@require_role("administrateur", "superviseur")
def api_ops_abonnements(request):
    if request.method == 'GET':
        return _liste_abonnements(request)
    return _creer_abonnement(request)


def _creer_abonnement(request):
    """
    POST /api/ops/abonnements
    Payload attendu : {
        "telephone_client": "0748643892",
        "pack": "essentiel" | "confort",
        "taille_sac": "S" | "M",
        "jour_collecte": 0-6,
        "jour_livraison": 0-6,
        "date_debut": "2026-07-20" (optionnel)
    }
    Le client doit deja avoir un Dossier existant (cree via inscription
    normale) - jamais de creation automatique de Dossier depuis cet
    endpoint, pour eviter les doublons (lecon retenue de l'incident
    doublon partenaire "L&O" en V1).
    """
    telephone_client = request.data.get("telephone_client", "").strip()
    pack = request.data.get("pack", "").strip()
    taille_sac = request.data.get("taille_sac", "").strip()
    jour_collecte = request.data.get("jour_collecte")
    jour_livraison = request.data.get("jour_livraison")
    date_debut = request.data.get("date_debut")

    if not all([telephone_client, pack, taille_sac]) or jour_collecte is None or jour_livraison is None:
        return Response(
            {"error": "telephone_client, pack, taille_sac, jour_collecte, jour_livraison requis"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if pack not in dict(Abonnement.PACK_CHOICES):
        return Response({"error": f"pack invalide, attendu: {list(dict(Abonnement.PACK_CHOICES))}"}, status=status.HTTP_400_BAD_REQUEST)
    if taille_sac not in dict(Abonnement.TAILLE_SAC_CHOICES):
        return Response({"error": f"taille_sac invalide, attendu: {list(dict(Abonnement.TAILLE_SAC_CHOICES))}"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        dossier_client = Dossier.objects.get(type_acteur="client", telephone=telephone_client, statut="actif")
    except Dossier.DoesNotExist:
        return Response(
            {"error": f"Aucun client actif trouve pour le telephone '{telephone_client}'."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        abonnement = creer_abonnement(
            dossier_client, pack, taille_sac,
            jour_collecte=int(jour_collecte), jour_livraison=int(jour_livraison),
            date_debut=date_debut,
        )
    except DossierNonUtilisable as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "id": abonnement.id,
        "client": dossier_client.nom,
        "pack": abonnement.get_pack_display(),
        "taille_sac": abonnement.get_taille_sac_display(),
        "jour_collecte": abonnement.get_jour_collecte_display(),
        "jour_livraison": abonnement.get_jour_livraison_display(),
        "statut": abonnement.get_statut_display(),
    }, status=status.HTTP_201_CREATED)


def _liste_abonnements(request):
    """GET /api/ops/abonnements - liste des abonnements, plus recents d'abord."""
    abonnements = Abonnement.objects.select_related("dossier_client").all()[:50]

    return Response({
        "total": Abonnement.objects.count(),
        "actifs": Abonnement.objects.filter(statut="actif").count(),
        "abonnements": [
            {
                "id": a.id,
                "client": a.dossier_client.nom,
                "telephone": a.dossier_client.telephone,
                "pack": a.get_pack_display(),
                "taille_sac": a.get_taille_sac_display(),
                "statut": a.get_statut_display(),
                "created": a.created_at.isoformat(),
            }
            for a in abonnements
        ],
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@require_role("administrateur", "superviseur")
def api_ops_generer_commande_abonnement(request, abonnement_id):
    """
    POST /api/ops/abonnements/<abonnement_id>/generer-commande
    Genere manuellement la Commande de l'echeance courante pour cet
    abonnement - appel manuel volontaire (OPS), jamais automatique par
    tache planifiee a ce stade (decision de gouvernance separee, meme
    principe que capacites_activees).
    """
    try:
        abonnement = Abonnement.objects.select_related("dossier_client").get(id=abonnement_id)
    except Abonnement.DoesNotExist:
        return Response({"error": "Abonnement introuvable."}, status=status.HTTP_404_NOT_FOUND)

    try:
        commande = generer_commande_depuis_abonnement(abonnement)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except PrixAbonnementNonConfigure as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "commande_id": commande.id,
        "client": abonnement.dossier_client.nom,
        "prix": float(commande.prix_engage),
        "delai_annonce": commande.delai_annonce,
    }, status=status.HTTP_201_CREATED)
