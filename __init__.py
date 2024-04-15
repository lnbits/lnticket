import asyncio

from fastapi import APIRouter
from loguru import logger

from lnbits.db import Database
from lnbits.helpers import template_renderer
from lnbits.tasks import create_permanent_unique_task

db = Database("ext_lnticket")

lnticket_ext: APIRouter = APIRouter(prefix="/lnticket", tags=["LNTicket"])

lnticket_static_files = [
    {
        "path": "/lnticket/static",
        "name": "lnticket_static",
    }
]


def lnticket_renderer():
    return template_renderer(["lnticket/templates"])


from .tasks import wait_for_paid_invoices
from .views import *  # noqa
from .views_api import *  # noqa


scheduled_tasks: list[asyncio.Task] = []


def lnticket_stop():
    for task in scheduled_tasks:
        try:
            task.cancel()
        except Exception as ex:
            logger.warning(ex)


def lnticket_start():
    task = create_permanent_unique_task("ext_lnticket", wait_for_paid_invoices)
    scheduled_tasks.append(task)
