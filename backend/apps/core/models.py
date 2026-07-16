import logging
import typing

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import models
from django.http.request import HttpRequest
from model_utils.models import (
    SoftDeletableModel,
    StatusModel,
    TimeStampedModel,
    UUIDModel,
)
from rest_framework.request import Request

from apps.core.constants import DefaultLogStatusChoices
from apps.core.utils import safe_get_object_or_raise

logger = logging.getLogger(__name__)
User = get_user_model()


class InvalidVersionException(Exception):
    """Raised when a version is invalid"""

    pass


class SimpleVersionModelMixin(models.Model):
    DEFAULT_ORDERING = ("-version_major", "-version_minor", "-version_patch")
    DEFAULT_VERSION = (1, 0, 0)

    version_major = models.IntegerField(default=DEFAULT_VERSION[0])
    version_minor = models.IntegerField(default=DEFAULT_VERSION[1])
    version_patch = models.IntegerField(default=DEFAULT_VERSION[2])
    version = models.CharField(null=True, blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.resolve_version()
        return super().save(*args, **kwargs)

    def validate_version(self):
        if not self.version:
            return self.DEFAULT_VERSION

        try:
            major, minor, patch = map(int, self.version.split("."))
            return major, minor, patch
        except Exception as e:
            raise InvalidVersionException from e

    def resolve_version(self):
        if self.version:
            (
                self.version_major,
                self.version_minor,
                self.version_patch,
            ) = self.validate_version()
        else:
            self.version = f"{self.version_major}.{self.version_minor}.{self.version_patch}"


class DeletionTrackingModel(SoftDeletableModel):
    """Model Helper to track .delete(..) on a model instance
    TODO: Handle bulk_delete, after some-stability prevent soft-delete without user.

    Attributes:
        is_removed (BooleanField): Is the Model Soft Deleted
        removed_by (ForeignKey): User that deleted the instance
    """

    deleted_by_fName = "deleted_by"
    removed_by = models.ForeignKey(
        to=User, on_delete=models.RESTRICT, null=True, blank=True, default=None, related_name="+"
    )

    class Meta:
        abstract = True

    def is_valid_user(self, user: typing.Any) -> bool:
        """Check if this user is valid and not anonymous"""
        return isinstance(user, User) and not isinstance(user, AnonymousUser)

    def _get_user_from_request(self, *args, **kwargs):
        """Fetch user from request"""
        request = kwargs.get("request", None)
        if isinstance(request, (HttpRequest, Request)):
            user = getattr(request, "user", None)
            if self.is_valid_user(user):
                return user

        return None

    def _get_user_from_args_kwargs(self, *args, **kwargs):
        """Get user from args and kwargs"""
        # Check kwargs first
        user = kwargs.get(self.deleted_by_fName, None)
        if self.is_valid_user(user):
            return user

        # Check args
        for arg in args:
            if self.is_valid_user(arg):
                return arg

        return None

    def _get_fallback_user(self):
        """Get a fallback user when no user is found"""
        # Try existing removed_by
        if hasattr(self, "removed_by") and self.removed_by is not None:
            return self.removed_by

        # TODO: Once we build an overriden auth package,
        # It'll have a get_system_user() and we'll use that
        # return User.system_user()
        return None

    def get_user_that_deleted(self, *args, **kwargs):
        """
        Get User that deleted the object
        Priority: request.user > removed_by kwarg > User objects in args > fallback
        """
        # Try request first
        user = self._get_user_from_request(*args, **kwargs)
        if user:
            return user

        # Then try args/kwargs
        user = self._get_user_from_args_kwargs(*args, **kwargs)
        if user:
            return user

        # Finally, fallback
        return self._get_fallback_user()

    def delete(
        self, using: typing.Any = None, *args: typing.Any, soft: bool = True, **kwargs: typing.Any
    ) -> tuple[int, dict[str, int]] | None:
        """
        Soft delete object (set its ``removed_by`` field to Foriegn Reference).
        Actually delete object if setting ``soft`` to False.
        """
        if soft:
            # Prevent overwriting removed_by if already soft-deleted
            if not getattr(self, "is_removed", False):
                user = self.get_user_that_deleted(*args, **kwargs)
                if user:
                    self.removed_by = user
                    self.save(using=using)
                else:
                    logger.warning(f"Could not determine user for deletion of {self.__class__.__name__} pk={self.pk}")
            else:
                logger.warning(
                    f"Attempted to soft-delete already deleted object {self.__class__.__name__} pk={self.pk}"
                )

        return super().delete(using, *args, soft=soft, **kwargs)


class AbstractParty:
    """Abstract Helper to give common party related attributes to a model

    Provide Attributes:
        suffix (CharField): Suffix for Name
        first_name (CharField): First name attribute.
        middle_name (CharField): Middle name attribute.
        last_name (CharField): Last name attribute.
        business_name (CharField): Business name attribute.
    """

    suffix = models.CharField(null=True, blank=True, default=None)
    first_name = models.CharField(null=True, blank=True, default=None)
    middle_name = models.CharField(null=True, blank=True, default=None)
    last_name = models.CharField(null=True, blank=True, default=None)
    business_name = models.CharField(null=True, blank=True, default=None)

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimeStampedModel, DeletionTrackingModel):
    """Base Model to be used by most of the models,

    Attributes:
        id (uuid): Sets the primary key for the model to a uuid field.
        created (DateTimeField): Adds the created field that gets auto-updated on model creation.
        modified (DateTimeField): Adds the modified field that gets auto-updated on model update(s).
        is_removed (BooleanField): Is the Model Soft Deleted
        removed_by (ForeignKey): User that deleted the instance
    """

    DEFAULT_ORDERING = ("-created", "-modified", "-pk")

    class Meta:
        abstract = True

    @classmethod
    def get_object(cls, **unique_filters) -> models.Model:
        """
        Getter to fetch database object for current class
        It uses ``available_objects.get``, as we have ``SotDeleteModel``, this is necessary

        Kwargs:
            unique_filters that define's a unique object

        Raises:
            ObjectNotFound
        """
        return safe_get_object_or_raise(cls, **unique_filters)


