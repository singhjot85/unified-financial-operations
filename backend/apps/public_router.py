from django.urls import include, path

from apps.core.admin import public_admin_site
from apps.core.api_router import get_api_router_instance

api_router = get_api_router_instance()


# api_router.register()

urlpatterns = [path("admin/", public_admin_site.urls, name="admin"), path("api/", include(api_router.urls))]
