import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'

import { useAuthStore } from '@/stores/auth-store'

export const Route = createFileRoute('/(app)')({
  beforeLoad: async () => {
    const { user } = useAuthStore.getState()

    if (!user) {
      throw redirect({ to: '/login' })
    }
  },
  component: AppLayout,
  pendingMs: 0,
})

function AppLayout() {
  return <Outlet />
}
