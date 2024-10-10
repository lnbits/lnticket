import httpx

from .crud import get_form, update_form, update_ticket
from .models import Ticket


async def send_webhook(webhook: str, ticket: Ticket) -> None:
    async with httpx.AsyncClient() as client:
        await client.post(
            webhook,
            json={
                "form": ticket.form,
                "name": ticket.name,
                "email": ticket.email,
                "content": ticket.ltext,
            },
            timeout=6,
        )


async def set_ticket_paid(ticket: Ticket) -> Ticket:
    if not ticket.paid:
        ticket.paid = True
        await update_ticket(ticket)
        formdata = await get_form(ticket.form)
        assert formdata, "Couldn't get form from paid ticket"
        formdata.amountmade += ticket.sats
        await update_form(formdata)
        if formdata.webhook:
            await send_webhook(formdata.webhook, ticket)

    return ticket
