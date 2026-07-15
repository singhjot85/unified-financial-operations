from django.conf import settings

# from django.urls import include, path
from rest_framework.routers import DefaultRouter, SimpleRouter

# from apps.customer_management.views import WorkflowViewSet
# from apps.tenants.views import BrandingViewSet
# from utils.admin_utils import private_admin_site
# from utils.view_utils import ConnTestMixin

app_name = "api"

router = SimpleRouter()
if settings.DEBUG:
    router = DefaultRouter()

# router.register(r"workflow", WorkflowViewSet, "workflow")
# router.register(r"branding", BrandingViewSet, "branding")
# router.register(r"conn-test", ConnTestMixin, "conn-test")

# api_urlpatterns = [
#     path("admin/", private_admin_site.urls, name="admin"),
#     path("auth/", include("dj_rest_auth.urls")),
# ]

# api_urlpatterns.extend(router.urls)

urlpatterns = [
    # path("api/", include(api_urlpatterns)),
]
