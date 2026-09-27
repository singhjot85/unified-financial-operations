from django.urls import include, path

from apps.core.admin import tenant_admin_site
from apps.tenants.urls import tenants_router

# from apps.crm.urls import crm_router

urlpatterns = [
    path("admin/", tenant_admin_site.urls, name="admin"),
    path(
        "api/",
        include(
            [
                *tenants_router.urls,
                # *crm_router.urls
            ]
        ),
    ),
]
