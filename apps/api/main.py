from fastapi import FastAPI

from apps.api.routers import backtests, health, instruments, journal, market_data, orders, risk, strategies


def create_app() -> FastAPI:
    application = FastAPI(title="Safety-first Trading Platform", version="0.1.0")
    application.include_router(health.router)
    application.include_router(instruments.router)
    application.include_router(market_data.router)
    application.include_router(backtests.router)
    application.include_router(strategies.router)
    application.include_router(risk.router)
    application.include_router(orders.router)
    application.include_router(journal.router)
    return application


app = create_app()
