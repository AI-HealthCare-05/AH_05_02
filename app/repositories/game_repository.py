from app.models.game import InventoryItem, RewardTransaction, UserAvatar, UserInventory, UserWallet


class GameRepository:
    async def wallet(self, user_id: int) -> UserWallet:
        wallet, _ = await UserWallet.get_or_create(user_id=user_id)
        return wallet

    async def credit(
        self,
        user_id: int,
        amount: int,
        source_type: str,
        source_ref: str,
        key: str,
        using_db=None,
    ):
        existing = await RewardTransaction.get_or_none(idempotency_key=key, using_db=using_db)
        if existing is not None:
            return existing, False
        wallet = await UserWallet.select_for_update().using_db(using_db).get_or_none(user_id=user_id)
        if wallet is None:
            wallet = await UserWallet.create(user_id=user_id, carrot_balance=0, using_db=using_db)
        wallet.carrot_balance += amount
        await wallet.save(using_db=using_db, update_fields=["carrot_balance", "updated_at"])
        transaction = await RewardTransaction.create(
            user_id=user_id,
            transaction_type="earn" if amount >= 0 else "spend",
            amount=amount,
            balance_after=wallet.carrot_balance,
            source_type=source_type,
            source_ref=source_ref,
            idempotency_key=key,
            using_db=using_db,
        )
        return transaction, True

    async def items(self) -> list[InventoryItem]:
        return await InventoryItem.filter(is_active=True).order_by("price_carrots", "id")

    async def inventory(self, user_id: int) -> list[UserInventory]:
        return await UserInventory.filter(user_id=user_id).order_by("item_id")

    async def avatar(self, user_id: int) -> UserAvatar:
        avatar, _ = await UserAvatar.get_or_create(user_id=user_id)
        return avatar
