import { createFileRoute, Link } from '@tanstack/react-router'
import { ArrowLeft } from 'lucide-react'
import { useMemo, useState } from 'react'

import type { components } from '@/api/__generated__/schema'

import {
  participantAnalyticsQueryOptions,
  queryClient,
  useParticipantAnalyticsQuery,
} from '@/api'
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Spinner,
  Typography,
} from '@/components/ui'
import { Input } from '@/components/ui/input'

type AnalyticsBattle = components['schemas']['AnalyticsBattleListItemResponse']
type HeatmapCell = components['schemas']['AnalyticsHeatmapCellResponse']

export const Route = createFileRoute('/(app)/participant-analytics')({
  component: ParticipantAnalyticsPage,
  loader: () => queryClient.ensureQueryData(participantAnalyticsQueryOptions()),
  pendingComponent: PagePending,
})

function chunkByWeek<T>(items: T[]) {
  const chunks: T[][] = []

  for (let index = 0; index < items.length; index += 7) {
    chunks.push(items.slice(index, index + 7))
  }

  return chunks
}

function ErrorFrequencies({
  frequencies,
}: {
  frequencies: components['schemas']['AnalyticsFrequencyResponse'][]
}) {
  const total = frequencies.reduce((acc, item) => acc + item.count, 0)

  if (frequencies.length === 0) {
    return <Typography variant="muted">Нет данных</Typography>
  }

  return (
    <div className="grid gap-2">
      {frequencies.slice(0, 6).map((item) => {
        const percent =
          total > 0 ? ((item.count / total) * 100).toFixed(1) : '0.0'

        return (
          <div
            className="flex items-center justify-between rounded-md border px-3 py-2"
            key={item.key}
          >
            <Typography className="font-medium" variant="small">
              {item.key}
            </Typography>
            <Typography variant="muted">
              {item.count} ({percent}%)
            </Typography>
          </div>
        )
      })}
    </div>
  )
}

