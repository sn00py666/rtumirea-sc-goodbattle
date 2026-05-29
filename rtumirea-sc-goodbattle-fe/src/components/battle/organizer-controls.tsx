import { Flag, Pause, Play, SkipForward } from 'lucide-react'

import { Button } from '@/components/ui'

import { useBattle } from './battle-context'

function OrganizerControls() {
  const {
    currentTaskIndex,
    onFinish,
    onNextTask,
    onPause,
    onStart,
    participants,
    status,
    totalTasks,
  } = useBattle()

  const isLastTask = currentTaskIndex >= totalTasks - 1

  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-2">
        {status === 'running' ? (
          <Button className="flex-1" onClick={onPause} variant="outline">
            <Pause className="size-4" />
            Пауза
          </Button>
        ) : (
          <Button
            className="flex-1"
            disabled={status === 'finished' || participants.length === 0}
            onClick={onStart}
          >
            <Play className="size-4" />
            {status === 'paused' ? 'Продолжить' : 'Старт'}
          </Button>
        )}
        <Button
          disabled={isLastTask || status === 'waiting'}
          onClick={onNextTask}
          variant="outline"
        >
          <SkipForward className="size-4" />
          След. задача
        </Button>
      </div>
      <Button
        disabled={status === 'waiting'}
        onClick={onFinish}
        variant="destructive"
      >
        <Flag className="size-4" />
        Завершить
      </Button>
    </div>
  )
}

export { OrganizerControls }
