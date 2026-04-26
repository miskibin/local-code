"use client";

import { use } from "react";
import { Builder } from "@/app/_components/tasks/Builder";

export default function TaskBuilderPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return <Builder taskId={id} />;
}
