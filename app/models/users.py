from enum import StrEnum

from tortoise import fields, models


class Gender(StrEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class User(models.Model):
    id = fields.BigIntField(primary_key=True)
    email = fields.CharField(max_length=40)
    hashed_password = fields.CharField(max_length=128)
    name = fields.CharField(max_length=20, null=True)
    gender = fields.CharEnumField(enum_type=Gender, null=True)
    birthday = fields.DateField(null=True)
    height_cm = fields.FloatField(null=True)
    phone_number = fields.CharField(max_length=11, null=True)
    terms_agreed = fields.BooleanField(default=False)
    terms_agreed_at = fields.DatetimeField(null=True)
    is_active = fields.BooleanField(default=True)
    is_admin = fields.BooleanField(default=False)
    last_login = fields.DatetimeField(null=True)
    auth_version = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "users"


class AuthThrottle(models.Model):
    id = fields.BigIntField(primary_key=True)
    scope = fields.CharField(max_length=30)
    key_hash = fields.CharField(max_length=64)
    failure_count = fields.IntField(default=0)
    lock_level = fields.IntField(default=0)
    locked_until = fields.DatetimeField(null=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "auth_throttles"
        unique_together = (("scope", "key_hash"),)


class PasswordResetToken(models.Model):
    id = fields.BigIntField(primary_key=True)
    user = fields.ForeignKeyField("models.User", related_name="password_reset_tokens", on_delete=fields.CASCADE)
    token_hash = fields.CharField(max_length=64, unique=True)
    expires_at = fields.DatetimeField()
    used_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "password_reset_tokens"
