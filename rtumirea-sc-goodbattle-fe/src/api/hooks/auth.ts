import { useAuthStore } from '@/stores/auth-store'

import { $api, queryClient } from '../query-client'

export function authMeQueryOptions() {
  return $api.queryOptions('get', '/api/auth/me', undefined, {
    retry: false,
    throwOnError: false,
  })
}

export async function fetchAuthUser() {
  try {
    return await queryClient.fetchQuery(authMeQueryOptions())
  } catch {
    return null
  }
}

export function useAuthMeQuery() {
  return $api.useQuery('get', '/api/auth/me', undefined, {
    retry: false,
    throwOnError: false,
  })
}

export function useLogin() {
  return $api.useMutation('post', '/api/auth/login', {
    onSuccess: (user) => {
      useAuthStore.getState().setAuthState(user)
      queryClient.setQueryData(authMeQueryOptions().queryKey, user)
    },
  })
}

export function useLogout() {
  return $api.useMutation('post', '/api/auth/logout', {
    onSuccess: () => {
      useAuthStore.getState().setAuthState(null)
      queryClient.removeQueries({ queryKey: authMeQueryOptions().queryKey })
      void queryClient.invalidateQueries()
    },
  })
}

export function useRegister() {
  return $api.useMutation('post', '/api/auth/register', {
    onSuccess: (user) => {
      useAuthStore.getState().setAuthState(user)
      queryClient.setQueryData(authMeQueryOptions().queryKey, user)
    },
  })
}
