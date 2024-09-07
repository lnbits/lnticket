import time
from typing import Optional, Union

import httpx
from lnbits.core.models import Wallet
from lnbits.db import Database
from lnbits.helpers import insert_query, update_query, urlsafe_short_hash

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
        time=int(time.time()),
    )
    await db.execute(
        insert_query("lnticket.ticket", ticket),
        ticket.dict(),
    )
    return ticket


async def set_ticket_paid(payment_hash: str) -> Ticket:
    row = await db.fetchone(
        "SELECT * FROM lnticket.ticket WHERE id = :id", {"id": payment_hash}
    )
    assert row, "Ticket not found"
    first_ticket = Ticket(**row)
    if not first_ticket.paid:
        await db.execute(
            "UPDATE lnticket.ticket SET paid = true WHERE id = :id",
            {"id": payment_hash},
        )

        formdata = await get_form(first_ticket.form)
        assert formdata, "Couldn't get form from paid ticket"

        amount = formdata.amountmade + first_ticket.sats
        await db.execute(
            "UPDATE lnticket.form2 SET amountmade = :amount WHERE id = :id",
            {"amount": amount, "id": first_ticket.form},
        )

        ticket = await get_ticket(payment_hash)
        assert ticket, "Newly paid ticket could not be retrieved"

        if formdata.webhook:
            async with httpx.AsyncClient() as client:
                await client.post(
                    formdata.webhook,
                    json={
                        "form": ticket.form,
                        "name": ticket.name,
                        "email": ticket.email,
                        "content": ticket.ltext,
                    },
                    timeout=40,
                )
            return ticket

    new_ticket = await get_ticket(payment_hash)
    assert new_ticket, "Newly paid ticket could not be retrieved"
    return new_ticket


async def get_ticket(ticket_id: str) -> Optional[Ticket]:
    row = await db.fetchone(
        "SELECT * FROM lnticket.ticket WHERE id = :id", {"id": ticket_id}
    )
    return Ticket(**row) if row else None


async def get_tickets(wallet_ids: Union[str, list[str]]) -> list[Ticket]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]

    q = ",".join([f"'{wallet_id}'" for wallet_id in wallet_ids])
    rows = await db.fetchall(f"SELECT * FROM lnticket.ticket WHERE wallet IN ({q})")

    return [Ticket(**row) for row in rows]


async def delete_ticket(ticket_id: str) -> None:
    await db.execute("DELETE FROM lnticket.ticket WHERE id = :id", {"id": ticket_id})


async def create_form(data: CreateFormData, wallet: Wallet) -> Form:
    form_id = urlsafe_short_hash()
    form = Form(
        id=form_id,
        wallet=wallet.id,
        name=wallet.name,
        webhook=data.webhook,
        description=data.description,
        flatrate=data.flatrate,
        amount=data.amount,
        amountmade=0,
        time=int(time.time()),
    )
    await db.execute(
        insert_query("lnticket.form2", form),
        form.dict(),
    )
    return form


async def update_form(form: Form) -> Form:
    await db.execute(
        update_query("lnticket.form2", form),
        form.dict(),
    )
    row = await db.fetchone(
        "SELECT * FROM lnticket.form2 WHERE id = :id", {"id": form.id}
    )
    assert row, "Newly updated form couldn't be retrieved"
    return Form(**row)


async def get_form(form_id: str) -> Optional[Form]:
    row = await db.fetchone(
        "SELECT * FROM lnticket.form2 WHERE id = :id", {"id": form_id}
    )
    return Form(**row) if row else None


async def get_forms(wallet_ids: Union[str, list[str]]) -> list[Form]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]

    q = ",".join([f"'{wallet_id}'" for wallet_id in wallet_ids])
    rows = await db.fetchall(f"SELECT * FROM lnticket.form2 WHERE wallet IN ({q})")

    return [Form(**row) for row in rows]


async def delete_form(form_id: str) -> None:
    await db.execute("DELETE FROM lnticket.form2 WHERE id = :id", {"id": form_id})
