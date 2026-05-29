import { QueryClient } from '@tanstack/react-query'
import createFetchClient from 'openapi-react-query'
import { toast } from 'sonner'

import { fetchClient } from './client'

export const $api = createFetchClient(fetchClient)

export function getErrorMessage(error: unknown): string {
  if (
    error &&
    typeof error === 'object' &&
    'detail' in error &&
    typeof (error as { detail: string }).detail === 'string'
  ) {
    return (error as { detail: string }).detail
  }
  if (error instanceof Error) return error.message
  return 'Произошла неизвестная ошибка'
}

export const queryClient = new QueryClient({
  defaultOptions: {
    mutations: {
      onError(err) {
        console.error(err)
        toast.error(getErrorMessage(err))
      },
    },
    queries: {
      refetchOnWindowFocus: true,
      retry: 3,
      staleTime: 30_000,
      throwOnError: true,
    },
  },
})
