"""
Throttling des endpoints publics du simulateur - FAGNI Platform (FOS-213
v1.3 section 11). Par IP uniquement pour /estimer (usage anonyme normal).
Pour /reserver, le throttling par telephone est gere separement au
niveau service (la reservation exige deja un telephone en payload,
contrairement a /estimer qui reste totalement anonyme).
"""
from rest_framework.throttling import AnonRateThrottle


class EstimerThrottle(AnonRateThrottle):
    scope = "simulateur_estimer"


class ReserverThrottle(AnonRateThrottle):
    scope = "simulateur_reserver"
