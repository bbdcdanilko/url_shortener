import base64
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import Url, UrlOut, UrlsOut, UrlCreate, UrlUpdate, Message

router = APIRouter()


@router.get("/", response_model=UrlsOut)
def read_urls(
        session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve items.
    """

    if current_user.is_superuser:
        count_statement = select(func.count()).select_from(Url)
        count = session.exec(count_statement).one()
        statement = select(Url).offset(skip).limit(limit)
        urls = session.exec(statement).all()
    else:
        count_statement = (
            select(func.count())
            .select_from(Url)
            .where(Url.owner_id == current_user.id)
        )
        count = session.exec(count_statement).one()
        statement = (
            select(Url)
            .where(Url.owner_id == current_user.id)
            .offset(skip)
            .limit(limit)
        )
        urls = session.exec(statement).all()

    return UrlsOut(data=urls, count=count)


@router.get("/{id}", response_model=UrlOut)
def read_url(session: SessionDep, current_user: CurrentUser, id: int) -> Any:
    """
    Get item by ID.
    """
    url = session.get(Url, id)
    if not url:
        raise HTTPException(status_code=404, detail="Url not found")
    if not current_user.is_superuser and (url.owner_id != current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    return url


@router.post("/", response_model=UrlOut)
def create_url(
        *, session: SessionDep, current_user: CurrentUser, url_in: UrlCreate
) -> Any:
    """
    Create new item.
    """
    byte_shorted_url = (url_in.original_url + str(current_user.id)).encode("utf8")
    url = Url.model_validate(url_in, update={"owner_id": current_user.id,
                                             "shorted_url": base64.b64encode(byte_shorted_url)})
    session.add(url)
    session.commit()
    session.refresh(url)
    return url


@router.put("/{id}", response_model=UrlOut)
def update_url(
        *, session: SessionDep, current_user: CurrentUser, id: int, url_in: UrlUpdate
) -> Any:
    """
    Update an item.
    """
    url = session.get(Url, id)
    if not url:
        raise HTTPException(status_code=404, detail="Url not found")
    if not current_user.is_superuser and (url.owner_id != current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    update_dict = url_in.model_dump(exclude_unset=True)
    url.sqlmodel_update(update_dict)
    session.add(url)
    session.commit()
    session.refresh(url)
    return url


@router.delete("/{id}")
def delete_url(session: SessionDep, current_user: CurrentUser, id: int) -> Message:
    """
    Delete an item.
    """
    url = session.get(Url, id)
    if not url:
        raise HTTPException(status_code=404, detail="Url not found")
    if not current_user.is_superuser and (url.owner_id != current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    session.delete(url)
    session.commit()
    return Message(message="Url deleted successfully")
