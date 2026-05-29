import { $api } from '../query-client'

export function roomQueryOptions(roomId: string) {
  return $api.queryOptions(
    'get',
    '/api/rooms/{room_id}',
    {
      params: {
        path: {
          room_id: roomId,
        },
      },
    },
    {
      retry: false,
    },
  )
}

export function useCreateRoom() {
  return $api.useMutation('post', '/api/rooms')
}

export function useJoinRoom() {
  return $api.useMutation('post', '/api/rooms/join')
}

export function useRoomQuery(roomId: string) {
  return $api.useQuery(
    'get',
    '/api/rooms/{room_id}',
    {
      params: {
        path: {
          room_id: roomId,
        },
      },
    },
    {
      retry: false,
    },
  )
}
