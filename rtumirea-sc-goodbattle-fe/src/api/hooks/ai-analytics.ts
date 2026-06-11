import { useMutation } from '@tanstack/react-query'

export type AiAnalyticsQueryRequest = {
  question: string
}

export type AiAnalyticsQueryResponse = {
  columns: string[]
  generated_at: string
  model: string
  question: string
  report_markdown: string
  row_count: number
  rows: Array<Record<string, unknown>>
  sql: string
  sql_explanation: string
  truncated: boolean
}

export function useAiAnalyticsQuery() {
  return useMutation({
    mutationFn: runAiAnalyticsQuery,
  })
}

async function runAiAnalyticsQuery(
  payload: AiAnalyticsQueryRequest,
): Promise<AiAnalyticsQueryResponse> {
  const response = await fetch(
    `${import.meta.env.VITE_API_URL}/api/analytics/ai/query`,
    {
      body: JSON.stringify(payload),
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      method: 'POST',
    },
  )

  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const detail =
      data && typeof data === 'object' && 'detail' in data
        ? String(data.detail)
        : 'Не удалось выполнить AI-аналитику'
    throw new Error(detail)
  }

  return data as AiAnalyticsQueryResponse
}
