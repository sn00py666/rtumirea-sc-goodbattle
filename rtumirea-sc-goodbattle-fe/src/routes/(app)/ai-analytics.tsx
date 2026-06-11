import { createFileRoute, Link } from '@tanstack/react-router'
import { ArrowLeft, Sparkles } from 'lucide-react'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { useAiAnalyticsQuery } from '@/api'
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Spinner,
  Textarea,
  Typography,
} from '@/components/ui'

const EXAMPLE_QUESTIONS = [
  'Покажи топ-10 самых сложных задач по доле Accepted',
  'Сравни среднее число отправок по языкам программирования',
  'Сколько баттлов завершились по таймеру за последние 30 дней',
  'Покажи динамику новых пользователей по дням за 2 месяца',
]

export const Route = createFileRoute('/(app)/ai-analytics')({
  component: AiAnalyticsPage,
})

function AiAnalyticsPage() {
  const aiQuery = useAiAnalyticsQuery()
  const [question, setQuestion] = useState(EXAMPLE_QUESTIONS[0])

  const result = aiQuery.data
  const isPending = aiQuery.isPending

  async function handleSubmit() {
    const trimmedQuestion = question.trim()
    if (!trimmedQuestion || isPending) {
      return
    }
    await aiQuery.mutateAsync({ question: trimmedQuestion })
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 py-8">
      <div className="flex items-start justify-between gap-3">
        <div>
          <Typography className="flex items-center gap-2" variant="h1">
            <Sparkles className="size-6 text-primary" />
            AI аналитика
          </Typography>
          <Typography className="mt-1" variant="muted">
            Опишите вопрос на естественном языке. Агент построит SQL-запрос и
            сформирует отчет по данным платформы.
          </Typography>
        </div>

        <Button asChild variant="outline">
          <Link to="/analytics">
            <ArrowLeft className="size-4" />
            Назад
          </Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Запрос к агенту</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <Textarea
            className="min-h-28"
            maxLength={700}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Например: Покажи проблемные задачи за последнюю неделю и среднее число попыток."
            value={question}
          />

          <div className="flex flex-wrap gap-2">
            {EXAMPLE_QUESTIONS.map((sample) => (
              <Button
                key={sample}
                onClick={() => setQuestion(sample)}
                size="xs"
                type="button"
                variant="outline"
              >
                {sample}
              </Button>
            ))}
          </div>

          <div className="flex items-center justify-between gap-3">
            <Typography variant="muted">{question.length}/700</Typography>
            <Button
              disabled={isPending || question.trim().length < 3}
              onClick={handleSubmit}
            >
              {isPending && <Spinner className="size-4" />}
              Построить отчет
            </Button>
          </div>
        </CardContent>
      </Card>

      {result && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Краткая сводка</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
              <MetricLine label="Модель" value={result.model} />
              <MetricLine
                label="Строк в отчете"
                value={String(result.row_count)}
              />
              <MetricLine
                label="Ограничено лимитом"
                value={result.truncated ? 'да' : 'нет'}
              />
              <MetricLine
                label="Сгенерировано"
                value={new Date(result.generated_at).toLocaleString('ru-RU')}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>SQL-запрос</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Typography variant="muted">{result.sql_explanation}</Typography>
              <pre className="overflow-x-auto rounded-lg border bg-muted/30 p-3 text-xs whitespace-pre-wrap">
                {result.sql}
              </pre>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>AI-отчет</CardTitle>
            </CardHeader>
            <CardContent className="prose prose-sm max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {result.report_markdown}
              </ReactMarkdown>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Результат выборки</CardTitle>
            </CardHeader>
            <CardContent>
              {result.row_count === 0 ? (
                <Typography variant="muted">
                  Нет строк по этому запросу.
                </Typography>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[640px] border-collapse text-sm">
                    <thead>
                      <tr>
                        {result.columns.map((column) => (
                          <th
                            className="border-b px-2 py-2 text-left font-semibold"
                            key={column}
                          >
                            {column}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.rows.map((row, rowIndex) => (
                        <tr className="align-top" key={rowIndex}>
                          {result.columns.map((column) => (
                            <td
                              className="border-b px-2 py-2"
                              key={`${rowIndex}-${column}`}
                            >
                              {formatCell(row[column])}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}

function MetricLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-md border px-3 py-2">
      <Typography variant="muted">{label}</Typography>
      <Typography className="font-semibold" variant="small">
        {value}
      </Typography>
    </div>
  )
}

function formatCell(value: unknown) {
  if (value == null) {
    return '—'
  }
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return String(value)
}
