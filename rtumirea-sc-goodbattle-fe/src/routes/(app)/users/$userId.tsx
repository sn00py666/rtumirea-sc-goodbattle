import { createFileRoute, Link } from '@tanstack/react-router'

import {
  participantPublicAnalyticsQueryOptions,
  queryClient,
  useParticipantPublicAnalyticsQuery,
} from '@/api'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Spinner,
  Typography,
} from '@/components/ui'

export const Route = createFileRoute('/(app)/users/$userId')({
  component: PublicUserAnalyticsPage,
  loader: ({ params }) =>
    queryClient.ensureQueryData(
      participantPublicAnalyticsQueryOptions(params.userId),
    ),
  pendingComponent: PagePending,
})

function PagePending() {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 items-center justify-center py-8">
      <Spinner className="size-6" />
    </div>
  )
}

function PublicUserAnalyticsPage() {
  const { userId } = Route.useParams()
  const analyticsQuery = useParticipantPublicAnalyticsQuery(userId)
  const analytics = analyticsQuery.data

  if (!analytics) return null

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 py-8">
      <div>
        <Typography variant="h1">Профиль участника</Typography>
        <Typography className="mt-1" variant="muted">
          Публичная статистика {analytics.username}
        </Typography>
      </div>

      <Card>
        <CardContent className="grid grid-cols-2 gap-4 pt-0">
          <Stat label="Баттлов" value={String(analytics.battles_count)} />
          <Stat label="Win rate" value={`${analytics.win_rate}%`} />
          <Stat
            label="Решено задач"
            value={String(analytics.solved_tasks_count)}
          />
          <Stat
            label="Ср. место"
            value={
              analytics.average_place != null
                ? String(analytics.average_place)
                : '—'
            }
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>История баттлов</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {analytics.battles.length === 0 && (
            <Typography variant="muted">Нет данных</Typography>
          )}
          {analytics.battles.map((battle) => (
            <div
              className="flex items-center justify-between rounded-lg border p-3"
              key={battle.id}
            >
              <div>
                <Typography className="font-semibold" variant="h3">
                  {battle.title}
                </Typography>
                <Typography variant="muted">
                  {battle.date} • место: {battle.place ?? '—'} •{' '}
                  {battle.solved_tasks}/{battle.total_tasks}
                </Typography>
              </div>

              {battle.status === 'finished' ? (
                <Link
                  className="text-sm text-primary underline"
                  params={{ battleId: battle.id }}
                  to="/battle-analytics/$battleId"
                >
                  Детали
                </Link>
              ) : (
                <Typography variant="muted">В процессе</Typography>
              )}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <Typography className="text-2xl font-semibold" variant="h3">
        {value}
      </Typography>
      <Typography variant="muted">{label}</Typography>
    </div>
  )
}
