from fastapi import APIRouter, status

from toollib import services
from toollib.api.deps import ClockDep, SessionDep, error_responses
from toollib.models import Category, ItemStatus
from toollib.schemas import ItemCreate, ItemOut

router = APIRouter(prefix="/items", tags=["items"])


@router.post("", status_code=status.HTTP_201_CREATED, responses=error_responses(422))
def create_item(data: ItemCreate, session: SessionDep, clock: ClockDep) -> ItemOut:
    """Add a tool to the library. New items are `available` (ITEM-1)."""
    return ItemOut.model_validate(services.create_item(session, clock, data))


@router.get("")
def list_items(
    session: SessionDep, status: ItemStatus | None = None, category: Category | None = None
) -> list[ItemOut]:
    """List items, optionally filtered by status and category (ITEM-4)."""
    return [ItemOut.model_validate(i) for i in services.list_items(session, status, category)]


@router.get("/{item_id}", responses=error_responses(404))
def get_item(item_id: int, session: SessionDep) -> ItemOut:
    return ItemOut.model_validate(services.get_item(session, item_id))
