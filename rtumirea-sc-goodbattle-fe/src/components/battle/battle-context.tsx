import { createContext, use } from 'react'

import type {
  BattleStatus,
  BattleTask,
  Participant,
  Role,
  TestResult,
} from '@/lib/battle-types'

type BattleContextValue = {
  aiHintRemaining: null | number
  aiMessages: {
    id: string
    role: 'assistant' | 'user'
    text: string
  }[]
  currentParticipantId?: string
  currentTask: BattleTask
  currentTaskIndex: number
  currentTaskSolvedParticipantIds: string[]
  isAiChatOpen: boolean
  isAiHintPending: boolean
  isCurrentTaskSolvedByCurrentUser: boolean
  isRunningCode: boolean
  languageNameByCode: Record<string, string>
  languages: string[]
  nextTaskTitle?: string
  onAskAiHint: (question: string) => void
  onCodeChange: (participantId: string, code: string) => void
  onFinish: () => void
  onLanguageChange: (language: string) => void
  onNextTask: () => void
  onOpenAiChat: () => void
  onPause: () => void
  onRunCode: () => void
  onSelectParticipantEditor: () => void
  onStart: () => void
  onTimerEnd: () => void
  participants: Participant[]
  participantsRating: {
    participantId: string
    place: number
    solvedTasksCount: number
    userId: string
    username: string
  }[]
  remainingSeconds: number
  role: Role
  roomCode: string
  status: BattleStatus
  testResults: null | TestResult[]
  timeLimit: number
  totalTasks: number
}

const BattleContext = createContext<BattleContextValue | null>(null)

function useBattle() {
  const ctx = use(BattleContext)
  if (!ctx) {
    throw new Error('useBattle must be used within BattleProvider')
  }
  return ctx
}

export { BattleContext, useBattle }
export type { BattleContextValue }
