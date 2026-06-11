import { createFileRoute, Link } from '@tanstack/react-router'
import { ArrowLeft } from 'lucide-react'
import { useMemo, useState } from 'react'

import type { components } from '@/api/__generated__/schema'

import {
  battleAnalyticsQueryOptions,
  queryClient,
  useBattleAnalyticsQuery,
} from '@/api'
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Spinner,
  Typography,
} from '@/components/ui'
import { useAuthStore } from '@/stores/auth-store'

export const Route = createFileRoute('/(app)/battle-analytics/$battleId')({
  component: BattleAnalyticsDetailPage,
  loader: async ({ params }) => {
    await queryClient.ensureQueryData(
      battleAnalyticsQueryOptions(params.battleId),
    )
  },
  pendingComponent: PagePending,
})

type BattleSubmission =
  components['schemas']['BattleSubmissionAnalyticsResponse']
type BattleSubmissionTestResult = {
  error_message?: null | string
  execution_memory_kb: number
  execution_time_ms: number
  test_id: string
  verdict: string
}
type BattleSubmissionWithDetails = BattleSubmission & {
  failed_tests?: number
  passed_tests?: number
  test_results?: BattleSubmissionTestResult[]
  total_tests?: number
}

function BattleAnalyticsDetailPage() {
  const { battleId } = Route.useParams()
  const user = useAuthStore((state) => state.user)

  const battleQuery = useBattleAnalyticsQuery(battleId)
  const battle = battleQuery.data

  const [showAllSubmissions, setShowAllSubmissions] = useState(false)
  const battleSubmissions = useMemo(
    () => (battle?.submissions ?? []) as BattleSubmissionWithDetails[],
    [battle?.submissions],
  )
  const currentParticipant = battle?.participants.find(
    (participant) => participant.user_id === user?.id,
  )
  const isParticipantView = currentParticipant != null

  const visibleSubmissions = useMemo(() => {
    if (!isParticipantView) return battleSubmissions
    if (showAllSubmissions) return battleSubmissions
    if (!user) return []
    return battleSubmissions.filter(
      (submission) => submission.user_id === user.id,
    )
  }, [battleSubmissions, isParticipantView, showAllSubmissions, user])

  const submissionsByUser = useMemo(() => {
    const result: Record<string, BattleSubmissionWithDetails[]> = {}
    for (const submission of battleSubmissions) {
      if (!result[submission.user_id]) {
        result[submission.user_id] = []
      }
      result[submission.user_id].push(submission)
    }

    return result
  }, [battleSubmissions])

  if (!battle || !user) return null

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 py-8">
      <div className="flex items-start justify-between gap-3">
        <div>
          <Typography variant="h1">{battle.title}</Typography>
          <Typography className="mt-1" variant="muted">
            {isParticipantView
              ? 'Детальная аналитика баттла (ваш взгляд как участника)'
              : 'Детальная аналитика баттла (взгляд организатора)'}
          </Typography>
        </div>

        <Button asChild variant="outline">
          <Link to="/battles">
            <ArrowLeft className="size-4" />
            Назад
          </Link>
        </Button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Metric
          label="Участники без успешного решения"
          value={String(battle.participants_without_ac_count)}
        />
        <Metric
          label="Доля участников с AI-подсказкой"
          value={`${battle.hint_usage_share}%`}
        />
        <Metric
          label="Статус"
          value={battle.status === 'finished' ? 'Завершен' : 'В процессе'}
        />
      </div>

      {isParticipantView && currentParticipant && (
        <Card>
          <CardHeader>
            <CardTitle>Ваш результат в баттле</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-4 gap-3">
            <MetricLine label="Место" value={`#${currentParticipant.place}`} />
            <MetricLine
              label="Решено задач"
              value={String(currentParticipant.solved_tasks)}
            />
            <MetricLine
              label="Отправок"
              value={String(currentParticipant.submissions_count)}
            />
            <MetricLine
              label="Время"
              value={formatDuration(currentParticipant.total_time_seconds)}
            />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Лидерборд</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          <Typography variant="muted">
            Успешное решение = статус <strong>Accepted</strong> (все тесты
            пройдены).
          </Typography>
          {battle.participants.map((participant) => (
            <details
              className="rounded-lg border p-3"
              key={participant.participant_id}
            >
              <summary className="flex cursor-pointer items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                  <Typography className="font-semibold" variant="small">
                    #{participant.place}
                  </Typography>
                  <Link
                    className="text-sm text-primary underline"
                    params={{ userId: participant.user_id }}
                    to="/users/$userId"
                  >
                    {participant.username}
                  </Link>
                </div>
                <Typography variant="muted">
                  {participant.solved_tasks} задач •{' '}
                  {participant.submissions_count} отправок
                </Typography>
              </summary>

              <div className="mt-3 grid grid-cols-4 gap-2">
                <MetricLine label="Место" value={`#${participant.place}`} />
                <MetricLine
                  label="Решено"
                  value={String(participant.solved_tasks)}
                />
                <MetricLine
                  label="Отправок"
                  value={String(participant.submissions_count)}
                />
                <MetricLine
                  label="Время"
                  value={formatDuration(participant.total_time_seconds)}
                />
                <MetricLine
                  label="Hint"
                  value={participant.hint_used ? 'да' : 'нет'}
                />
                <MetricLine
                  label="Посылок в логе"
                  value={String(
                    (submissionsByUser[participant.user_id] ?? []).length,
                  )}
                />
              </div>
            </details>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Метрики по задачам</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {battle.tasks.map((task) => (
            <div className="rounded-lg border p-3" key={task.task_id}>
              <Typography className="font-semibold" variant="h3">
                {task.title}
              </Typography>
              <div className="mt-2 grid grid-cols-4 gap-2 text-sm">
                <MetricLine
                  label="Время до 1-го успешного решения"
                  value={
                    task.first_ac_time_seconds != null
                      ? formatDuration(task.first_ac_time_seconds)
                      : 'N/A'
                  }
                />
                <MetricLine
                  label="Ср. время успешного решения"
                  value={
                    task.average_time_to_ac_seconds != null
                      ? formatDuration(
                          Math.round(task.average_time_to_ac_seconds),
                        )
                      : 'N/A'
                  }
                />
                <MetricLine
                  label="Ср. отправок"
                  value={String(task.average_submissions)}
                />
                <MetricLine
                  label="Решаемость"
                  value={`${task.solved_percent}%`}
                />
              </div>

              <div className="mt-2 flex flex-wrap gap-2">
                {task.error_frequencies.map((errorItem) => (
                  <Badge
                    key={`${task.task_id}-${errorItem.key}`}
                    variant="outline"
                  >
                    {errorItem.key}: {errorItem.count}
                  </Badge>
                ))}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Проблемные задачи</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {battle.problematic_tasks.map((task) => (
            <div
              className="flex items-center justify-between rounded-lg border p-3"
              key={task.task_id}
            >
              <Typography className="font-semibold" variant="small">
                {task.title}
              </Typography>
              <Typography variant="muted">{task.solved_percent}%</Typography>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            {isParticipantView ? 'Посылки участника' : 'Посылки баттла'}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {isParticipantView && (
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <input
                checked={showAllSubmissions}
                onChange={(event) =>
                  setShowAllSubmissions(event.target.checked)
                }
                type="checkbox"
              />
              Показывать все посылки (не только мои)
            </label>
          )}

          {visibleSubmissions.length === 0 && (
            <Typography variant="muted">Посылок пока нет</Typography>
          )}
          {visibleSubmissions.map((submission) => (
            <details
              className="rounded-lg border p-3"
              key={submission.submission_id}
            >
              <summary className="cursor-pointer">
                <div className="flex items-center justify-between gap-2">
                  <Typography className="font-semibold" variant="small">
                    {submission.username}
                  </Typography>
                  <Badge variant="outline">{submission.verdict}</Badge>
                </div>
                <Typography className="mt-1" variant="muted">
                  {new Date(submission.created_at).toLocaleString('ru-RU')} •{' '}
                  {submission.language} • task: {submission.task_id}
                </Typography>
              </summary>

              <div className="mt-3 grid grid-cols-3 gap-2">
                <MetricLine
                  label="Время проверки"
                  value={`${submission.execution_time_ms} мс`}
                />
                <MetricLine
                  label="Память"
                  value={`${submission.execution_memory_kb} KB`}
                />
                <MetricLine
                  label="Тесты"
                  value={`${getPassedTests(submission)}/${getTotalTests(submission)}`}
                />
              </div>

              <div className="mt-3 rounded-md border bg-muted/30 p-3">
                <Typography className="mb-2 font-semibold" variant="small">
                  Отправленный код
                </Typography>
                <pre className="overflow-x-auto text-xs whitespace-pre-wrap">
                  {submission.source_code}
                </pre>
              </div>

              <div className="mt-3 grid gap-2">
                <Typography className="font-semibold" variant="small">
                  Детали по тестам
                </Typography>
                {getTestResults(submission).map((testResult) => (
                  <div
                    className="grid grid-cols-5 gap-2 rounded-md border px-3 py-2 text-xs"
                    key={`${submission.submission_id}-${testResult.test_id}`}
                  >
                    <span>{testResult.test_id.slice(0, 8)}</span>
                    <span>{testResult.verdict}</span>
                    <span>{testResult.execution_time_ms} мс</span>
                    <span>{testResult.execution_memory_kb} KB</span>
                    <span
                      className="truncate"
                      title={testResult.error_message ?? ''}
                    >
                      {testResult.error_message || 'ok'}
                    </span>
                  </div>
                ))}
              </div>
            </details>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

function formatDuration(totalSeconds: number) {
  const safeSeconds = Math.max(totalSeconds, 0)
  const hours = Math.floor(safeSeconds / 3600)
  const minutes = Math.floor((safeSeconds % 3600) / 60)
  const seconds = safeSeconds % 60

  if (hours > 0) {
    return `${hours}ч ${minutes}м ${seconds}с`
  }
  return `${minutes}м ${seconds}с`
}

function getPassedTests(submission: BattleSubmissionWithDetails) {
  if (submission.passed_tests != null) return submission.passed_tests
  return getTestResults(submission).filter(
    (testResult) => testResult.verdict === 'ACCEPTED',
  ).length
}

function getTestResults(submission: BattleSubmissionWithDetails) {
  return submission.test_results ?? []
}

function getTotalTests(submission: BattleSubmissionWithDetails) {
  if (submission.total_tests != null) return submission.total_tests
  return getTestResults(submission).length
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="pt-0">
        <Typography className="text-2xl font-semibold" variant="h3">
          {value}
        </Typography>
        <Typography variant="muted">{label}</Typography>
      </CardContent>
    </Card>
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

function PagePending() {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 items-center justify-center py-8">
      <Spinner className="size-6" />
    </div>
  )
}