class BaseLogModel(UUIDModel, TimeStampedModel, StatusModel):
    """
    Base Model for any log(s) related models

    Attributes:
        id (uuid): Sets the primary key for the model to a uuid field.
        created (DateTimeField): Adds the created field that gets auto-updated on model creation.
        modified (DateTimeField): Adds the modified field that gets auto-updated on model update(s).
        status (CharField): Sets a Choice(s) Based Charfield that takes choices from ``STATUS`` class attribute.
        status_changed (DateTimeField): Tacks the status change date-time.
    """

    DEFAULT_ORDERING = ("-created", "-modified", "-pk")

    STATUS = DefaultLogStatusChoices.choices

    class Meta:
        abstract = True


class BaseVersioningModel(UUIDModel, TimeStampedModel, SimpleVersionModelMixin):
    """Base Model to be used by models with Versioning,

    Attributes:
        id (uuid): Sets the primary key for the model to a uuid field.
        created (DateTimeField): Adds the created field that gets auto-updated on model creation.
        modified (DateTimeField): Adds the modified field that gets auto-updated on model update(s).
        version_major, *_minor, *_patch (IntegerField): Three integer fields
        version (CharField): Semantic Version value.
    """

    _major = "major"
    _minor = "minor"
    _patch = "patch"

    _bump_types = (_major, _minor, _patch)

    @classmethod
    def _get_latest_object(cls, **filters) -> models.Model:
        """Get latest object from Database."""
        return cls.objects.filter(**filters).order_by(cls.DEFAULT_ORDERING).first()

    @classmethod
    def get_latest_versions(cls, **filters) -> tuple[int, int, int]:
        """Get latest versions from Database."""
        obj = cls._get_latest_object(**filters)
        return (
            obj.version_major,
            obj.version_minor,
            obj.version_patch if obj else f"{cls.DEFAULT_VERSION[0]}.{cls.DEFAULT_VERSION[1]}.{cls.DEFAULT_VERSION[2]}",
        )

    @classmethod
    def get_latest_version(cls, **filters) -> str:
        """Get latest version from Database."""
        obj = cls._get_latest_object(**filters)
        return obj.version if obj else f"{cls.DEFAULT_VERSION[0]}.{cls.DEFAULT_VERSION[1]}.{cls.DEFAULT_VERSION[2]}"

    def bump_version(self, bump_type: str):
        """
        TODO: Don't like this method, this could be better
        """
        major, minor, patch = self.version_major, self.version_minor, self.version_patch

        if bump_type == self._major:
            major += 1
        elif bump_type == self._minor:
            minor += 1
        elif bump_type == self._patch:
            patch += 1

        self.version_major = major
        self.version_minor = minor
        self.version_patch = patch
        self.save()

    class Meta:
        abstract = True
