# Risk Management

`RiskEngine` в MVP выполняет pre-trade проверки:

- режим торговли и запрет live trading по умолчанию;
- allowlist инструмента;
- активность торговой сессии;
- свежесть market data;
- максимальный спред;
- максимальный риск на сделку;
- дневной и недельный лимит убытка;
- максимальное число открытых позиций;
- максимальный размер позиции;
- максимальная notional exposure;
- максимальное количество в ордере;
- запрет повторного idempotency key;
- запрет market orders в live mode без явного разрешения;
- активность `KillSwitch`.

`KillSwitch` блокирует новые ордера. Если включён `allow_reduce_only_when_killed`, он может пропускать только
position-reducing заявки.

## Idempotency

`RiskEngine` проверяет:

- `idempotency_key_present`;
- `idempotency_key_is_new`.

Одобренный ключ добавляется в набор использованных ключей. Повторный `OrderIntent` с тем же ключом
отклоняется до брокера.

## Live allowlist

В `LIVE_GUARDED` пустой `instrument_allowlist` всегда блокирует ордер, даже если `ALLOW_LIVE_TRADING=true`
и адаптер поддерживает live execution.

## Reduce-only when killed

Когда `KillSwitch` активен и `allow_reduce_only_when_killed=true`, допускаются только заявки, уменьшающие
абсолютную позицию:

- long 2, `SELL 1` разрешён;
- long 2, `SELL 3` запрещён, потому что flip через ноль;
- short -2, `BUY 1` разрешён;
- short -2, `BUY 3` запрещён;
- flat 0, новый order запрещён.
