import { create } from 'zustand'

import type { components } from '@/api/__generated__/schema'

type AuthState = {
  isAuthResolved: boolean
  setAuthState: (user: AuthUser | null) => void
  user: AuthUser | null
}

type AuthUser = components['schemas']['UserResponse']

export const useAuthStore = create<AuthState>()((set) => ({
  isAuthResolved: false,
  setAuthState: (user) => set({ isAuthResolved: true, user }),
  user: null,
}))