function formatDateForTooltip(dateKey: string) {
  const [year, month, day] = dateKey.split('-').map(Number)
  const date = new Date(year, (month ?? 1) - 1, day ?? 1)
  return date.toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

function Heatmap({ cells }: { cells: HeatmapCell[] }) {
  const lastDays = 84
  const byDate = new Map(cells.map((cell) => [cell.date, cell.count]))
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const startDate = new Date(today)
  startDate.setDate(startDate.getDate() - (lastDays - 1))

  const startWeekday = mondayBasedWeekday(startDate)
  const gridStartDate = new Date(startDate)
  gridStartDate.setDate(gridStartDate.getDate() - startWeekday)

  const endWeekday = mondayBasedWeekday(today)
  const gridEndDate = new Date(today)
  gridEndDate.setDate(gridEndDate.getDate() + (6 - endWeekday))

  const days: Array<{
    count: null | number
    key: string
    label: string
  }> = []

  const currentDate = new Date(gridStartDate)
  while (currentDate <= gridEndDate) {
    const key = toLocalDateKey(currentDate)
    const inRange = currentDate >= startDate && currentDate <= today
    const count = inRange ? (byDate.get(key) ?? 0) : null

    days.push({
      count,
      key,
      label: inRange
        ? `${formatDateForTooltip(key)}: ${count} баттлов`
        : `${formatDateForTooltip(key)}: вне диапазона`,
    })

    currentDate.setDate(currentDate.getDate() + 1)
  }

  const weeks = chunkByWeek(days)

  return (
    <div className="grid gap-3 md:grid-cols-[auto_1fr]">
      <div className="hidden grid-rows-7 gap-1 text-xs text-muted-foreground md:grid">
        {['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'].map((weekday) => (
          <div className="flex h-4 items-center" key={weekday}>
            {weekday}
          </div>
        ))}
      </div>

      <div className="overflow-x-auto">
        <div className="flex min-w-max gap-1">
          {weeks.map((week, weekIndex) => (
            <div
              className="grid grid-rows-7 gap-1"
              key={`${week[0]?.key ?? weekIndex}`}
            >
              {week.map((day) => (
                <div className="group relative h-4 w-4" key={day.key}>
                  <div
                    className={`h-4 w-4 rounded-sm ${heatmapColor(day.count)}`}
                  />
                  {day.count != null && (
                    <div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 w-max -translate-x-1/2 rounded-md border bg-card px-2 py-1 text-[11px] text-card-foreground opacity-0 shadow-sm transition-opacity duration-150 group-hover:opacity-100">
                      {day.label}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      <div className="col-span-full flex items-center gap-3 text-xs text-muted-foreground">
        <span>Интенсивность:</span>
        <div className="flex items-center gap-1">
          <span className="h-3 w-3 rounded-sm bg-muted" />0
        </div>
        <div className="flex items-center gap-1">
          <span className="h-3 w-3 rounded-sm bg-pink-200" />
          1-2
        </div>
        <div className="flex items-center gap-1">
          <span className="h-3 w-3 rounded-sm bg-pink-400" />
          3-5
        </div>
        <div className="flex items-center gap-1">
          <span className="h-3 w-3 rounded-sm bg-pink-600" />
          6+
        </div>
      </div>
    </div>
  )
}

function heatmapColor(count: null | number) {
  if (count == null) return 'bg-transparent'
  if (count <= 0) return 'bg-muted'
  if (count <= 2) return 'bg-pink-200'
  if (count <= 5) return 'bg-pink-400'
  return 'bg-pink-600'
}

function MetricCard({ label, value }: { label: string; value: string }) {
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

function mondayBasedWeekday(date: Date) {
  return (date.getDay() + 6) % 7
}

function PagePending() {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 items-center justify-center py-8">
      <Spinner className="size-6" />
    </div>
  )
}

function ParticipantAnalyticsPage() {
  const analyticsQuery = useParticipantAnalyticsQuery()
  const analytics = analyticsQuery.data

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<
    'all' | 'finished' | 'in_progress'
  >('all')
  const [sortBy, setSortBy] = useState<
    'attempts_desc' | 'date_asc' | 'date_desc' | 'place_asc' | 'solved_desc'
  >('date_desc')

  const filteredBattles = useMemo(() => {
    let data = (analytics?.battles ?? []).slice()

    if (statusFilter !== 'all') {
      data = data.filter((battle) => battle.status === statusFilter)
    }

    if (search.trim().length > 0) {
      const query = search.trim().toLowerCase()
      data = data.filter((battle) => battle.title.toLowerCase().includes(query))
    }

    data.sort((left, right) => sortParticipantBattles(left, right, sortBy))
    return data
  }, [analytics?.battles, search, sortBy, statusFilter])

  if (!analytics) return null

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 py-8">
      <div className="flex items-start justify-between gap-3">
        <div>
          <Typography variant="h1">Аналитика участника</Typography>
          <Typography className="mt-1" variant="muted">
            Ваши результаты как участника баттлов
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
        <MetricCard label="Баттлов" value={String(analytics.battles_count)} />
        <MetricCard label="Win rate" value={`${analytics.win_rate}%`} />
        <MetricCard
          label="Решено задач"
          value={String(analytics.solved_tasks_count)}
        />
        <MetricCard
          label="Ср. попыток на задачу"
          value={String(analytics.average_attempts_per_task)}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Активность по дням</CardTitle>
        </CardHeader>
        <CardContent>
          <Typography className="mb-3" variant="muted">
            1 клетка = 1 день. Наведите курсор, чтобы увидеть дату и число
            баттлов.
          </Typography>
          <Heatmap cells={analytics.heatmap} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Частые типы ошибок</CardTitle>
        </CardHeader>
        <CardContent>
          <ErrorFrequencies frequencies={analytics.error_frequencies} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Баттлы участника</CardTitle>
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
                setStatusFilter(
                  event.target.value as 'all' | 'finished' | 'in_progress',
                )
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
                    | 'attempts_desc'
                    | 'date_asc'
                    | 'date_desc'
                    | 'place_asc'
                    | 'solved_desc',
                )
              }
              value={sortBy}
            >
              <option value="date_desc">Сначала новые</option>
              <option value="date_asc">Сначала старые</option>
              <option value="place_asc">По месту</option>
              <option value="solved_desc">По решенным задачам</option>
              <option value="attempts_desc">По попыткам</option>
            </select>
          </div>

          {filteredBattles.length === 0 && (
            <Typography variant="muted">Баттлы не найдены</Typography>
          )}
          {filteredBattles.map((battle) => (
            <div
              className="flex items-center justify-between rounded-lg border p-3"
              key={battle.id}
            >
              <div>
                <Typography className="font-semibold" variant="h3">
                  {battle.title}
                </Typography>
                <Typography variant="muted">
                  {battle.date} • место: {battle.place ?? '—'} • решено:{' '}
                  {battle.solved_tasks}/{battle.total_tasks} • попыток:{' '}
                  {battle.attempts}
                </Typography>
              </div>

              {battle.status === 'in_progress' ? (
                <Link
                  className="text-sm text-primary underline"
                  params={{ roomId: battle.id }}
                  to="/rooms/$roomId"
                >
                  Перейти
                </Link>
              ) : (
                <Link
                  className="text-sm text-primary underline"
                  params={{ battleId: battle.id }}
                  to="/battle-analytics/$battleId"
                >
                  Дашборд баттла
                </Link>
              )}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

function sortParticipantBattles(
  left: AnalyticsBattle,
  right: AnalyticsBattle,
  sortBy:
    | 'attempts_desc'
    | 'date_asc'
    | 'date_desc'
    | 'place_asc'
    | 'solved_desc',
) {
  if (sortBy === 'date_asc') {
    return left.date.localeCompare(right.date)
  }

  if (sortBy === 'date_desc') {
    return right.date.localeCompare(left.date)
  }

  if (sortBy === 'place_asc') {
    const leftPlace = left.place ?? Number.MAX_SAFE_INTEGER
    const rightPlace = right.place ?? Number.MAX_SAFE_INTEGER
    if (leftPlace !== rightPlace) return leftPlace - rightPlace
    return right.date.localeCompare(left.date)
  }

  if (sortBy === 'solved_desc') {
    if (right.solved_tasks !== left.solved_tasks) {
      return right.solved_tasks - left.solved_tasks
    }
    return right.date.localeCompare(left.date)
  }

  if (right.attempts !== left.attempts) {
    return right.attempts - left.attempts
  }
  return right.date.localeCompare(left.date)
}

function toLocalDateKey(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
