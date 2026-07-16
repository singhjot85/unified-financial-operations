from django.urls import path

from apps.core.admin import tenant_admin_site
from apps.core.api_router import get_api_router_instance

api_router = get_api_router_instance()


# api_router.register()

urlpatterns = [path("admin/", tenant_admin_site.urls), path("api/", api_router.urls)]
