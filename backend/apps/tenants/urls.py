from apps.core.api_router import get_api_router_instance
from apps.tenants.views import TenantBrandingViewSet

tenants_router = get_api_router_instance()

tenants_router.register(r"branding", TenantBrandingViewSet, "branding")
