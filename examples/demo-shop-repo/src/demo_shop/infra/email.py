"""Email adapter stub."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmailClient:
    sender: str

    def send(self, to: str, subject: str, body: str) -> None:
        print(
            f'email from={self.sender} to={to} subject={subject!r} body={body!r}'
        )
