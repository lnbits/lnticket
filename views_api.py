import re
from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Query

from lnbits.core.crud import get_standalone_payment, get_user
from lnbits.core.models import WalletTypeInfo
from lnbits.core.services import create_invoice
from lnbits.decorators import require_admin_key, require_invoice_key

from .crud import (
    create_form,
    create_ticket,
    delete_form,
    delete_ticket,
    get_form,
    get_forms,
    get_ticket,
    get_tickets,
    update_form,
)
from .models import CreateFormData, CreateTicketData, Form, Ticket
from .services import set_ticket_paid

lnticket_api_router: APIRouter = APIRouter()


@lnticket_api_router.get("/api/v1/forms")
async def api_forms_get(
    all_wallets: bool = Query(False),
    key_info: WalletTypeInfo = Depends(require_admin_key),
) -> list[Form]:
    wallet_ids = [key_info.wallet.id]

    if all_wallets:
        user = await get_user(key_info.wallet.user)
        wallet_ids = user.wallet_ids if user else []

    return await get_forms(wallet_ids)


@lnticket_api_router.post("/api/v1/forms", status_code=HTTPStatus.CREATED)
async def api_form_create(
    data: CreateFormData,
    key_info: WalletTypeInfo = Depends(require_admin_key),
) -> Form:
    if data.wallet != key_info.wallet.id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="Not your wallet.")
    form = await create_form(data)
    return form

@lnticket_api_router.put("/api/v1/forms/{form_id}", status_code=HTTPStatus.CREATED)
async def api_form_update(
    form_id: str, data: CreateFormData, key_info: WalletTypeInfo = Depends(require_admin_key)
) -> Form:
    form = await get_form(form_id)

    if not form:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Form does not exist."
        )

    if form.wallet != key_info.wallet.id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="Not your form.")

    for key, value in data.dict().items():
        setattr(form, key, value)
    form = await update_form(form)
    return form

@lnticket_api_router.delete("/api/v1/forms/{form_id}")
async def api_form_delete(
    form_id: str, key_info: WalletTypeInfo = Depends(require_admin_key)
) -> None:
    form = await get_form(form_id)

    if not form:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Form does not exist."
        )

    if form.wallet != key_info.wallet.id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="Not your form.")

    await delete_form(form_id)


@lnticket_api_router.get("/api/v1/tickets")
async def api_tickets(
    all_wallets: bool = Query(False),
    key_info: WalletTypeInfo = Depends(require_admin_key),
) -> list[Ticket]:
    wallet_ids = [key_info.wallet.id]

    if all_wallets:
        user = await get_user(key_info.wallet.user)
        wallet_ids = user.wallet_ids if user else []

    return await get_tickets(wallet_ids)


@lnticket_api_router.post("/api/v1/tickets/{form_id}", status_code=HTTPStatus.CREATED)
async def api_ticket_make_ticket(data: CreateTicketData, form_id: str):
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
async def api_ticket_send_ticket(payment_hash: str):
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
    if payment.success:
        await set_ticket_paid(ticket)
    return {"paid": payment.success}


@lnticket_api_router.delete("/api/v1/tickets/{ticket_id}")
async def api_ticket_delete(
    ticket_id, wallet: WalletTypeInfo = Depends(require_admin_key)
):
    ticket = await get_ticket(ticket_id)

    if not ticket:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="LNTicket does not exist."
        )

    if ticket.wallet != wallet.wallet.id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="Not your ticket.")

    await delete_ticket(ticket_id)
