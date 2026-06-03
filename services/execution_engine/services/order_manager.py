"""Order management service."""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from services.execution_engine.adapters.alpaca_executor import AlpacaExecutionAdapter
from services.execution_engine.domain.schemas import OrderResponse, PlaceOrderRequest

logger = structlog.get_logger(__name__)

_adapter = AlpacaExecutionAdapter()
_initialized = False


async def ensure_adapter() -> None:
    global _initialized  # noqa: PLW0603
    if not _initialized:
        await _adapter.connect()
        _initialized = True


class OrderManager:
    """Manages order lifecycle."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def place_order(self, request: PlaceOrderRequest) -> OrderResponse:
        await ensure_adapter()
        logger.info("Placing order", ticker=request.ticker, side=request.side, qty=request.quantity)
        order = await _adapter.place_order(request)
        logger.info("Order placed", order_id=order.id, status=order.status)
        return order

    async def cancel_order(self, external_order_id: str) -> bool:
        await ensure_adapter()
        result = await _adapter.cancel_order(external_order_id)
        logger.info("Order cancellation", external_id=external_order_id, success=result)
        return result

    async def liquidate_all(self) -> bool:
        await ensure_adapter()
        result = await _adapter.liquidate_all()
        logger.info("Emergency liquidation triggered", success=result)
        return result
