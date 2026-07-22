"""
URL configuration for fagniplatform project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from api.api_auth import api_auth_login, api_auth_refresh, api_auth_logout
from api.api_seed import api_seed_test_comptes
from api.api_compte import api_compte_me
from api.api_driver import api_driver_missions, api_driver_mission_workflow
from api.api_partner import api_partner_orders, api_partner_mission_workflow
from api.api_ops import api_ops_dashboard
from api.api_client import api_client_orders, api_client_order_workflow
from api.api_workflow import api_mission_workflow
from api.api_abonnements import api_ops_abonnements, api_ops_generer_commande_abonnement
from api.api_admin_compte import api_admin_creer_compte_ops
from api.api_admin_superuser import api_admin_creer_superuser
from simulateur.api import api_estimer, api_reprendre

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/login', api_auth_login, name='auth_login'),
    path('api/auth/refresh', api_auth_refresh, name='auth_refresh'),
    path('api/auth/logout', api_auth_logout, name='auth_logout'),
    path('api/admin/seed', api_seed_test_comptes, name='admin_seed'),
    path('api/admin/creer-compte-ops', api_admin_creer_compte_ops, name='admin_creer_compte_ops'),
    path('api/admin/creer-superuser', api_admin_creer_superuser, name='admin_creer_superuser'),
    path('api/compte/me', api_compte_me, name='compte_me'),
    path('api/driver/missions', api_driver_missions, name='driver_missions'),
    path('api/driver/missions/<int:mission_id>/workflow', api_driver_mission_workflow, name='driver_mission_workflow'),
    path('api/partner/orders', api_partner_orders, name='partner_orders'),
    path('api/partner/missions/<int:mission_id>/workflow', api_partner_mission_workflow, name='partner_mission_workflow'),
    path('api/ops/dashboard', api_ops_dashboard, name='ops_dashboard'),
    path('api/client/orders', api_client_orders, name='client_orders'),
    path('api/client/orders/<int:commande_id>/workflow', api_client_order_workflow, name='client_order_workflow'),
    path('api/ops/missions/<int:mission_id>/workflow', api_mission_workflow, name='mission_workflow'),
    path('api/ops/abonnements', api_ops_abonnements, name='ops_abonnements'),
    path('api/ops/abonnements/<int:abonnement_id>/generer-commande', api_ops_generer_commande_abonnement, name='ops_generer_commande_abonnement'),
    path('api/simulateur/estimer', api_estimer, name='simulateur_estimer'),
    path('api/simulateur/reprendre/<str:resume_token>', api_reprendre, name='simulateur_reprendre'),
    path('api/', include('dossiers.urls')),
]
