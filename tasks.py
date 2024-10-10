import asyncio

from lnbits.core.models import Payment
from lnbits.helpers import get_current_extension_name
from lnbits.tasks import register_invoice_listener
from loguru import logger

from .crud import get_ticket
from .services import set_ticket_paid


async def wait_for_paid_invoices():
    invoice_queue = asyncio.Queue()
    register_invoice_listener(invoice_queue, get_current_extension_name())

    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


async def on_invoice_paid(payment: Payment) -> None:
    if not payment.extra or payment.extra.get("tag") != "lnticket":
        # not a lnticket invoice
        return

    ticket = await get_ticket(payment.checking_id)
    if not ticket:
        logger.error("ticket for payment not found", payment)
        return

    await set_ticket_paid(ticket)
