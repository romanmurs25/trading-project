# Будущая миграция Java/Kafka

## Почему Kafka не используется в MVP

В MVP главная цель — безопасное и тестируемое доменное ядро. Kafka добавляет брокер сообщений, схемы,
replay, мониторинг, операционную поддержку и новые классы отказов. Пока нет больших потоков событий,
независимых команд и требований к горизонтальному масштабированию, это преждевременная сложность.

## Когда Kafka станет оправданной

Kafka стоит рассматривать, когда появятся:

- несколько независимых процессов ingestion/execution/risk;
- высокий поток market data;
- необходимость event replay;
- независимые команды или разные языки реализации;
- строгая интеграция order reconciliation и audit trail;
- требования к масштабированию ingestion отдельно от API.

## Возможные topics

- `market.candles.v1`
- `market.order_book.v1`
- `strategy.signals.v1`
- `orders.intent.v1`
- `risk.decisions.v1`
- `orders.submitted.v1`
- `orders.state_changed.v1`
- `executions.v1`
- `positions.changed.v1`
- `audit.events.v1`
- `system.kill_switch.v1`

## Будущие схемы событий

Каждое событие должно иметь:

- `event_id`
- `event_type`
- `schema_version`
- `ts`
- `source`
- `correlation_id`
- `idempotency_key`
- `payload`

Для финансовых значений payload должен хранить decimal как строку, а не float.

## Какие Python-модули могут стать Java services

- `market-data-ingestion-service`: будущие MOEX/Bybit ingestion adapters.
- `risk-service`: `trading_core.risk`.
- `execution-service`: `trading_core.execution` и broker execution adapters.
- `order-reconciliation-service`: будущий reconciliation модуль.
- `event-replay-service`: future event log replay.

## Соответствие монолита event-driven архитектуре

Сегодня `apps` синхронно собирают `strategy -> risk -> paper broker`. В будущем эти границы можно заменить
на события: стратегия публикует `strategy.signals.v1`, execution service создаёт `orders.intent.v1`,
risk service публикует `risk.decisions.v1`, broker adapter публикует `orders.state_changed.v1` и
`executions.v1`. До этого момента in-process вызовы проще, безопаснее и дешевле в сопровождении.
