import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'

import { Typography } from '@/components/ui'
import Logo from '@/icons/logo.svg'
import { useAuthStore } from '@/stores/auth-store'

export const Route = createFileRoute('/(auth)')({
  beforeLoad: () => {
    const { user } = useAuthStore.getState()

    if (user) {
      throw redirect({ to: '/' })
    }
  },
  component: AuthLayout,
})

function AuthLayout() {
  return (
    <div className="flex flex-1 items-center justify-center gap-24 px-16">
      <div className="flex flex-col items-center gap-8">
        <Logo className="size-56 drop-shadow-2xl" />
        <div className="text-center">
          <Typography className="text-5xl" variant="h1">
            Good Battle
          </Typography>
          <Typography className="mt-3 text-muted-foreground" variant="large">
            Платформа для организации и проведения соревнований
          </Typography>
        </div>
      </div>

      <Outlet />
    </div>
  )
}
