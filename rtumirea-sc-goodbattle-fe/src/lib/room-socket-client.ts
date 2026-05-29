import type { BattleStatus, Role, TestResult } from '@/lib/battle-types'

type RoomSocketClientMessage<T extends RoomSocketClientMessageType> = {
  data: RoomSocketClientMessageMap[T]
  type: T
}

type RoomSocketClientMessageMap = {
  ask_ai_hint: {
    question: string
    task_id: string
  }
  code_update: {
    code: string
  }
  finish_battle: Record<string, never>
  language_change: {
    language: string
  }
  next_task: Record<string, never>
  pause_battle: Record<string, never>
  run_code: {
    code: string
    language: string
    task_id: string
  }
  start_battle: Record<string, never>
}

type RoomSocketClientMessageType = keyof RoomSocketClientMessageMap

type RoomSocketServerMessage<T extends RoomSocketServerMessageType> = {
  data: RoomSocketServerMessageMap[T]
  type: T
}

type RoomSocketServerMessageMap = {
  ai_hint_chunk: {
    delta: string
  }
  ai_hint_result: {
    hint: string
    remaining: number
    task_id: string
  }
  ai_hint_started: {
    task_id: string
  }
  battle_finished: {
    results: {
      id: string
      place: number
      solved_tasks: number
      total_tasks: number
      total_time: number
      user_id: string
      username: string
    }[]
  }
  code_update: {
    code: string
    id: string
    user_id: string
  }
  error: {
    detail: string
    status: number
  }
  language_change: {
    id: string
    language: string
    user_id: string
  }
  next_task: {
    currentTaskIndex: number
  }
  participant_joined: {
    id: string
    language: string
    role: Role
    user_id: string
    username: string
  }
  participant_left: {
    id: string
    user_id: string
  }
  participant_task_solved: {
    participant_id: string
    solved_task_ids: string[]
    task_id: string
    user_id: string
  }
  run_code_result: {
    results: TestResult[]
    task_id: string
  }
  status_change: {
    status: BattleStatus
  }
}

type RoomSocketServerMessageType = keyof RoomSocketServerMessageMap

type RoomSocketServerMessageUnion = {
  [K in RoomSocketServerMessageType]: RoomSocketServerMessage<K>
}[RoomSocketServerMessageType]

let roomSocket: null | WebSocket = null
let roomSocketRoomId: null | string = null
let skipRoomSocketCloseNotification = false

const roomSocketDisconnectListeners = new Set<(error: Error) => void>()
const roomSocketMessageListeners = new Set<
  (message: RoomSocketServerMessageUnion) => void
>()

const ROOM_SOCKET_CONNECT_TIMEOUT_MS = 5000

export async function connectRoomSocket(roomId: string) {
  if (
    roomSocket &&
    roomSocketRoomId === roomId &&
    roomSocket.readyState === WebSocket.OPEN
  ) {
    return roomSocket
  }

  if (
    roomSocket &&
    roomSocketRoomId === roomId &&
    roomSocket.readyState === WebSocket.CONNECTING
  ) {
    await waitForSocketOpen(roomSocket)

    return roomSocket
  }

  disconnectRoomSocket()

  roomSocketRoomId = roomId
  roomSocket = new WebSocket(createRoomSocketUrl(roomId))
  const currentSocket = roomSocket

  currentSocket.addEventListener('close', () => {
    if (roomSocket !== currentSocket) {
      return
    }

    roomSocket = null
    roomSocketRoomId = null

    if (skipRoomSocketCloseNotification) {
      skipRoomSocketCloseNotification = false

      return
    }

    notifyRoomSocketDisconnect(new Error('Room socket disconnected'))
  })

  currentSocket.addEventListener('error', () => {
    if (roomSocket !== currentSocket) {
      return
    }

    notifyRoomSocketDisconnect(new Error('Room socket connection failed'))
  })

  currentSocket.addEventListener('message', (event) => {
    const message = parseServerMessage(event.data)

    if (!message) {
      return
    }

    roomSocketMessageListeners.forEach((listener) => {
      listener(message)
    })
  })

  try {
    await waitForSocketOpen(currentSocket)

    return currentSocket
  } catch (error) {
    if (roomSocket === currentSocket) {
      disconnectRoomSocket()
    }

    throw error
  }
}

export function disconnectRoomSocket() {
  if (!roomSocket) {
    roomSocketRoomId = null

    return
  }

  if (
    roomSocket.readyState === WebSocket.CONNECTING ||
    roomSocket.readyState === WebSocket.OPEN
  ) {
    skipRoomSocketCloseNotification = true
    roomSocket.close(1000, 'Leaving room')
  }

  roomSocket = null
  roomSocketRoomId = null
}

export function onRoomSocketDisconnect(listener: (error: Error) => void) {
  roomSocketDisconnectListeners.add(listener)

  return () => {
    roomSocketDisconnectListeners.delete(listener)
  }
}

