from apps.core.serializers import ReadOnlyModelSerializer
from apps.tenants.models import (
    TenantBranding,
    TenantConfiguration,
    TenantContactInfo,
    Tenants,
)


class TenantContactInfoSerializer(ReadOnlyModelSerializer):

    class Meta:
        model = TenantContactInfo
        fields = ["order", "contact_type", "tenant", "value"]


class TenantSerializer(ReadOnlyModelSerializer):

    tenant_contact = TenantContactInfoSerializer(many=True, read_only=True, required=False, source="contact_info")

    class Meta:
        model = Tenants
        fields = ["label", "is_active", "public_id", "tenant_contact"]


class TenantConfigurationSerializer(ReadOnlyModelSerializer):

    class Meta:
        model = TenantConfiguration
        fields = ["name", "tenant", "details"]


class TenantBrandingSerializer(ReadOnlyModelSerializer):

    tenant = TenantSerializer(read_only=True, required=False)

    class Meta:
        model = TenantBranding
        fields = ["tenant", "details"]
