import { CheckCircle, Loader2, Play, XCircle } from 'lucide-react'

import type { Participant } from '@/lib/battle-types'

import {
  Badge,
  Button,
  Card,
  CardContent,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Typography,
} from '@/components/ui'
import { cn } from '@/lib/utils'

import { useBattle } from './battle-context'
import { CodeEditor } from './code-editor'

function ParticipantEditor({
  isCurrentUser = false,
  participant,
}: {
  isCurrentUser?: boolean
  participant: Participant
}) {
  const {
    currentParticipantId,
    currentTaskSolvedParticipantIds,
    isCurrentTaskSolvedByCurrentUser,
    isRunningCode,
    languageNameByCode,
    languages,
    onCodeChange,
    onLanguageChange,
    onRunCode,
    status,
    testResults,
  } = useBattle()

  const isCurrentTaskSolvedByParticipant =
    currentTaskSolvedParticipantIds.includes(participant.id)

  return (
    <Card
      className={cn(
        'flex h-full flex-col overflow-hidden',
        isCurrentUser && 'border-primary',
      )}
    >
      <div className="flex shrink-0 flex-row items-center gap-2 px-4 py-2">
        <Typography className="shrink-0 font-medium" variant="small">
          {participant.username}
        </Typography>
        {isCurrentUser && (
          <Typography
            className="shrink-0 text-muted-foreground"
            variant="small"
          >
            (вы)
          </Typography>
        )}
        <div className="flex-1" />
        {isCurrentUser ? (
          <>
            {isCurrentTaskSolvedByParticipant && (
              <Badge
                className="bg-green-500/15 text-green-700 dark:text-green-400"
                variant="secondary"
              >
                Решено
              </Badge>
            )}
            <Select
              disabled={isCurrentTaskSolvedByCurrentUser}
              onValueChange={onLanguageChange}
              value={participant.language}
            >
              <SelectTrigger className="h-7 w-auto gap-1 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {languages.map((lang) => (
                  <SelectItem key={lang} value={lang}>
                    {languageNameByCode[lang] ?? lang}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              disabled={
                isCurrentTaskSolvedByCurrentUser ||
                isRunningCode ||
                status !== 'running'
              }
              onClick={onRunCode}
              size="sm"
              variant="outline"
            >
              {isRunningCode ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Play className="size-3.5" />
              )}
              {isRunningCode ? 'Выполняется...' : 'Запустить'}
            </Button>
          </>
        ) : (
          <>
            {isCurrentTaskSolvedByParticipant && (
              <Badge
                className="bg-green-500/15 text-green-700 dark:text-green-400"
                variant="secondary"
              >
                Решено
              </Badge>
            )}
            <Badge variant="secondary">
              {languageNameByCode[participant.language] ?? participant.language}
            </Badge>
          </>
        )}
      </div>

      <CardContent className="min-h-0 flex-1 overflow-auto p-0">
        <div
          className={cn(
            'h-full',
            !isCurrentUser &&
              isCurrentTaskSolvedByParticipant &&
              // проверка на не-организатора
              currentParticipantId &&
              'blur-sm',
          )}
        >
          <CodeEditor
            code={participant.code}
            language={participant.language}
            onChange={
              isCurrentUser
                ? (code) => onCodeChange(participant.id, code)
                : undefined
            }
            readOnly={
              !isCurrentUser ||
              status !== 'running' ||
              isCurrentTaskSolvedByCurrentUser
            }
          />
        </div>
      </CardContent>

      {isCurrentUser && testResults && (
        <div className="flex max-h-40 shrink-0 flex-col border-t p-2">
          <div className="flex flex-col gap-1 overflow-y-auto font-mono text-xs">
            {testResults.map((r, i) => (
              <div
                className={cn(
                  'flex items-start gap-1.5 rounded px-2 py-1',
                  r.passed
                    ? 'bg-green-500/10 text-green-700 dark:text-green-400'
                    : 'bg-red-500/10 text-red-700 dark:text-red-400',
                )}
                key={i}
              >
                {(() => {
                  const actualValue = r.actual ?? ''
                  const detailValue =
                    r.log?.stderr?.trim() ||
                    r.actual?.trim() ||
                    r.log?.stdout?.trim() ||
                    ''
                  const expectedValue = r.expected ?? ''

                  return (
                    <>
                      {r.passed ? (
                        <CheckCircle className="mt-0.5 size-3 shrink-0" />
                      ) : (
                        <XCircle className="mt-0.5 size-3 shrink-0" />
                      )}
                      <div>
                        <span className="text-muted-foreground">
                          Тест {i + 1}:
                        </span>{' '}
                        {r.passed ? (
                          'OK'
                        ) : (
                          <>
                            {r.error && (
                              <span className="text-destructive-foreground">
                                {r.error.toUpperCase()}
                              </span>
                            )}

                            {r.error === 'wrong_answer' && (
                              <>
                                <div className="flex items-start gap-1">
                                  <span className="text-muted-foreground">
                                    Ожидалось:
                                  </span>
                                  <span className="break-words">
                                    {expectedValue}
                                  </span>
                                </div>

                                <div className="flex items-start gap-1">
                                  <span className="text-muted-foreground">
                                    Получено:
                                  </span>
                                  <span className="break-words">
                                    {actualValue}
                                  </span>
                                </div>
                              </>
                            )}

                            {r.error !== 'wrong_answer' &&
                              detailValue.length > 0 && (
                                <>
                                  <div className="text-muted-foreground">
                                    Детали:
                                  </div>
                                  <pre className="overflow-x-auto break-words whitespace-pre-wrap text-current">
                                    {detailValue}
                                  </pre>
                                </>
                              )}

                            {r.error !== 'wrong_answer' &&
                              r.log?.exit_code !== null && (
                                <div className="text-muted-foreground">
                                  Exit code: {r.log?.exit_code}
                                </div>
                              )}
                          </>
                        )}
                      </div>
                    </>
                  )
                })()}
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  )
}

export { ParticipantEditor }
