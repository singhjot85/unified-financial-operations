import logging
import typing

import pytest
from django.conf import settings
from django_tenants.test.client import TenantClient
from django_tenants.utils import (
    get_public_schema_name,
    get_tenant_model,
    schema_context,
)

if typing.TYPE_CHECKING:
    from apps.tenants.models import Tenants

TEST_SCHEMA_NAME = settings.TENANT_SCHEMA_NAME
LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Hooks into pytest-django's database setup to ensure the test tenant
    is created (and its schema migrated) exactly once per test session.
    """
    with django_db_blocker.unblock():
        Tenant: "Tenants" = get_tenant_model()

        test_tenant, created = Tenant.objects.get_or_create(
            schema_name=TEST_SCHEMA_NAME,
            defaults={"label": TEST_SCHEMA_NAME.replace("_", ""), "is_active": True, "public_id": "Test-XXXXX"},
        )
        if created:
            LOGGER.info(msg=f"Created Test Tenant Schema >>> {test_tenant}")


@pytest.fixture
def tenant(db):
    Tenant: "Tenants" = get_tenant_model()

    test_tenant, created = Tenant.objects.get_or_create(
        schema_name=TEST_SCHEMA_NAME,
        defaults={"label": TEST_SCHEMA_NAME.replace("_", ""), "is_active": True, "public_id": "Test-XXXXX"},
    )
    return test_tenant


@pytest.fixture(autouse=True)
def tenant_db(db, tenant):
    """
    Automatically activates the tenant schema context for ALL tests.
    Requires the 'db' fixture, ensuring DB access is enabled globally.
    """
    with schema_context(tenant.schema_name):
        yield


@pytest.fixture
def public_db(db):
    """
    Context manager that activates the public schema.
    Call this explicitly in tests that require the public database.
    """
    with schema_context(get_public_schema_name()):
        yield


@pytest.fixture
def tenant_client(tenant):
    """
    Provides a Django test client automatically configured for the test tenant.
    """
    return TenantClient(tenant)
