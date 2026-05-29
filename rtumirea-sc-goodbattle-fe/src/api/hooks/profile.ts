import { $api } from '../query-client'

export function profileQueryOptions() {
  return $api.queryOptions('get', '/api/profile', undefined, {
    retry: false,
    throwOnError: false,
  })
}

export function useProfileQuery() {
  return $api.useQuery('get', '/api/profile', undefined, {
    retry: false,
    throwOnError: false,
  })
}
