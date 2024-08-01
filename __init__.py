import asyncio

from fastapi import APIRouter
from loguru import logger

from .crud import db
from .tasks import wait_for_paid_invoices
from .views import lnticket_generic_router
from .views_api import lnticket_api_router

lnticket_ext: APIRouter = APIRouter(prefix="/lnticket", tags=["LNTicket"])
lnticket_ext.include_router(lnticket_generic_router)
lnticket_ext.include_router(lnticket_api_router)
lnticket_static_files = [
    {
        "path": "/lnticket/static",
        "name": "lnticket_static",
    }
]
scheduled_tasks: list[asyncio.Task] = []


def lnticket_stop():
    for task in scheduled_tasks:
        try:
            task.cancel()
        except Exception as ex:
            logger.warning(ex)


def lnticket_start():
    from lnbits.tasks import create_permanent_unique_task

    task = create_permanent_unique_task("ext_lnticket", wait_for_paid_invoices)
    scheduled_tasks.append(task)


__all__ = [
    "db",
    "lnticket_ext",
    "lnticket_static_files",
    "lnticket_start",
    "lnticket_stop",
]
