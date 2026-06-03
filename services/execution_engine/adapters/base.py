"""Base execution adapter interface."""

from abc import ABC, abstractmethod

from services.execution_engine.domain.schemas import OrderResponse, PlaceOrderRequest


class BaseExecutionAdapter(ABC):
    """Abstract base for broker execution adapters."""

    @abstractmethod
    async def place_order(self, request: PlaceOrderRequest) -> OrderResponse:
        """Place an order with the broker."""
        ...

    @abstractmethod
    async def cancel_order(self, external_order_id: str) -> bool:
        """Cancel an order."""
        ...

    @abstractmethod
    async def get_order_status(self, external_order_id: str) -> OrderResponse:
        """Get current order status."""
        ...

    @abstractmethod
    async def connect(self) -> None:
        """Connect to broker."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from broker."""
        ...

    @abstractmethod
    async def liquidate_all(self) -> bool:
        """Cancel all open orders and liquidate all open positions."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Adapter name."""
        ...