export function onRoomSocketMessage(
  listener: (message: RoomSocketServerMessageUnion) => void,
) {
  roomSocketMessageListeners.add(listener)

  return () => {
    roomSocketMessageListeners.delete(listener)
  }
}

export function sendRoomSocketMessage<T extends RoomSocketClientMessageType>(
  message: RoomSocketClientMessage<T>,
) {
  if (!roomSocket || roomSocket.readyState !== WebSocket.OPEN) {
    return false
  }

  roomSocket.send(JSON.stringify(message))

  return true
}

function createRoomSocketUrl(roomId: string) {
  const apiUrl = new URL(import.meta.env.VITE_API_URL)

  apiUrl.hash = ''
  apiUrl.pathname = `/ws/rooms/${encodeURIComponent(roomId)}`
  apiUrl.search = ''
  apiUrl.protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'

  return apiUrl.toString()
}

function isRoomSocketServerMessageType(
  value: unknown,
): value is RoomSocketServerMessageType {
  return (
    value === 'ai_hint_chunk' ||
    value === 'ai_hint_result' ||
    value === 'ai_hint_started' ||
    value === 'battle_finished' ||
    value === 'code_update' ||
    value === 'error' ||
    value === 'language_change' ||
    value === 'next_task' ||
    value === 'participant_joined' ||
    value === 'participant_left' ||
    value === 'participant_task_solved' ||
    value === 'run_code_result' ||
    value === 'status_change'
  )
}

function notifyRoomSocketDisconnect(error: Error) {
  roomSocketDisconnectListeners.forEach((listener) => {
    listener(error)
  })
}

function parseServerMessage(
  data: unknown,
): null | RoomSocketServerMessageUnion {
  if (typeof data !== 'string') {
    return null
  }

  try {
    const parsed = JSON.parse(data) as {
      data?: unknown
      type?: unknown
    }

    if (!isRoomSocketServerMessageType(parsed.type)) {
      return null
    }

    const payload = (parsed.data ?? {}) as unknown

    switch (parsed.type) {
      case 'ai_hint_chunk':
        return {
          data: payload as RoomSocketServerMessageMap['ai_hint_chunk'],
          type: 'ai_hint_chunk',
        }
      case 'ai_hint_result':
        return {
          data: payload as RoomSocketServerMessageMap['ai_hint_result'],
          type: 'ai_hint_result',
        }
      case 'ai_hint_started':
        return {
          data: payload as RoomSocketServerMessageMap['ai_hint_started'],
          type: 'ai_hint_started',
        }
      case 'battle_finished':
        return {
          data: payload as RoomSocketServerMessageMap['battle_finished'],
          type: 'battle_finished',
        }
      case 'code_update':
        return {
          data: payload as RoomSocketServerMessageMap['code_update'],
          type: 'code_update',
        }
      case 'error':
        return {
          data: payload as RoomSocketServerMessageMap['error'],
          type: 'error',
        }
      case 'language_change':
        return {
          data: payload as RoomSocketServerMessageMap['language_change'],
          type: 'language_change',
        }
      case 'next_task':
        return {
          data: payload as RoomSocketServerMessageMap['next_task'],
          type: 'next_task',
        }
      case 'participant_joined':
        return {
          data: payload as RoomSocketServerMessageMap['participant_joined'],
          type: 'participant_joined',
        }
      case 'participant_left':
        return {
          data: payload as RoomSocketServerMessageMap['participant_left'],
          type: 'participant_left',
        }
      case 'participant_task_solved':
        return {
          data: payload as RoomSocketServerMessageMap['participant_task_solved'],
          type: 'participant_task_solved',
        }
      case 'run_code_result':
        return {
          data: payload as RoomSocketServerMessageMap['run_code_result'],
          type: 'run_code_result',
        }
      case 'status_change':
        return {
          data: payload as RoomSocketServerMessageMap['status_change'],
          type: 'status_change',
        }
    }
  } catch {
    return null
  }
}

function waitForSocketOpen(socket: WebSocket) {
  return new Promise<void>((resolve, reject) => {
    if (socket.readyState === WebSocket.OPEN) {
      resolve()

      return
    }

    const timeout = window.setTimeout(() => {
      cleanup()
      reject(new Error('Room socket connection timeout'))
    }, ROOM_SOCKET_CONNECT_TIMEOUT_MS)

    function cleanup() {
      window.clearTimeout(timeout)
      socket.removeEventListener('close', handleClose)
      socket.removeEventListener('error', handleError)
      socket.removeEventListener('open', handleOpen)
    }

    function handleClose(event: CloseEvent) {
      cleanup()
      reject(new Error(`Room socket closed: ${event.code}`))
    }

    function handleError() {
      cleanup()
      reject(new Error('Room socket connection failed'))
    }

    function handleOpen() {
      cleanup()
      resolve()
    }

    socket.addEventListener('close', handleClose)
    socket.addEventListener('error', handleError)
    socket.addEventListener('open', handleOpen)
  })
}

export type { RoomSocketServerMessageUnion }
