from datetime import datetime
from typing import Optional, Union

from lnbits.db import Database
from lnbits.helpers import urlsafe_short_hash

from .models import CreateFormData, CreateTicketData, Form, Ticket

db = Database("ext_lnticket")


async def create_ticket(
    payment_hash: str, wallet: str, data: CreateTicketData
) -> Ticket:
    ticket = Ticket(
        id=payment_hash,
        form=data.form,
        email=data.email,
        ltext=data.ltext,
        name=data.name,
        wallet=wallet,
        sats=data.sats,
        paid=False,
        time=datetime.now(),
    )
    await db.insert("lnticket.ticket", ticket)
    return ticket


async def update_ticket(ticket: Ticket) -> Ticket:
    await db.update("lnticket.ticket", ticket)
    return ticket


async def get_ticket(ticket_id: str) -> Optional[Ticket]:
    return await db.fetchone(
        "SELECT * FROM lnticket.ticket WHERE id = :id",
        {"id": ticket_id},
        Ticket,
    )


async def get_tickets(wallet_ids: Union[str, list[str]]) -> list[Ticket]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]
    q = ",".join([f"'{wallet_id}'" for wallet_id in wallet_ids])
    return await db.fetchall(
        f"SELECT * FROM lnticket.ticket WHERE wallet IN ({q})",
        model=Ticket,
    )


async def delete_ticket(ticket_id: str) -> None:
    await db.execute("DELETE FROM lnticket.ticket WHERE id = :id", {"id": ticket_id})


async def create_form(data: CreateFormData) -> Form:
    form_id = urlsafe_short_hash()
    form = Form(
        id=form_id,
        wallet=data.wallet,
        name=data.name,
        webhook=data.webhook,
        description=data.description,
        flatrate=data.flatrate,
        amount=data.amount,
        amountmade=0,
        time=datetime.now(),
    )
    await db.insert("lnticket.form2", form)
    return form


async def update_form(form: Form) -> Form:
    await db.update("lnticket.form2", form)
    return form


async def get_form(form_id: str) -> Optional[Form]:
    return await db.fetchone(
        "SELECT * FROM lnticket.form2 WHERE id = :id",
        {"id": form_id},
        Form,
    )


async def get_forms(wallet_ids: Union[str, list[str]]) -> list[Form]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]
    q = ",".join([f"'{wallet_id}'" for wallet_id in wallet_ids])
    return await db.fetchall(
        f"SELECT * FROM lnticket.form2 WHERE wallet IN ({q})",
        model=Form,
    )


async def delete_form(form_id: str) -> None:
    await db.execute("DELETE FROM lnticket.form2 WHERE id = :id", {"id": form_id})
