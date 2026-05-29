import { Link, useLocation, useNavigate } from '@tanstack/react-router'
import { BarChart3, LogOut, Swords, User } from 'lucide-react'
import { ViewTransition } from 'react'

import { useLogout } from '@/api'
import Logo from '@/icons/logo.svg'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth-store'

import { Button, Spinner, Typography } from './ui'

function Header() {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const isAuthResolved = useAuthStore((state) => state.isAuthResolved)
  const user = useAuthStore((state) => state.user)

  const logout = useLogout()

  async function handleLogoutClick() {
    try {
      await logout.mutateAsync({})
      void navigate({ to: '/login' })
    } catch {
      return
    }
  }

  const compact = pathname.startsWith('/rooms/')

  return (
    <header
      className={cn(
        'sticky top-0 z-50 flex shrink-0 items-center justify-between overflow-hidden bg-background px-4 transition-all duration-300',
        compact ? 'h-10 pt-2' : 'h-16 pt-4',
      )}
    >
      <Link
        className={cn(
          'flex items-center transition-all duration-300 select-none',
          compact ? 'gap-3' : 'gap-2',
        )}
        tabIndex={-1}
        to="/"
      >
        <Logo
          className={cn(
            'transition-all duration-300',
            compact ? 'size-6' : 'size-8',
          )}
        />
        <Typography
          as="span"
          className={compact ? 'text-md' : ''}
          variant="large"
        >
          good battle
        </Typography>
      </Link>

      {isAuthResolved && user && (
        <ViewTransition>
          {compact ? (
            <div className="flex items-center gap-1" key="compact">
              <Button asChild size="sm" variant="ghost">
                <Link to="/profile">
                  <User className="size-3.5" />
                  {user.username}
                </Link>
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2" key="full">
              <Button asChild size="lg" variant="ghost">
                <Link to="/battles">
                  <Swords />
                  Мои баттлы
                </Link>
              </Button>
              <Button asChild size="lg" variant="ghost">
                <Link to="/analytics">
                  <BarChart3 />
                  Хаб аналитики
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link to="/profile">
                  <User />
                  {user.username}
                </Link>
              </Button>
              <Button
                disabled={logout.isPending}
                onClick={handleLogoutClick}
                size="lg"
                variant="destructive"
              >
                {logout.isPending && <Spinner />}
                <LogOut />
                Выйти
              </Button>
            </div>
          )}
        </ViewTransition>
      )}
    </header>
  )
}

export { Header }
