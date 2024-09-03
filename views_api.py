import re
from http import HTTPStatus

from fastapi import APIRouter, Depends, Query
from lnbits.core.crud import get_standalone_payment, get_user
from lnbits.core.models import WalletTypeInfo
from lnbits.core.services import create_invoice
from lnbits.decorators import get_key_type
from starlette.exceptions import HTTPException

from .crud import (
    create_form,
    create_ticket,
    delete_form,
    delete_ticket,
    get_form,
    get_forms,
    get_ticket,
    get_tickets,
    set_ticket_paid,
    update_form,
)
from .models import CreateFormData, CreateTicketData

lnticket_api_router: APIRouter = APIRouter()


@lnticket_api_router.get("/api/v1/forms")
async def api_forms_get(
    all_wallets: bool = Query(False), wallet: WalletTypeInfo = Depends(get_key_type)
):
    wallet_ids = [wallet.wallet.id]

    if all_wallets:
        user = await get_user(wallet.wallet.user)
        wallet_ids = user.wallet_ids if user else []

    return [form.dict() for form in await get_forms(wallet_ids)]


@lnticket_api_router.post("/api/v1/forms", status_code=HTTPStatus.CREATED)
@lnticket_api_router.put("/api/v1/forms/{form_id}")
async def api_form_create(
    data: CreateFormData, form_id=None, wallet: WalletTypeInfo = Depends(get_key_type)
):
    if form_id:
        form = await get_form(form_id)

        if not form:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, detail="Form does not exist."
            )

        if form.wallet != wallet.wallet.id:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN, detail="Not your form."
            )

        form = await update_form(form_id, **data.dict())
    else:
        form = await create_form(data, wallet.wallet)
    return form.dict()


@lnticket_api_router.delete("/api/v1/forms/{form_id}")
async def api_form_delete(form_id, wallet: WalletTypeInfo = Depends(get_key_type)):
    form = await get_form(form_id)

    if not form:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Form does not exist."
        )

    if form.wallet != wallet.wallet.id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="Not your form.")

    await delete_form(form_id)

    return "", HTTPStatus.NO_CONTENT


#########tickets##########


@lnticket_api_router.get("/api/v1/tickets")
async def api_tickets(
    all_wallets: bool = Query(False), wallet: WalletTypeInfo = Depends(get_key_type)
):
    wallet_ids = [wallet.wallet.id]

    if all_wallets:
        user = await get_user(wallet.wallet.user)
        wallet_ids = user.wallet_ids if user else []

    return [form.dict() for form in await get_tickets(wallet_ids)]


@lnticket_api_router.post("/api/v1/tickets/{form_id}", status_code=HTTPStatus.CREATED)
async def api_ticket_make_ticket(data: CreateTicketData, form_id):
    form = await get_form(form_id)
    if not form:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="LNTicket does not exist."
        )
    if data.sats < 1:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="0 invoices not allowed."
        )

    nwords = len(re.split(r"\s+", data.ltext))

    try:
        payment_hash, payment_request = await create_invoice(
            wallet_id=form.wallet,
            amount=data.sats,
            memo=f"ticket with {nwords} words on {form_id}",
            extra={"tag": "lnticket"},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc

    ticket = await create_ticket(
        payment_hash=payment_hash, wallet=form.wallet, data=data
    )

    if not ticket:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="LNTicket could not be fetched."
        )

    return {"payment_hash": payment_hash, "payment_request": payment_request}


@lnticket_api_router.get("/api/v1/tickets/{payment_hash}", status_code=HTTPStatus.OK)
async def api_ticket_send_ticket(payment_hash):
    ticket = await get_ticket(payment_hash)
    if not ticket:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="LNTicket does not exist."
        )
    payment = await get_standalone_payment(payment_hash, incoming=True)
    if not payment:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Payment does not exist."
        )

    status = await payment.check_status()
    if status.success:
        await set_ticket_paid(payment_hash=payment_hash)
    return {"paid": status.success}


@lnticket_api_router.delete("/api/v1/tickets/{ticket_id}")
async def api_ticket_delete(ticket_id, wallet: WalletTypeInfo = Depends(get_key_type)):
    ticket = await get_ticket(ticket_id)

    if not ticket:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="LNTicket does not exist."
        )

    if ticket.wallet != wallet.wallet.id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="Not your ticket.")

    await delete_ticket(ticket_id)
    return "", HTTPStatus.NO_CONTENT
