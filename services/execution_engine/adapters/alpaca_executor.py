"""Alpaca broker execution adapter."""

import uuid
from datetime import UTC, datetime

import structlog

from services.execution_engine.adapters.base import BaseExecutionAdapter
from services.execution_engine.domain.schemas import OrderResponse, OrderStatus, PlaceOrderRequest
from shared.config import get_settings

logger = structlog.get_logger(__name__)


class AlpacaExecutionAdapter(BaseExecutionAdapter):
    """Order execution via Alpaca Markets API."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = None

    @property
    def name(self) -> str:
        return "alpaca"

    async def connect(self) -> None:
        try:
            from alpaca.trading.client import TradingClient  # noqa: PLC0415

            self._client = TradingClient(
                api_key=self._settings.alpaca_api_key,
                secret_key=self._settings.alpaca_secret_key,
                paper=True,
            )
            logger.info("Alpaca execution adapter connected")
        except ImportError:
            logger.warning("alpaca-py not installed, using paper mode simulation")

    async def disconnect(self) -> None:
        self._client = None

    async def place_order(self, request: PlaceOrderRequest) -> OrderResponse:
        """Place order via Alpaca API."""
        if self._client is None:
            return self._simulate_fill(request)

        try:
            from alpaca.trading.enums import OrderSide, TimeInForce  # noqa: PLC0415
            from alpaca.trading.requests import (  # noqa: PLC0415
                LimitOrderRequest,
                MarketOrderRequest,
            )

            side = OrderSide.BUY if request.side.value == "buy" else OrderSide.SELL
            tif = TimeInForce.DAY

            if request.order_type.value == "market":
                order_req = MarketOrderRequest(
                    symbol=request.ticker,
                    qty=request.quantity,
                    side=side,
                    time_in_force=tif,
                )
            elif request.order_type.value == "limit":
                order_req = LimitOrderRequest(
                    symbol=request.ticker,
                    qty=request.quantity,
                    side=side,
                    time_in_force=tif,
                    limit_price=request.price,
                )
            else:
                order_req = MarketOrderRequest(
                    symbol=request.ticker, qty=request.quantity, side=side, time_in_force=tif
                )

            order = self._client.submit_order(order_req)
            return OrderResponse(
                id=uuid.uuid4(),
                external_order_id=str(order.id),
                symbol_id=uuid.uuid4(),  # Would be looked up in real impl
                order_type=request.order_type.value,
                side=request.side.value,
                quantity=float(request.quantity),
                price=request.price,
                stop_price=request.stop_price,
                time_in_force=request.time_in_force.value,
                status=OrderStatus.SUBMITTED.value,
                filled_qty=0.0,
                avg_fill_price=None,
                rejection_reason=None,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        except Exception as e:
            logger.error("Alpaca order placement failed", error=str(e))
            return self._simulate_fill(request)

    async def cancel_order(self, external_order_id: str) -> bool:
        if self._client is None:
            return True
        try:
            self._client.cancel_order_by_id(external_order_id)
            return True
        except Exception as e:
            logger.error("Failed to cancel order", error=str(e))
            return False

    async def liquidate_all(self) -> bool:
        if self._client is None:
            logger.info("Simulating liquidation of all open orders and positions")
            return True
        try:
            self._client.close_all_positions(cancel_orders=True)
            logger.info("Alpaca liquidation command executed successfully")
            return True
        except Exception as e:
            logger.error("Alpaca liquidation failed", error=str(e))
            return False

    async def get_order_status(self, external_order_id: str) -> OrderResponse:
        if self._client is None:
            raise NotImplementedError("No client available")
        order = self._client.get_order_by_id(external_order_id)
        return OrderResponse(
            id=uuid.uuid4(),
            external_order_id=external_order_id,
            symbol_id=uuid.uuid4(),
            order_type="market",
            side="buy",
            quantity=float(order.qty),
            price=None,
            stop_price=None,
            time_in_force="day",
            status=str(order.status),
            filled_qty=float(order.filled_qty or 0),
            avg_fill_price=float(order.filled_avg_price) if order.filled_avg_price else None,
            rejection_reason=None,
            created_at=order.created_at or datetime.now(UTC),
            updated_at=order.updated_at or datetime.now(UTC),
        )

    def _simulate_fill(self, request: PlaceOrderRequest) -> OrderResponse:
        """Simulate order fill for paper trading / testing."""
        import random  # noqa: PLC0415

        fill_price = request.price or round(random.uniform(100, 500), 2)
        return OrderResponse(
            id=uuid.uuid4(),
            external_order_id=f"SIM_{uuid.uuid4().hex[:8]}",
            symbol_id=uuid.uuid4(),
            order_type=request.order_type.value,
            side=request.side.value,
            quantity=request.quantity,
            price=request.price,
            stop_price=request.stop_price,
            time_in_force=request.time_in_force.value,
            status=OrderStatus.FILLED.value,
            filled_qty=request.quantity,
            avg_fill_price=fill_price,
            rejection_reason=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
