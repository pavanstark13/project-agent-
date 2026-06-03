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
from src.trade.risk_manager import DailyLossCap
from src.scheduler.auto_retrain import CloudRetrainScheduler
from fastapi.responses import HTMLResponse
import threading

# Load settings
settings = Settings()

# Initialize components
order_manager = OrderManager(
    exchange_name=settings.exchange_name,
    api_key=settings.api_key,
    secret=settings.api_secret,
)
strategy_engine = StrategyEngine(symbol=settings.default_symbol)
# Scale daily loss cap 
risk_manager = DailyLossCap(daily_loss_cap_pct=settings.daily_loss_cap_pct, initial_equity=10000.0)
scheduler = CloudRetrainScheduler(settings)

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
        current_equity = 10000.0 + backtest_res.get("total_return", 0) * 10000
        if risk_manager.update_equity(current_equity):
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

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    html_content = """
    <html>
        <head>
            <title>Trading AI Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; background: #121212; color: #fff; padding: 20px; }
                .card { background: #1e1e1e; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
                h1 { color: #4caf50; }
            </style>
        </head>
        <body>
            <h1>Trading AI Agent Dashboard</h1>
            <div class="card">
                <h2>Risk Status</h2>
                <p>Trading Halted: {}</p>
                <p>Current Equity: ${:.2f}</p>
            </div>
        </body>
    </html>
    """.format(risk_manager.halt_trading, risk_manager.current_equity)
    return HTMLResponse(content=html_content)

@app.on_event("startup")
def startup_event():
    # Start background scheduler
    scheduler.start()

@app.on_event("shutdown")
def shutdown_event():
    scheduler.stop()

if __name__ == "__main__":
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
