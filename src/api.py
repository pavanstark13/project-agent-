from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import datetime
import os
import uvicorn

# Import modules
from src.multimodal.ingest import ingest
from src.backtest.engine import run_backtest
from src.trade.order_manager import OrderManager
from src.trade.strategy_engine import StrategyEngine
from src.trade.config import Settings
from src.risk import DailyLossCap

# Load settings
settings = Settings()

# Initialize components
order_manager = OrderManager(
    exchange_name=settings.exchange_name,
    api_key=settings.api_key,
    secret=settings.api_secret,
)
strategy_engine = StrategyEngine(symbol=settings.default_symbol)
# Scale daily loss cap (percentage of a base 10,000 unit capital for example)
risk_manager = DailyLossCap(loss_cap=settings.daily_loss_cap_pct * 10000)

app = FastAPI(title="Trading AI Multimodal Service")

@app.post("/execute")
async def execute(file: UploadFile = File(...)):
    try:
        # Save uploaded file temporarily
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        # Process multimodal file
        data = ingest(temp_path)
        # Run backtest on extracted signal
        backtest_res = run_backtest(data.get("signal", []))
        # Validation
        if not strategy_engine.validate(backtest_res):
            raise HTTPException(status_code=403, detail="Strategy validation failed. Trade aborted.")
        # Risk check (daily loss cap)
        pnl = backtest_res.get("total_return", 0) * 1000
        timestamp = datetime.datetime.utcnow().isoformat() + "Z"
        if not risk_manager.update(timestamp, pnl):
            raise HTTPException(status_code=403, detail="Daily loss cap exceeded. Trading halted.")
        # Decision making
        order_spec = strategy_engine.decide(backtest_res, data)
        execution_res = order_manager.execute(order_spec)
        os.remove(temp_path)
        return JSONResponse(content={"ingest": data, "backtest": backtest_res, "order": execution_res})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run")
async def run(file: UploadFile = File(...)):
    try:
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        data = ingest(temp_path)
        backtest_res = run_backtest(data.get("signal", []))
        os.remove(temp_path)
        return JSONResponse(content={"ingest": data, "backtest": backtest_res})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
