import type { ChangeEvent, KeyboardEvent } from 'react'

import { Loader2, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import remarkGfm from 'remark-gfm'

import { Button, Input, Typography } from '@/components/ui'

import { useBattle } from './battle-context'

const MAX_AI_MESSAGE_LENGTH = 100
const AI_LOADING_STEPS = [
  'Подготавливаем контейнер...',
  'Тестируем решение...',
  'Собираем контекст...',
  'Спрашиваем LLM...',
  'Формулируем подсказку...',
]

function AiChatPanel() {
  const {
    aiHintRemaining,
    aiMessages,
    isAiHintPending,
    onAskAiHint,
    onOpenAiChat,
  } = useBattle()

  const [prompt, setPrompt] = useState('')
  const [loadingStepIndex, setLoadingStepIndex] = useState(0)

  useEffect(() => {
    if (!isAiHintPending) {
      queueMicrotask(() => setLoadingStepIndex(0))

      return
    }

    const timer = window.setInterval(() => {
      setLoadingStepIndex((prev) => (prev + 1) % AI_LOADING_STEPS.length)
    }, 1300)

    return () => {
      window.clearInterval(timer)
    }
  }, [isAiHintPending])

  function handleAiPromptChange(event: ChangeEvent<HTMLInputElement>) {
    setPrompt(event.target.value.slice(0, MAX_AI_MESSAGE_LENGTH))
  }

  function handleCloseAiChat() {
    onOpenAiChat()
  }

  function handleSubmitAiPrompt() {
    const trimmedPrompt = prompt.trim()

    if (!trimmedPrompt || isAiHintPending) {
      return
    }

    onAskAiHint(trimmedPrompt)
    setPrompt('')
  }

  function handlePromptKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key !== 'Enter') {
      return
    }

    handleSubmitAiPrompt()
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border bg-card">
      <div className="flex items-center gap-2 border-b px-3 py-2">
        <Typography className="flex-1 font-medium" variant="small">
          AI-чат
        </Typography>
        <Button onClick={handleCloseAiChat} size="icon-xs" variant="ghost">
          <X className="size-3.5" />
        </Button>
      </div>
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-3">
        {aiMessages.length === 0 && (
          <Typography className="text-muted-foreground" variant="small">
            Задайте вопрос по текущей задаче. Подсказка доступна один раз на
            задачу.
          </Typography>
        )}
        {aiMessages.map((message, index) => (
          <div
            className={
              message.role === 'user'
                ? 'ml-auto max-w-[90%] rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground'
                : 'max-w-[90%] rounded-lg border bg-muted/40 px-3 py-2'
            }
            key={message.id}
          >
            {message.text.length === 0 &&
              index === aiMessages.length - 1 &&
              isAiHintPending && (
                <Typography
                  className="animate-pulse text-muted-foreground"
                  variant="small"
                >
                  {AI_LOADING_STEPS[loadingStepIndex]}
                </Typography>
              )}
            <ReactMarkdown
              components={{
                code: ({ children, className }) => {
                  const language = className?.replace('language-', '')
                  const codeText = String(children).replace(/\n$/, '')

                  if (!language) {
                    return <code className="font-mono text-xs">{children}</code>
                  }

                  return (
                    <SyntaxHighlighter
                      customStyle={{
                        background: 'transparent',
                        borderRadius: 0,
                        fontSize: '0.75rem',
                        margin: 0,
                        padding: 0,
                      }}
                      language={language}
                      style={oneDark}
                    >
                      {codeText}
                    </SyntaxHighlighter>
                  )
                },
                p: ({ children }) => (
                  <Typography className="whitespace-pre-wrap" variant="small">
                    {children}
                  </Typography>
                ),
                pre: ({ children }) => (
                  <div className="mt-2 overflow-x-auto rounded-md border bg-muted p-2">
                    {children}
                  </div>
                ),
                ul: ({ children }) => (
                  <ul className="list-disc space-y-1 pl-5 text-sm">
                    {children}
                  </ul>
                ),
              }}
              remarkPlugins={[remarkGfm]}
            >
              {message.text}
            </ReactMarkdown>
          </div>
        ))}
      </div>
      <div className="border-t p-3">
        <div className="flex items-center gap-2">
          <Input
            disabled={isAiHintPending || aiHintRemaining === 0}
            maxLength={MAX_AI_MESSAGE_LENGTH}
            onChange={handleAiPromptChange}
            onKeyDown={handlePromptKeyDown}
            placeholder="Напишите сообщение для AI..."
            value={prompt}
          />
          <Button
            disabled={
              isAiHintPending ||
              aiHintRemaining === 0 ||
              prompt.trim().length === 0
            }
            onClick={handleSubmitAiPrompt}
            size="sm"
            variant="default"
          >
            {isAiHintPending && <Loader2 className="size-3.5 animate-spin" />}
            Отправить
          </Button>
        </div>
        <div className="mt-1 flex items-center justify-between gap-2">
          <Typography className="text-muted-foreground" variant="small">
            {aiHintRemaining === 0
              ? 'Лимит подсказки на задачу исчерпан'
              : '1 подсказка на задачу'}
          </Typography>
          <Typography className="text-muted-foreground" variant="small">
            {prompt.length}/{MAX_AI_MESSAGE_LENGTH}
          </Typography>
        </div>
      </div>
    </div>
  )
}

export { AiChatPanel }
