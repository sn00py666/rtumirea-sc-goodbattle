import { $api } from '../query-client'

export function adminPlatformAnalyticsQueryOptions() {
  return $api.queryOptions('get', '/api/analytics/admin/platform', undefined, {
    retry: false,
    throwOnError: false,
  })
}

export function battleAnalyticsQueryOptions(battleId: string) {
  return $api.queryOptions(
    'get',
    '/api/analytics/battles/{battle_id}',
    analyticsBattlePathParams(battleId),
    {
      retry: false,
      throwOnError: false,
    },
  )
}

export function battleMlRiskQueryOptions(battleId: string) {
  return $api.queryOptions(
    'get',
    '/api/analytics/battles/{battle_id}/ml-risk',
    analyticsBattlePathParams(battleId),
    {
      retry: false,
      throwOnError: false,
    },
  )
}

export function organizerAnalyticsQueryOptions() {
  return $api.queryOptions('get', '/api/analytics/organizer/me', undefined, {
    retry: false,
    throwOnError: false,
  })
}

export function participantAnalyticsQueryOptions() {
  return $api.queryOptions('get', '/api/analytics/participants/me', undefined, {
    retry: false,
    throwOnError: false,
  })
}

export function participantPublicAnalyticsQueryOptions(userId: string) {
  return $api.queryOptions(
    'get',
    '/api/analytics/participants/{user_id}',
    analyticsUserPathParams(userId),
    {
      retry: false,
      throwOnError: false,
    },
  )
}

export function useAdminPlatformAnalyticsQuery() {
  return $api.useQuery('get', '/api/analytics/admin/platform', undefined, {
    retry: false,
    throwOnError: false,
  })
}

export function useBattleAnalyticsQuery(battleId: string) {
  return $api.useQuery(
    'get',
    '/api/analytics/battles/{battle_id}',
    analyticsBattlePathParams(battleId),
    {
      retry: false,
      throwOnError: false,
    },
  )
}

export function useBattleMlRiskQuery(battleId: string) {
  return $api.useQuery(
    'get',
    '/api/analytics/battles/{battle_id}/ml-risk',
    analyticsBattlePathParams(battleId),
    {
      retry: false,
      throwOnError: false,
    },
  )
}

export function useOrganizerAnalyticsQuery() {
  return $api.useQuery('get', '/api/analytics/organizer/me', undefined, {
    retry: false,
    throwOnError: false,
  })
}

export function useParticipantAnalyticsQuery() {
  return $api.useQuery('get', '/api/analytics/participants/me', undefined, {
    retry: false,
    throwOnError: false,
  })
}

export function useParticipantPublicAnalyticsQuery(userId: string) {
  return $api.useQuery(
    'get',
    '/api/analytics/participants/{user_id}',
    analyticsUserPathParams(userId),
    {
      retry: false,
      throwOnError: false,
    },
  )
}

function analyticsBattlePathParams(battleId: string) {
  return {
    params: {
      path: {
        battle_id: battleId,
      },
    },
  }
}

function analyticsUserPathParams(userId: string) {
  return {
    params: {
      path: {
        user_id: userId,
      },
    },
  }
}
