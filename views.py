from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from lnbits.core.crud import get_wallet
from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from lnbits.helpers import template_renderer

from .crud import get_form

lnticket_generic_router = APIRouter()


def lnticket_renderer():
    return template_renderer(["lnticket/templates"])


@lnticket_generic_router.get("/", response_class=HTMLResponse)
async def index(request: Request, user: User = Depends(check_user_exists)):
    return lnticket_renderer().TemplateResponse(
        "lnticket/index.html", {"request": request, "user": user.json()}
    )


@lnticket_generic_router.get("/{form_id}")
async def display(request: Request, form_id):
    form = await get_form(form_id)
    if not form:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="LNTicket does not exist."
        )

    wallet = await get_wallet(form.wallet)
    assert wallet

    return lnticket_renderer().TemplateResponse(
        "lnticket/display.html",
        {
            "request": request,
            "form_id": form.id,
            "form_name": form.name,
            "form_desc": form.description,
            "form_amount": form.amount,
            "form_flatrate": form.flatrate,
            "form_wallet": wallet.inkey,
        },
    )
