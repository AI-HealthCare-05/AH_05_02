from tortoise import fields, models


class UserWallet(models.Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(unique=True)
    carrot_balance = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_wallets"


class RewardTransaction(models.Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(db_index=True)
    transaction_type = fields.CharField(max_length=20)
    amount = fields.IntField()
    balance_after = fields.IntField()
    source_type = fields.CharField(max_length=40)
    source_ref = fields.CharField(max_length=100)
    idempotency_key = fields.CharField(max_length=150, unique=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "reward_transactions"


class InventoryItem(models.Model):
    id = fields.BigIntField(primary_key=True)
    code = fields.CharField(max_length=50, unique=True)
    name = fields.CharField(max_length=80)
    category = fields.CharField(max_length=30)
    price_carrots = fields.IntField(default=0)
    asset_ref = fields.CharField(max_length=300, null=True)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "inventory_items"


class UserInventory(models.Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(db_index=True)
    item_id = fields.BigIntField(db_index=True)
    quantity = fields.IntField(default=1)
    acquired_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_inventory"
        unique_together = (("user_id", "item_id"),)


class UserAvatar(models.Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(unique=True)
    equipped_item_ids = fields.JSONField(default=list)
    version = fields.IntField(default=1)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_avatars"
