import { createFileRoute, Link } from '@tanstack/react-router'
import {
  Calendar,
  Code2,
  Crown,
  Mail,
  Percent,
  Swords,
  Trophy,
} from 'lucide-react'

import {
  profileQueryOptions,
  queryClient,
  useLanguagesQuery,
  useProfileQuery,
} from '@/api'
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Separator,
  Spinner,
  Typography,
} from '@/components/ui'
import { useAuthStore } from '@/stores/auth-store'

export const Route = createFileRoute('/(app)/profile')({
  component: ProfilePage,
  loader: () => queryClient.ensureQueryData(profileQueryOptions()),
  pendingComponent: PagePending,
})

function PagePending() {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 items-center justify-center py-8">
      <Spinner className="size-6" />
    </div>
  )
}

function ProfilePage() {
  const user = useAuthStore((state) => state.user)
  const languagesQuery = useLanguagesQuery()
  const profileQuery = useProfileQuery()
  const profile = profileQuery.data

  if (!profile) return null

  const joinedDate = new Date(profile.created_at).toLocaleDateString('ru-RU', {
    month: 'long',
    year: 'numeric',
  })

  const topLanguageName =
    languagesQuery.data?.find(
      (language) => language.code === profile.top_language,
    )?.name ??
    profile.top_language ??
    '—'

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 py-8">
      <div>
        <Typography variant="h1">Профиль</Typography>
        <Typography className="mt-1" variant="muted">
          Информация о пользователе и статистика
        </Typography>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Личные данные</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <div className="flex size-14 items-center justify-center rounded-full bg-primary text-2xl font-bold text-primary-foreground">
              {profile.username[0]}
            </div>
            <div>
              <Typography className="font-medium" variant="h3">
                {profile.username}
              </Typography>
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <Mail className="size-3.5" />
                <Typography variant="muted">{profile.email}</Typography>
              </div>
            </div>
          </div>
          <Separator />
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Calendar className="size-3.5" />
            <Typography variant="muted">На платформе с {joinedDate}</Typography>
          </div>
        </CardContent>
      </Card>

      <div>
        <Typography className="mb-3" variant="h2">
          Статистика
        </Typography>
        <div className="grid grid-cols-2 gap-4">
          <StatCard
            icon={<Swords className="size-5" />}
            label="Баттлов сыграно"
            value={String(profile.battles_played)}
          />
          <StatCard
            icon={<Crown className="size-5" />}
            label="Баттлов организовано"
            value={String(profile.battles_organized)}
          />
          <StatCard
            icon={<Trophy className="size-5" />}
            label="Побед"
            value={String(profile.wins_count)}
          />
          <StatCard
            icon={<Percent className="size-5" />}
            label="Процент побед"
            value={`${profile.win_rate}%`}
          />
          <StatCard
            icon={<Code2 className="size-5" />}
            label="Топ язык"
            value={topLanguageName}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Button asChild size="lg" variant="outline">
          <Link to="/battles">Мои баттлы</Link>
        </Button>
        <Button asChild size="lg" variant="outline">
          <Link to="/analytics">Хаб аналитики</Link>
        </Button>
        <Button asChild size="lg" variant="outline">
          <Link to="/participant-analytics">Аналитика участника</Link>
        </Button>
        <Button asChild size="lg" variant="outline">
          <Link to="/organizer-analytics">Аналитика организатора</Link>
        </Button>
        {user?.is_admin && (
          <Button asChild size="lg" variant="outline">
            <Link to="/admin-analytics">Админ-аналитика</Link>
          </Button>
        )}
      </div>
    </div>
  )
}

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode
  label: string
  value: string
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 pt-0">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          {icon}
        </div>
        <div>
          <Typography className="font-semibold" variant="h3">
            {value}
          </Typography>
          <Typography variant="muted">{label}</Typography>
        </div>
      </CardContent>
    </Card>
  )
}
