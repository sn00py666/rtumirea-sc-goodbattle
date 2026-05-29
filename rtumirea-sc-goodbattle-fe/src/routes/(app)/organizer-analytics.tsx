import { createFileRoute, Link } from '@tanstack/react-router'
import { ArrowLeft } from 'lucide-react'
import { useMemo, useState } from 'react'

import type { components } from '@/api/__generated__/schema'

import {
  organizerAnalyticsQueryOptions,
  queryClient,
  useOrganizerAnalyticsQuery,
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
import { Input } from '@/components/ui/input'

export const Route = createFileRoute('/(app)/organizer-analytics')({
  component: OrganizerAnalyticsPage,
  loader: () => queryClient.ensureQueryData(organizerAnalyticsQueryOptions()),
  pendingComponent: PagePending,
})

type BattleListItem = components['schemas']['AnalyticsBattleListItemResponse']

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

function Metric({
  label,
  value,
}: {
  label: string
  value: string
}) {
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

function MetricLine({
  label,
  value,
}: {
  label: string
  value: string
}) {
  return (
    <div className="flex items-center justify-between rounded-md border px-3 py-2">
      <Typography variant="muted">{label}</Typography>
      <Typography className="font-semibold" variant="small">
        {value}
      </Typography>
    </div>
  )
}

function OrganizerAnalyticsPage() {
  const analyticsQuery = useOrganizerAnalyticsQuery()
  const analytics = analyticsQuery.data

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'finished' | 'in_progress'>('all')
  const [sortBy, setSortBy] = useState<'date_asc' | 'date_desc' | 'participants_desc' | 'solved_desc'>('date_desc')

  const filteredBattles = useMemo(() => {
    let data = (analytics?.battles ?? []).slice()

    if (statusFilter !== 'all') {
      data = data.filter((battle) => battle.status === statusFilter)
    }

    if (search.trim().length > 0) {
      const query = search.trim().toLowerCase()
      data = data.filter((battle) => battle.title.toLowerCase().includes(query))
    }

    data.sort((left, right) => sortOrganizerBattles(left, right, sortBy))
    return data
  }, [analytics?.battles, search, sortBy, statusFilter])

  if (!analytics) return null

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 py-8">
      <div className="flex items-start justify-between gap-3">
        <div>
          <Typography variant="h1">Аналитика организатора</Typography>
          <Typography className="mt-1" variant="muted">
            Сводка по баттлам, где вы выступали организатором
          </Typography>
        </div>

        <Button asChild variant="outline">
          <Link to="/profile">
            <ArrowLeft className="size-4" />
            Назад
          </Link>
        </Button>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <Metric label="Баттлов" value={String(analytics.organized_battles_count)} />
        <Metric label="Ср. участников" value={String(analytics.average_participants)} />
        <Metric
          label="Ср. решаемость"
          value={`${analytics.average_solved_percent}%`}
        />
        <Metric
          label="Hint usage"
          value={`${analytics.hint_usage_share}%`}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Дополнительные метрики</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-3 text-sm">
          <MetricLine
            label="Ср. отправок на задачу"
            value={String(analytics.average_submissions_per_task)}
          />
          <MetricLine
            label="Ср. длительность баттла"
            value={
              analytics.average_battle_duration_seconds != null
                ? formatDuration(Math.round(analytics.average_battle_duration_seconds))
                : 'N/A'
            }
          />
          <MetricLine
            label="Доля завершений по таймеру"
            value={`${analytics.finish_by_timer_share}%`}
          />
          <MetricLine
            label="Доля досрочных завершений"
            value={`${analytics.finish_early_share}%`}
          />
          <MetricLine
            label="Retention"
            value={`${analytics.retention_percent}%`}
          />
          <MetricLine
            label="Разброс уровня"
            value={
              analytics.average_skill_spread != null
                ? String(analytics.average_skill_spread)
                : 'N/A'
            }
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Частота языков</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {analytics.language_frequencies.length === 0 && (
            <Typography variant="muted">Нет данных</Typography>
          )}
          {analytics.language_frequencies.map((languageItem) => (
            <Badge key={languageItem.key} variant="outline">
              {languageItem.key}: {languageItem.count}
            </Badge>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Баттлы организатора</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="grid grid-cols-3 gap-2">
            <Input
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Поиск по названию"
              value={search}
            />
            <select
              className="h-10 rounded-md border bg-background px-3 text-sm"
              onChange={(event) =>
                setStatusFilter(event.target.value as 'all' | 'finished' | 'in_progress')
              }
              value={statusFilter}
            >
              <option value="all">Все статусы</option>
              <option value="finished">Завершенные</option>
              <option value="in_progress">В процессе</option>
            </select>
            <select
              className="h-10 rounded-md border bg-background px-3 text-sm"
              onChange={(event) =>
                setSortBy(
                  event.target.value as
                    | 'date_asc'
                    | 'date_desc'
                    | 'participants_desc'
                    | 'solved_desc',
                )
              }
              value={sortBy}
            >
              <option value="date_desc">Сначала новые</option>
              <option value="date_asc">Сначала старые</option>
              <option value="participants_desc">По участникам</option>
              <option value="solved_desc">По решенным задачам</option>
            </select>
          </div>

          {filteredBattles.length === 0 && (
            <Typography variant="muted">Баттлы не найдены</Typography>
          )}
          {filteredBattles.map((battle) => (
            <div className="flex items-center justify-between rounded-lg border p-3" key={battle.id}>
              <div>
                <Typography className="font-semibold" variant="h3">
                  {battle.title}
                </Typography>
                <Typography variant="muted">
                  {battle.date} • участников: {battle.participants} • решено:{' '}
                  {battle.solved_tasks}/{battle.total_tasks}
                </Typography>
              </div>

              <Link
                className="text-sm text-primary underline"
                params={{ battleId: battle.id }}
                to="/battle-analytics/$battleId"
              >
                Дашборд баттла
              </Link>
            </div>
          ))}
        </CardContent>
      </Card>
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

function sortOrganizerBattles(
  left: BattleListItem,
  right: BattleListItem,
  sortBy: 'date_asc' | 'date_desc' | 'participants_desc' | 'solved_desc',
) {
  if (sortBy === 'date_asc') return left.date.localeCompare(right.date)
  if (sortBy === 'date_desc') return right.date.localeCompare(left.date)

  if (sortBy === 'participants_desc') {
    if (right.participants !== left.participants) {
      return right.participants - left.participants
    }
    return right.date.localeCompare(left.date)
  }

  if (right.solved_tasks !== left.solved_tasks) {
    return right.solved_tasks - left.solved_tasks
  }
  return right.date.localeCompare(left.date)
}
