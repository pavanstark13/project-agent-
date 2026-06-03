"""Risk/Emergency execution API endpoints."""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from services.execution_engine.services.order_manager import OrderManager
from shared.database import get_db

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/kill-switch")
async def trigger_kill_switch(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger the global emergency Kill Switch to liquidate all positions and orders."""
    manager = OrderManager(db)
    try:
        success = await manager.liquidate_all()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to liquidate all positions")
        
        # Also notify Risk Management Service if needed (to activate its circuit breaker)
        import httpx  # noqa: PLC0415
        try:
            # Activate circuit breaker in Risk service
            async with httpx.AsyncClient() as client:
                await client.post(
                    "http://localhost:8003/api/v1/circuit-breaker/activate",
                    params={"reason": "Kill switch triggered via Execution Engine"},
                )
            logger.info("Successfully notified Risk Management Service to activate circuit breaker")
        except Exception as err:
            logger.warning("Could not automatically notify Risk Management Service to activate circuit breaker", error=str(err))

        return {"status": "liquidated", "success": True, "message": "Emergency liquidation triggered successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Kill switch execution failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Emergency liquidation failed: {e}")
