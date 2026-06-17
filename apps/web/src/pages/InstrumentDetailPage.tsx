import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { apiGet } from "../api/client";
import type { InstrumentDetail } from "../api/types";
import { Card } from "../components/ui/Card";
import { DateTimeCell } from "../components/ui/DateTimeCell";
import { DecimalCell } from "../components/ui/DecimalCell";
import { ErrorState } from "../components/ui/ErrorState";
import { JsonBlock } from "../components/ui/JsonBlock";
import { LoadingState } from "../components/ui/LoadingState";

export function InstrumentDetailPage() {
  const { instrumentId, canonicalSymbol } = useParams();
  const path = canonicalSymbol
    ? `/api/instruments/by-symbol/${encodeURIComponent(canonicalSymbol)}`
    : `/api/instruments/${encodeURIComponent(instrumentId ?? "")}`;
  const detail = useQuery({
    queryKey: ["instrument-detail", path],
    queryFn: () => apiGet<InstrumentDetail>(path),
    enabled: Boolean(instrumentId || canonicalSymbol),
  });

  if (detail.isLoading) {
    return <LoadingState />;
  }
  if (detail.error) {
    return <ErrorState error={detail.error} />;
  }

  const instrument = detail.data?.instrument;
  const spec = detail.data?.contract_spec;

  return (
    <div className="page-stack">
      <div className="page-title">
        <p className="eyebrow">Детали инструмента</p>
        <h2>{instrument?.canonical_symbol ?? "Инструмент"}</h2>
      </div>
      <Card title="Инструмент">
        <dl className="details-grid">
          <div>
            <dt>Native symbol</dt>
            <dd>{instrument?.native_symbol}</dd>
          </div>
          <div>
            <dt>Площадка</dt>
            <dd>{instrument?.venue}</dd>
          </div>
          <div>
            <dt>Класс актива</dt>
            <dd>{instrument?.asset_class}</dd>
          </div>
          <div>
            <dt>Экспирация</dt>
            <dd><DateTimeCell value={instrument?.expiry_date} /></dd>
          </div>
        </dl>
      </Card>
      <Card title="Спецификация контракта">
        {spec ? (
          <dl className="details-grid">
            <div>
              <dt>Lot size</dt>
              <dd><DecimalCell value={spec.lot_size} /></dd>
            </div>
            <div>
              <dt>Tick size</dt>
              <dd><DecimalCell value={spec.tick_size} /></dd>
            </div>
            <div>
              <dt>Tick value</dt>
              <dd><DecimalCell value={spec.tick_value} /></dd>
            </div>
            <div>
              <dt>Валюта</dt>
              <dd>{spec.currency}</dd>
            </div>
          </dl>
        ) : (
          <p className="muted">Спецификация контракта не сохранена.</p>
        )}
      </Card>
      <Card title="Metadata">
        <JsonBlock value={{ instrument: instrument?.metadata, contract_spec: spec?.metadata ?? null }} />
      </Card>
    </div>
  );
}
