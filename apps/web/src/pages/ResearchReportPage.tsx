import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { apiGet } from "../api/client";
import type { ResearchReport } from "../api/types";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { ErrorState } from "../components/ui/ErrorState";
import { JsonBlock } from "../components/ui/JsonBlock";
import { LoadingState } from "../components/ui/LoadingState";

export function ResearchReportPage() {
  const { runId = "" } = useParams();
  const report = useQuery({
    queryKey: ["research-report", runId],
    queryFn: () => apiGet<ResearchReport>(`/api/research/runs/${encodeURIComponent(runId)}/report`),
    enabled: Boolean(runId),
  });

  if (report.isLoading) {
    return <LoadingState />;
  }
  if (report.error) {
    return <ErrorState error={report.error} />;
  }

  const markdown = typeof report.data?.markdown === "string" ? report.data.markdown : null;

  return (
    <div className="page-stack">
      <div className="page-title">
        <p className="eyebrow">Research report</p>
        <h2>{runId}</h2>
      </div>
      <Link to={`/research/${encodeURIComponent(runId)}`}><Button variant="secondary">Back to run</Button></Link>
      {markdown ? (
        <Card title="Markdown report">
          <pre className="markdown-view">{markdown}</pre>
        </Card>
      ) : null}
      <Card title="JSON report">
        <JsonBlock value={report.data} />
      </Card>
    </div>
  );
}
