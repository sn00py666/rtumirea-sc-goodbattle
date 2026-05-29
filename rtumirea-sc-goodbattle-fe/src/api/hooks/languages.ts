import { $api } from '../query-client'

export function languagesQueryOptions() {
  return $api.queryOptions('get', '/api/languages')
}

export function useLanguagesQuery() {
  return $api.useQuery('get', '/api/languages')
}
