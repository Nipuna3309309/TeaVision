import os
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException


class SmartAuctionClient:
    def __init__(self):
        self.base_url = os.getenv(
            "SMART_AUCTION_API_BASE",
            "http://127.0.0.1:8001/api"
        ).rstrip("/")

        self.timeout = httpx.Timeout(
            timeout=180.0,
            connect=15.0,
            read=180.0,
            write=180.0,
            pool=30.0,
        )

    async def request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, url, json=json_data)
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=(
                    f"Smart Auction service is unreachable. "
                    f"Expected at: {self.base_url}. "
                    f"Error: {e}"
                ),
            )

        if response.status_code >= 400:
            try:
                err = response.json()
                detail = err.get("detail", err)
            except Exception:
                detail = response.text

            raise HTTPException(
                status_code=response.status_code,
                detail=f"Smart Auction service error: {detail}",
            )

        try:
            return response.json()
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Invalid JSON received from Smart Auction service: {e}",
            )

    async def get(self, path: str) -> Dict[str, Any]:
        return await self.request("GET", path)

    async def post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self.request("POST", path, json_data=payload)


smart_auction_client = SmartAuctionClient()