from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from trading_core.backtest.engine import BacktestEngine, BacktestResult
from trading_core.domain.enums import TradingMode, Venue
from trading_core.domain.errors import DataValidationError
from trading_core.domain.models import BacktestRun, Candle, Instrument, RiskConfig, utc_now
from trading_core.ports.backtest_broker import BacktestBrokerPort
from trading_core.ports.storage import StoragePort
from trading_core.research.data_quality_gate import DataQualityGateConfig, evaluate_data_quality_gate
from trading_core.research.models import (
    BacktestEquityPoint,
    BacktestTradeRecord,
    ResearchBacktestResult,
    ResearchRun,
    ResearchRunSummary,
    ResearchStatus,
)
from trading_core.research.parameter_grid import parse_parameter_grid
from trading_core.research.reporting import build_research_report
from trading_core.risk.engine import RiskEngine
from trading_core.risk.kill_switch import KillSwitch
from trading_core.strategy.registry import create_strategy, get_strategy_metadata

BrokerFactory = Callable[[Decimal], BacktestBrokerPort]


@dataclass
class ResearchRunner:
    storage: StoragePort
    broker_factory: BrokerFactory

    def run(
        self,
        *,
        strategy_id: str,
        canonical_symbol: str,
        interval: str,
        start: Any,
        end: Any,
        parameter_grid: dict[str, list[Any]],
        initial_cash: Decimal,
        data_quality_gate_config: DataQualityGateConfig,
        max_combinations: int = 500,
    ) -> ResearchRunSummary:
        get_strategy_metadata(strategy_id)
        instrument = self.storage.get_instrument_by_canonical_symbol(canonical_symbol)
        if instrument is None:
            raise DataValidationError(f"instrument not found: {canonical_symbol}")

        candles = self.storage.load_candles(instrument.id, interval, start, end)
        gate_decision = evaluate_data_quality_gate(candles, interval, data_quality_gate_config)
        combinations = parse_parameter_grid(parameter_grid, max_combinations=max_combinations)
        run = ResearchRun(
            strategy_id=strategy_id,
            canonical_symbol=canonical_symbol,
            instrument_id=instrument.id,
            interval=interval,
            start=start,
            end=end,
            parameter_grid=parameter_grid,
            data_quality_gate=data_quality_gate_config.model_dump(mode="json"),
            status=ResearchStatus.RUNNING,
        )
        self.storage.save_research_run(run)

        if not gate_decision.approved:
            failed_result = self._failed_result(
                run,
                params={},
                quality_report=gate_decision.report.model_dump(mode="json"),
                error_message=gate_decision.reason,
            )
            self.storage.save_research_backtest_result(failed_result)
            failed_run = run.model_copy(update={"status": ResearchStatus.FAILED, "completed_at": utc_now()})
            self.storage.save_research_run(failed_run)
            return self._summary(failed_run, [failed_result], len(combinations), [gate_decision.reason])

        results: list[ResearchBacktestResult] = []
        for params in combinations:
            try:
                result = self._run_one(
                    run=run,
                    instrument=instrument,
                    candles=candles,
                    params=params,
                    initial_cash=initial_cash,
                    quality_report=gate_decision.report.model_dump(mode="json"),
                )
            except Exception as exc:
                result = self._failed_result(
                    run,
                    params=params,
                    quality_report=gate_decision.report.model_dump(mode="json"),
                    error_message=str(exc),
                )
                self.storage.save_research_backtest_result(result)
            results.append(result)

        completed = sum(1 for result in results if result.status == ResearchStatus.COMPLETED)
        failed = len(results) - completed
        status = ResearchStatus.COMPLETED
        if failed and completed:
            status = ResearchStatus.PARTIAL
        elif failed:
            status = ResearchStatus.FAILED
        completed_run = run.model_copy(update={"status": status, "completed_at": utc_now()})
        self.storage.save_research_run(completed_run)
        return self._summary(completed_run, results, len(combinations), [])

    def _run_one(
        self,
        *,
        run: ResearchRun,
        instrument: Instrument,
        candles: list[Candle],
        params: dict[str, object],
        initial_cash: Decimal,
        quality_report: dict[str, object],
    ) -> ResearchBacktestResult:
        strategy = create_strategy(run.strategy_id, params)
        paper_instrument = instrument.model_copy(update={"venue": Venue.PAPER})
        paper_candles = [candle.model_copy(update={"venue": Venue.PAPER}) for candle in candles]
        risk_config = RiskConfig(
            trading_mode=TradingMode.PAPER,
            instrument_allowlist=[instrument.id, instrument.canonical_symbol],
        )
        engine = BacktestEngine(
            strategy=strategy,
            risk_engine=RiskEngine(risk_config, KillSwitch(risk_config)),
            broker=self.broker_factory(initial_cash),
        )
        backtest_result = engine.run(paper_candles, paper_instrument)
        backtest_run = self._backtest_run(run, params, initial_cash, risk_config, backtest_result)
        self.storage.save_backtest_run(backtest_run)
        self.storage.save_backtest_equity_points(
            _with_backtest_id(backtest_result.equity_curve, backtest_run.id)
        )
        self.storage.save_backtest_trade_records(
            _with_trade_backtest_id(backtest_result.trade_records, backtest_run.id)
        )
        result = ResearchBacktestResult(
            research_run_id=run.id,
            backtest_run_id=backtest_run.id,
            strategy_id=run.strategy_id,
            canonical_symbol=run.canonical_symbol,
            instrument_id=run.instrument_id,
            interval=run.interval,
            start=run.start,
            end=run.end,
            params=params,
            metrics={key: str(value) for key, value in backtest_result.metrics.items()},
            quality_report=quality_report,
            status=ResearchStatus.COMPLETED,
        )
        self.storage.save_research_backtest_result(result)
        return result

    def _backtest_run(
        self,
        run: ResearchRun,
        params: dict[str, object],
        initial_cash: Decimal,
        risk_config: RiskConfig,
        result: BacktestResult,
    ) -> BacktestRun:
        return BacktestRun(
            strategy_id=run.strategy_id,
            strategy_config=params,
            risk_config=risk_config.model_dump(mode="json"),
            instruments=[run.instrument_id],
            start=run.start,
            end=run.end,
            initial_cash=initial_cash,
            final_equity=result.final_equity,
            total_pnl=result.total_pnl,
            max_drawdown=result.max_drawdown,
            win_rate=result.win_rate,
            profit_factor=result.profit_factor,
            expectancy=result.expectancy,
            avg_r=result.avg_r,
            trades_count=result.trades_count,
        )

    def _failed_result(
        self,
        run: ResearchRun,
        *,
        params: dict[str, object],
        quality_report: dict[str, object],
        error_message: str,
    ) -> ResearchBacktestResult:
        return ResearchBacktestResult(
            research_run_id=run.id,
            backtest_run_id=None,
            strategy_id=run.strategy_id,
            canonical_symbol=run.canonical_symbol,
            instrument_id=run.instrument_id,
            interval=run.interval,
            start=run.start,
            end=run.end,
            params=params,
            metrics={},
            quality_report=quality_report,
            status=ResearchStatus.FAILED,
            error_message=error_message,
        )

    def _summary(
        self,
        run: ResearchRun,
        results: list[ResearchBacktestResult],
        parameter_combinations: int,
        warnings: list[str],
    ) -> ResearchRunSummary:
        report = build_research_report(run, results)
        report_warnings = report.get("warnings", []) if isinstance(report, dict) else []
        return ResearchRunSummary(
            research_run_id=run.id,
            strategy_id=run.strategy_id,
            canonical_symbol=run.canonical_symbol,
            interval=run.interval,
            start=run.start,
            end=run.end,
            parameter_combinations=parameter_combinations,
            completed_backtests=sum(1 for result in results if result.status == ResearchStatus.COMPLETED),
            failed_backtests=sum(1 for result in results if result.status == ResearchStatus.FAILED),
            best_result_by_profit_factor=(
                report.get("best_by_profit_factor") if isinstance(report, dict) else None
            ),
            best_result_by_expectancy=report.get("best_by_expectancy") if isinstance(report, dict) else None,
            warnings=[*warnings, *report_warnings],
        )


def _with_backtest_id(points: list[BacktestEquityPoint], backtest_run_id: str) -> list[BacktestEquityPoint]:
    return [point.model_copy(update={"backtest_run_id": backtest_run_id}) for point in points]


def _with_trade_backtest_id(
    records: list[BacktestTradeRecord],
    backtest_run_id: str,
) -> list[BacktestTradeRecord]:
    return [record.model_copy(update={"backtest_run_id": backtest_run_id}) for record in records]
