"""Shared pagination types."""

from pydantic import BaseModel


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


def total_pages(total: int, page_size: int) -> int:
    if total < 1 or page_size < 1:
        return 0
    return (total + page_size - 1) // page_size
