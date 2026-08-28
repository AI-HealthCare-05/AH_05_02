from tortoise import fields
from tortoise.models import Model


class ForestSpace(Model):
    id = fields.BigIntField(primary_key=True)
    group_id = fields.BigIntField(unique=True, db_index=True)
    name = fields.CharField(max_length=40, default="당근의 숲")
    created_by_user_id = fields.BigIntField(db_index=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "forest_spaces"


class ForestAvatar(Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(unique=True, db_index=True)
    display_name = fields.CharField(max_length=20)
    hair_code = fields.CharField(max_length=40, default="midnight_short")
    outfit_code = fields.CharField(max_length=40, default="orange_hoodie")
    accessory_code = fields.CharField(max_length=40, default="none")
    carrot_balance = fields.IntField(default=100)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "forest_avatars"


class ForestInventory(Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(db_index=True)
    item_code = fields.CharField(max_length=40)
    acquired_source = fields.CharField(max_length=40)
    acquired_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "forest_inventories"
        unique_together = (("user_id", "item_code"),)


class ForestObject(Model):
    id = fields.BigIntField(primary_key=True)
    forest_space_id = fields.BigIntField(db_index=True)
    placed_by_user_id = fields.BigIntField(db_index=True)
    object_code = fields.CharField(max_length=40)
    position_x = fields.IntField()
    position_y = fields.IntField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "forest_objects"


class ForestReward(Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField(db_index=True)
    forest_space_id = fields.BigIntField(db_index=True)
    source_key = fields.CharField(max_length=100, unique=True)
    reward_date = fields.DateField(db_index=True)
    carrot_amount = fields.IntField()
    item_code = fields.CharField(max_length=40, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "forest_rewards"
