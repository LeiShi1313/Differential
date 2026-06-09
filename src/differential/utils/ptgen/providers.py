from dataclasses import dataclass
from typing import Any, Dict, Protocol, Sequence
from urllib.parse import quote

import requests

from differential.utils.ptgen.reference import PTGenReference


class PTGenProviderError(Exception):
    pass


class PTGenProvider(Protocol):
    name: str

    def fetch(
        self,
        reference: PTGenReference,
        session: requests.Session,
        timeout: int,
    ) -> Dict[str, Any]:
        ...


def _response_json(provider_name: str, response: requests.Response) -> Dict[str, Any]:
    if not response.ok:
        raise PTGenProviderError(
            f"{provider_name} HTTP {response.status_code} - {response.reason}"
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise PTGenProviderError(f"{provider_name} returned invalid JSON") from exc

    if not isinstance(data, dict):
        raise PTGenProviderError(f"{provider_name} returned non-object JSON")
    return data


@dataclass(frozen=True)
class StaticPtGenProvider:
    name: str
    base_url: str

    def url_for(self, reference: PTGenReference) -> str:
        site = quote(reference.site, safe="")
        sid = quote(reference.sid, safe="")
        return f"{self.base_url.rstrip('/')}/{site}/{sid}.json"

    def fetch(
        self,
        reference: PTGenReference,
        session: requests.Session,
        timeout: int,
    ) -> Dict[str, Any]:
        response = session.get(self.url_for(reference), timeout=timeout)
        return _response_json(self.name, response)


@dataclass(frozen=True)
class ApiPtGenProvider:
    name: str
    base_url: str

    def fetch(
        self,
        reference: PTGenReference,
        session: requests.Session,
        timeout: int,
    ) -> Dict[str, Any]:
        response = session.get(
            self.base_url,
            params={"site": reference.site, "sid": reference.sid},
            timeout=timeout,
        )
        return _response_json(self.name, response)


DEFAULT_PTGEN_PROVIDERS: Sequence[PTGenProvider] = (
    StaticPtGenProvider(
        name="ourhelp-cdn",
        base_url="https://cdn.ourhelp.club/ptgen",
    ),
    StaticPtGenProvider(
        name="github-pages",
        base_url="https://ourbits.github.io/PtGen",
    ),
    ApiPtGenProvider(
        name="ourhelp-api",
        base_url="https://api.ourhelp.club/infogen",
    ),
)
