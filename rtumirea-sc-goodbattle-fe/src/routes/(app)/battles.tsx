import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import {
  Calendar,
  ChevronRight,
  Crown,
  Plus,
  Trophy,
  Users,
} from 'lucide-react'

import type { components } from '@/api/__generated__/schema'

import {
  battlesQueryOptions,
  languagesQueryOptions,
  queryClient,
  useBattlesQuery,
  useLanguagesQuery,
} from '@/api'
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Spinner,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Typography,
} from '@/components/ui'
import { cn } from '@/lib/utils'

type BattleHistoryItem = components['schemas']['BattleHistoryItemResponse']

export const Route = createFileRoute('/(app)/battles')({
  component: BattlesPage,
  loader: async () => {
    await Promise.all([
      queryClient.ensureQueryData(battlesQueryOptions('organizer')),
      queryClient.ensureQueryData(battlesQueryOptions('participant')),
      queryClient.ensureQueryData(languagesQueryOptions()),
    ])
  },
  pendingComponent: PagePending,
})

function BattleCard({
  battle,
  languageNameByCode,
}: {
  battle: BattleHistoryItem
  languageNameByCode: Record<string, string>
}) {
  const navigate = useNavigate()

  const date = new Date(battle.date).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })

  const isInProgress = battle.status !== 'finished'
  const isOrganizer = battle.role === 'organizer'

  function handleClick() {
    if (isInProgress) {
      navigate({ params: { roomId: battle.id }, to: '/rooms/$roomId' })
      return
    }

    navigate({
      params: { battleId: battle.id },
      to: '/battle-analytics/$battleId',
    })
  }

  return (
    <Card
      className={cn('transition-colors hover:bg-muted/50', 'cursor-pointer')}
      onClick={handleClick}
    >
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            {battle.role === 'organizer' ? (
              <Crown className="size-4 text-primary" />
            ) : (
              <Users className="size-4 text-primary" />
            )}
            {battle.title}
          </span>
          <span className="flex items-center gap-2">
            {battle.place != null && (
              <Badge
                variant={
                  battle.place === 1
                    ? 'default'
                    : battle.place <= 3
                      ? 'secondary'
                      : 'outline'
                }
              >
                <Trophy className="size-3" />
                {battle.place} место
              </Badge>
            )}
            {isInProgress && (
              <ChevronRight className="size-4 text-muted-foreground" />
            )}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Calendar className="size-3.5" />
            <Typography variant="muted">{date}</Typography>
          </div>
          <Typography variant="muted">
            {battle.participants} участников
          </Typography>
          {!isOrganizer && (
            <Typography variant="muted">
              {battle.solved_tasks}/{battle.total_tasks} задач
            </Typography>
          )}
          <div className="flex gap-1">
            {battle.languages.map((lang) => (
              <Badge key={lang} variant="outline">
                {languageNameByCode[lang] ?? lang}
              </Badge>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function BattleList({
  battles,
  languageNameByCode,
}: {
  battles: BattleHistoryItem[]
  languageNameByCode: Record<string, string>
}) {
  if (battles.length === 0) {
    return (
      <div className="py-12 text-center">
        <Typography variant="muted">Баттлов пока нет</Typography>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {battles.map((battle) => (
        <BattleCard
          battle={battle}
          key={battle.id}
          languageNameByCode={languageNameByCode}
        />
      ))}
    </div>
  )
}

function BattlesPage() {
  const languagesQuery = useLanguagesQuery()
  const participantBattlesQuery = useBattlesQuery('participant')
  const organizerBattlesQuery = useBattlesQuery('organizer')

  const languageNameByCode = Object.fromEntries(
    (languagesQuery.data ?? []).map((language) => [
      language.code,
      language.name,
    ]),
  )

  const participantBattles = participantBattlesQuery.data ?? []
  const organizerBattles = organizerBattlesQuery.data ?? []

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 py-8">
      <div className="flex justify-between">
        <div>
          <Typography variant="h1">Мои баттлы</Typography>
          <Typography className="mt-1" variant="muted">
            История ваших соревнований
          </Typography>
        </div>

        <Button asChild variant="secondary">
          <Link to="/">
            <Plus /> Новый
          </Link>
        </Button>
      </div>

      <Tabs defaultValue="organizer">
        <TabsList>
          <TabsTrigger value="organizer">
            <Crown className="size-4" />
            Организатор ({organizerBattles.length})
          </TabsTrigger>
          <TabsTrigger value="participant">
            <Users className="size-4" />
            Участник ({participantBattles.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="participant">
          <BattleList
            battles={participantBattles}
            languageNameByCode={languageNameByCode}
          />
        </TabsContent>
        <TabsContent value="organizer">
          <BattleList
            battles={organizerBattles}
            languageNameByCode={languageNameByCode}
          />
        </TabsContent>
      </Tabs>
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
