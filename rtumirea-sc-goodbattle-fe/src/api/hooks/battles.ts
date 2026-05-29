import type { operations } from '../__generated__/schema'

import { $api } from '../query-client'

export function battlesQueryOptions(
  role: NonNullable<
    operations['list_battles_api_battles_get']['parameters']['query']
  >['role'],
) {
  return $api.queryOptions('get', '/api/battles', battlesQueryParams(role), {
    retry: false,
    throwOnError: false,
  })
}

export function useBattlesQuery(
  role: NonNullable<
    operations['list_battles_api_battles_get']['parameters']['query']
  >['role'],
) {
  return $api.useQuery('get', '/api/battles', battlesQueryParams(role), {
    retry: false,
    throwOnError: false,
  })
}

function battlesQueryParams(
  role: NonNullable<
    operations['list_battles_api_battles_get']['parameters']['query']
  >['role'],
) {
  return {
    params: {
      query: {
        role,
      },
    },
  }
}
