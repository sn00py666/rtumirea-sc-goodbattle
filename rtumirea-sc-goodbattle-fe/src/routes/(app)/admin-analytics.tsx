import { createFileRoute } from '@tanstack/react-router'

import {
  adminPlatformAnalyticsQueryOptions,
  queryClient,
  useAdminPlatformAnalyticsQuery,
} from '@/api'
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Spinner,
  Typography,
} from '@/components/ui'

export const Route = createFileRoute('/(app)/admin-analytics')({
  component: AdminAnalyticsPage,
  loader: () =>
    queryClient.ensureQueryData(adminPlatformAnalyticsQueryOptions()),
  pendingComponent: PagePending,
})

function AdminAnalyticsPage() {
  const analyticsQuery = useAdminPlatformAnalyticsQuery()
  const analytics = analyticsQuery.data

  if (!analytics) return null

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 py-8">
      <div>
        <Typography variant="h1">Админ-аналитика платформы</Typography>
        <Typography className="mt-1" variant="muted">
          Сводка по активности пользователей и качеству баттлов
        </Typography>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <Metric label="Пользователи" value={String(analytics.total_users)} />
        <Metric label="Баттлы" value={String(analytics.total_battles)} />
        <Metric
          label="Уникальные участники"
          value={String(analytics.unique_participants)}
        />
        <Metric label="Отправки" value={String(analytics.total_submissions)} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Активность и конверсия</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-3 gap-3 text-sm">
          <MetricLine label="DAU" value={String(analytics.dau)} />
          <MetricLine label="WAU" value={String(analytics.wau)} />
          <MetricLine label="MAU" value={String(analytics.mau)} />
          <MetricLine
            label="Ср. участников на баттл"
            value={String(analytics.average_participants_per_battle)}
          />
          <MetricLine
            label="Ср. решаемость"
            value={`${analytics.average_solved_percent}%`}
          />
          <MetricLine
            label="Конверсия в 1-й баттл"
            value={`${analytics.first_battle_conversion_percent}%`}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Воронка организатора</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-3 gap-3 text-sm">
          <MetricLine
            label="Создано комнат"
            value={String(analytics.organizer_funnel.created_rooms)}
          />
          <MetricLine
            label="Запущено баттлов"
            value={String(analytics.organizer_funnel.started_battles)}
          />
          <MetricLine
            label="Завершено баттлов"
            value={String(analytics.organizer_funnel.finished_battles)}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Частоты вердиктов и языков</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4">
          <div className="flex flex-wrap gap-2">
            {analytics.verdict_frequencies.map((verdictItem) => (
              <Badge key={verdictItem.key} variant="outline">
                {verdictItem.key}: {verdictItem.count}
              </Badge>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            {analytics.language_frequencies.map((languageItem) => (
              <Badge key={languageItem.key} variant="outline">
                {languageItem.key}: {languageItem.count}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Топ задач</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <Typography className="mb-2 font-semibold" variant="small">
              По сложности
            </Typography>
            <div className="flex flex-col gap-2">
              {analytics.top_tasks_by_difficulty.map((taskItem) => (
                <MetricLine
                  key={taskItem.task_id}
                  label={taskItem.title}
                  value={`${taskItem.solved_percent}%`}
                />
              ))}
            </div>
          </div>
          <div>
            <Typography className="mb-2 font-semibold" variant="small">
              По популярности
            </Typography>
            <div className="flex flex-col gap-2">
              {analytics.top_tasks_by_popularity.map((taskItem) => (
                <MetricLine
                  key={taskItem.task_id}
                  label={taskItem.title}
                  value={String(taskItem.submissions_count)}
                />
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
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
