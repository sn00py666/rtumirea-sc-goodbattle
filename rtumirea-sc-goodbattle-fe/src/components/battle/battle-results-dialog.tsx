import { Trophy } from 'lucide-react'

import type { BattleResult } from '@/lib/battle-types'

import {
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Separator,
  Typography,
} from '@/components/ui'

function BattleResultsDialog({
  onClose,
  open,
  results,
}: {
  onClose: () => void
  open: boolean
  results: BattleResult[]
}) {
  return (
    <Dialog open={open}>
      <DialogContent className="sm:max-w-md" showCloseButton={false}>
        <DialogHeader className="items-center">
          <Trophy className="size-8 text-muted-foreground" />
          <DialogTitle className="text-center text-lg">
            Результаты баттла
          </DialogTitle>
        </DialogHeader>

        <Separator />

        <div className="flex flex-col gap-3">
          {results.length === 0 ? (
            <Typography className="text-center" variant="muted">
              Победителей нет: время вышло
            </Typography>
          ) : (
            results.map((r) => (
              <div
                className="flex items-center gap-3 rounded-lg border p-3"
                key={r.participantId}
              >
                <span className="text-xl font-bold text-muted-foreground tabular-nums">
                  #{r.place}
                </span>
                <div className="flex flex-1 flex-col gap-1">
                  <Typography className="font-medium" variant="body">
                    {r.username}
                  </Typography>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">
                      {r.solvedTasks}/{r.totalTasks} задач
                    </Badge>
                    <Typography variant="muted">{r.totalTime}</Typography>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        <DialogFooter>
          <Button className="w-full" onClick={onClose}>
            Закрыть
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export { BattleResultsDialog }
