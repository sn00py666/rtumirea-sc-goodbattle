import { createRootRoute, Outlet } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools'
import { ViewTransition } from 'react'

import { fetchAuthUser } from '@/api'
import { Header } from '@/components/header'
import { Button, Spinner, Typography } from '@/components/ui'
import { Toaster } from '@/components/ui/sonner'
import Logo from '@/icons/logo.svg'
import { useAuthStore } from '@/stores/auth-store'

export const Route = createRootRoute({
  beforeLoad: async () => {
    const user = await fetchAuthUser()
    useAuthStore.getState().setAuthState(user)
  },
  component: RootLayout,
  errorComponent: RootError,
  pendingComponent: RootPending,
})

function RootError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="flex h-screen w-screen items-center justify-center p-8">
      <div className="flex w-full max-w-lg flex-col gap-4 rounded-xl border p-6">
        <Typography variant="h2">Что-то пошло не так</Typography>
        <Typography variant="muted">{error.message}</Typography>
        <Button onClick={reset} variant="outline">
          Повторить
        </Button>
      </div>
    </div>
  )
}

function RootLayout() {
  return (
    <>
      <div className="flex h-screen w-screen flex-col gap-4 px-4 max-md:hidden">
        <Header />

        <ViewTransition>
          <Outlet />
        </ViewTransition>

        <TanStackRouterDevtools />
      </div>

      <div className="flex h-screen w-screen flex-col items-center justify-center gap-6 p-8 text-center md:hidden">
        <Logo className="size-20" />
        <div className="flex flex-col items-center gap-2">
          <Typography variant="h2">Платформа недоступна</Typography>
          <Typography className="max-w-xs" variant="muted">
            Good Battle можно использовать только в&nbsp;десктопной версии
            браузера. Пожалуйста, откройте сайт на&nbsp;компьютере.
          </Typography>
        </div>
      </div>

      <Toaster />
    </>
  )
}

function RootPending() {
  return (
    <div className="flex h-screen w-screen items-center justify-center">
      <Spinner />
    </div>
  )
}
