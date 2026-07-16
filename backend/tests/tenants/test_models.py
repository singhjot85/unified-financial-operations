import pytest
from django.conf import settings
from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_context

from apps.tenants.models import Tenants


@pytest.mark.django_db
def test_database_setup():
    """Verify the db setup for tests"""
    assert (
        connection.schema_name == settings.TENANT_SCHEMA_NAME
    ), "Current schema is not correct, it should be private schema"

    with schema_context(get_public_schema_name()):
        assert (
            connection.schema_name == get_public_schema_name()
        ), "Public Schema not created, verify test databse setup."

        private_tenant_qs = Tenants.available_objects.filter(schema_name=settings.TENANT_SCHEMA_NAME)
        assert private_tenant_qs.exists(), "Private Schema not created, verify test databse setup."


@pytest.mark.django_db
def test_public_db_sets_schema_to_public(public_db):
    """Verify public_db sets schema correctly"""

    assert (
        connection.schema_name == get_public_schema_name()
    ), "Current schema is not correct, it should be public schema"
