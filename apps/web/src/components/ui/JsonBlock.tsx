import { useMemo, useState } from "react";

import { Button } from "./Button";

export function JsonBlock({ value }: { value: unknown }) {
  const [copied, setCopied] = useState(false);
  const json = useMemo(() => JSON.stringify(value, null, 2), [value]);

  async function copy() {
    await navigator.clipboard?.writeText(json);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  }

  return (
    <div className="json-block">
      <div className="json-toolbar">
        <span>JSON</span>
        <Button type="button" variant="ghost" onClick={copy}>
          {copied ? "Copied" : "Copy"}
        </Button>
      </div>
      <pre>{json}</pre>
    </div>
  );
}
