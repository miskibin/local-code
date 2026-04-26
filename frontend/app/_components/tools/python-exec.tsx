"use client";

import { CodeBlock, CodeBlockCopyButton } from "@/components/ai-elements/code-block";
import type { ToolArgsProps, ToolRenderer, ToolResultProps } from "./types";
import { DefaultArgs, DefaultResult } from "./default";

function PythonExecArgs({ args, step }: ToolArgsProps) {
  const code = typeof args?.code === "string" ? args.code : "";
  if (!code) return <DefaultArgs args={args} step={step} />;
  return (
    <div className="relative">
      <CodeBlock
        code={code}
        language="python"
        className="overflow-hidden rounded-lg"
        style={{ border: "1px solid var(--border)", background: "var(--code-bg)" }}
      >
        <div className="absolute right-1.5 top-1.5">
          <CodeBlockCopyButton />
        </div>
      </CodeBlock>
    </div>
  );
}

function PythonExecResult({ result, status, step }: ToolResultProps) {
  if (!result) return <DefaultResult result={result} status={status} step={step} />;

  const lines = result.split("\n");
  const stderrIdx = lines.findIndex((l) => l.startsWith("stderr: "));
  const stdout = stderrIdx === -1 ? result : lines.slice(0, stderrIdx).join("\n");
  const stderr =
    stderrIdx === -1
      ? ""
      : [
          lines[stderrIdx].replace(/^stderr:\s*/, ""),
          ...lines.slice(stderrIdx + 1),
        ].join("\n");

  return (
    <div className="flex flex-col gap-1.5">
      {stdout && (
        <pre
          className="m-0 whitespace-pre-wrap break-words rounded-lg px-3 py-2"
          style={{
            background: "var(--code-bg)",
            border: "1px solid var(--border)",
            fontFamily: "var(--font-mono)",
            fontSize: 12.5,
            color: "var(--code-ink)",
            lineHeight: 1.5,
          }}
        >
          {stdout}
        </pre>
      )}
      {stderr && (
        <pre
          className="m-0 whitespace-pre-wrap break-words rounded-lg px-3 py-2"
          style={{
            background: "var(--red-soft)",
            border: "1px solid var(--red)",
            fontFamily: "var(--font-mono)",
            fontSize: 12.5,
            color: "var(--red)",
            lineHeight: 1.5,
          }}
        >
          {stderr}
        </pre>
      )}
    </div>
  );
}

export const pythonExecRenderer: ToolRenderer = {
  Args: PythonExecArgs,
  Result: PythonExecResult,
};
