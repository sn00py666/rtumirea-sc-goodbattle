import { createFileRoute, Link } from '@tanstack/react-router'
import { BarChart3, Crown, Shield, User } from 'lucide-react'

import { profileQueryOptions, queryClient, useProfileQuery } from '@/api'
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Spinner,
  Typography,
} from '@/components/ui'
import { useAuthStore } from '@/stores/auth-store'

export const Route = createFileRoute('/(app)/analytics')({
  component: AnalyticsHubPage,
  loader: () => queryClient.ensureQueryData(profileQueryOptions()),
  pendingComponent: PagePending,
})

function AnalyticsHubPage() {
  const user = useAuthStore((state) => state.user)
  const profileQuery = useProfileQuery()
  const profile = profileQuery.data

  if (!profile) return null

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 py-8">
      <div>
        <Typography variant="h1">Хаб аналитики</Typography>
        <Typography className="mt-1" variant="muted">
          Выберите раздел аналитики по вашей роли
        </Typography>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <User className="size-5 text-primary" />
              Аналитика участника
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Typography variant="muted">
              Ваша личная статистика как участника баттлов.
            </Typography>
            <Button asChild>
              <Link to="/participant-analytics">Открыть</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Crown className="size-5 text-primary" />
              Аналитика организатора
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Typography variant="muted">
              Статистика по баттлам, которые вы организовали.
            </Typography>
            <Button asChild variant="outline">
              <Link to="/organizer-analytics">Открыть</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Shield className="size-5 text-primary" />
              Админ-аналитика
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Typography variant="muted">
              Платформенные метрики и состояние всей системы.
            </Typography>
            {user?.is_admin ? (
              <Button asChild variant="secondary">
                <Link to="/admin-analytics">Открыть</Link>
              </Button>
            ) : (
              <Typography variant="muted">Доступно только администраторам</Typography>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="flex items-center justify-between pt-0">
          <div>
            <Typography className="font-semibold" variant="h3">
              Быстрый переход
            </Typography>
            <Typography variant="muted">
              К истории баттлов и профилю
            </Typography>
          </div>
          <div className="flex gap-2">
            <Button asChild variant="outline">
              <Link to="/battles">Мои баттлы</Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/profile">
                <BarChart3 className="size-4" />
                Профиль
              </Link>
            </Button>
          </div>
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
