from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.apis.responses import envelope
from app.dependencies.security import get_request_user
from app.dtos.game import AvatarEquipRequest
from app.models.users import User
from app.services.game import GameService

game_router = APIRouter(tags=["Reward, inventory and avatar"])


@game_router.get("/wallet")
async def wallet(user: Annotated[User, Depends(get_request_user)]):
    return envelope(await GameService().wallet(user))


@game_router.get("/inventory-items")
async def inventory_items():
    return envelope(await GameService().catalog())


@game_router.get("/inventory")
async def inventory(user: Annotated[User, Depends(get_request_user)]):
    return envelope(await GameService().inventory(user))


@game_router.post("/inventory/items/{item_id}/purchase", status_code=status.HTTP_201_CREATED)
async def purchase(item_id: int, user: Annotated[User, Depends(get_request_user)]):
    return envelope(await GameService().purchase(user, item_id))


@game_router.get("/avatar")
async def avatar(user: Annotated[User, Depends(get_request_user)]):
    return envelope(await GameService().avatar(user))


@game_router.put("/avatar/equipment")
async def equip_avatar(request: AvatarEquipRequest, user: Annotated[User, Depends(get_request_user)]):
    return envelope(await GameService().equip(user, request))
