from constance.admin import Config, ConstanceAdmin
from django.contrib import admin
from django.shortcuts import redirect


class PublicAdminSite(admin.AdminSite):
    site_header = "Public Administration"
    site_title = "Public Admin"
    index_title = "Public Portal"

    def login(self, request, extra_context=...):
        """
        If user is alredy logged in redirect to admin
        Else redirect to custom login endpoint
        """

        if request.user.is_authenticated and request.user.is_staff:
            return redirect("admin:index")

        return redirect("/", preserve_request=False)


class TenantAdminSite(admin.AdminSite):
    site_header = "Tenant Administration"
    site_title = "Tenant Admin"
    index_title = "Tenant Portal"

    def login(self, request, extra_context=...):
        """
        If user is alredy logged in redirect to admin
        Else redirect to custom login endpoint
        """

        if request.user.is_authenticated and request.user.is_staff:
            return redirect("admin:index")

        return redirect("/", preserve_request=False)


public_admin_site = PublicAdminSite(name="public_admin")
tenant_admin_site = TenantAdminSite(name="private_admin")


# =============================
#   Register Third Party Admins
# =============================

public_admin_site.register([Config], ConstanceAdmin)
tenant_admin_site.register([Config], ConstanceAdmin)


class ReadOnlyAdmin(admin.ModelAdmin):
    """Read Only Admin Class, a reusable admin utility that converts a admin in readonly, ex: LogModels"""

    def get_readonly_fields(self, request, obj=...):
        """Declare all the Admin fields as readonly"""
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        """Restrict Object creation from list view"""
        return False

    def has_change_permission(self, request, obj=None):
        """Restrict Object change from object view"""
        return False
