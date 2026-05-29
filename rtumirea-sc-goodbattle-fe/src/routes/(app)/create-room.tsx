import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import {
  ArrowLeft,
  ArrowRight,
  Code2,
  ListChecks,
  Plus,
  Timer,
  Trash2,
} from 'lucide-react'
import { type ChangeEvent, useState } from 'react'

import {
  queryClient,
  tasksQueryOptions,
  useCreateRoom,
  useCreateTask,
  useLanguagesQuery,
  useTasksQuery,
} from '@/api'
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Checkbox,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Label,
  Slider,
  Spinner,
  Textarea,
  Typography,
} from '@/components/ui'

export const Route = createFileRoute('/(app)/create-room')({
  component: CreateRoomPage,
  loader: () => queryClient.ensureQueryData(tasksQueryOptions()),
  pendingComponent: PagePending,
})

type DraftTaskExample = {
  id: string
  input: string
  output: string
}

type DraftTaskTestCase = {
  expectedOutput: string
  id: string
  input: string
  isHidden: boolean
}

function createDraftTaskExample(): DraftTaskExample {
  return {
    id: crypto.randomUUID(),
    input: '',
    output: '',
  }
}

function createDraftTaskTestCase(): DraftTaskTestCase {
  return {
    expectedOutput: '',
    id: crypto.randomUUID(),
    input: '',
    isHidden: true,
  }
}

function CreateRoomPage() {
  const navigate = useNavigate()
  const createTask = useCreateTask()
  const createRoom = useCreateRoom()

  const [createTaskDialogOpen, setCreateTaskDialogOpen] = useState(false)
  const [customTaskDescription, setCustomTaskDescription] = useState('')
  const [customTaskExamples, setCustomTaskExamples] = useState<
    DraftTaskExample[]
  >([])
  const [customTaskMemoryLimitMb, setCustomTaskMemoryLimitMb] = useState('256')
  const [customTaskTestCases, setCustomTaskTestCases] = useState<
    DraftTaskTestCase[]
  >([createDraftTaskTestCase()])
  const [customTaskTimeLimitMs, setCustomTaskTimeLimitMs] = useState('1000')
  const [customTaskTitle, setCustomTaskTitle] = useState('')
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>([])
  const [timeLimit, setTimeLimit] = useState(10)
  const [selectedTasks, setSelectedTasks] = useState<string[]>([])

  const languagesQuery = useLanguagesQuery()
  const tasksQuery = useTasksQuery()

  const customTaskMemoryLimitMbNumber = Number(customTaskMemoryLimitMb)
  const customTaskTimeLimitMsNumber = Number(customTaskTimeLimitMs)

  const preparedTaskExamples = customTaskExamples
    .filter(
      (example) =>
        example.input.trim().length > 0 && example.output.trim().length > 0,
    )
    .map((example) => ({
      input: example.input.trim(),
      output: example.output.trim(),
    }))

  const preparedTaskTestCases = customTaskTestCases
    .filter(
      (testCase) =>
        testCase.expectedOutput.trim().length > 0 &&
        testCase.input.trim().length > 0,
    )
    .map((testCase) => ({
      expected_output: testCase.expectedOutput.trim(),
      input: testCase.input.trim(),
      is_hidden: testCase.isHidden,
    }))

  const hasIncompleteTaskExamples = customTaskExamples.some(
    (example) =>
      example.input.trim().length > 0 !== example.output.trim().length > 0,
  )

  const hasIncompleteTaskTestCases = customTaskTestCases.some(
    (testCase) =>
      testCase.expectedOutput.trim().length > 0 !==
      testCase.input.trim().length > 0,
  )

  const isCreateTaskValid =
    customTaskTitle.trim().length > 0 &&
    customTaskDescription.trim().length > 0 &&
    customTaskTimeLimitMsNumber > 0 &&
    customTaskMemoryLimitMbNumber > 0 &&
    Number.isFinite(customTaskTimeLimitMsNumber) &&
    Number.isFinite(customTaskMemoryLimitMbNumber) &&
    preparedTaskTestCases.length > 0 &&
    !hasIncompleteTaskExamples &&
    !hasIncompleteTaskTestCases &&
    !createTask.isPending

  const isValid =
    selectedLanguages.length > 0 &&
    selectedTasks.length > 0 &&
    !createRoom.isPending

  function toggleLanguage(id: string) {
    setSelectedLanguages((prev) =>
      prev.includes(id) ? prev.filter((l) => l !== id) : [...prev, id],
    )
  }

  function toggleTask(id: string) {
    setSelectedTasks((prev) =>
      prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id],
    )
  }

  function resetCustomTaskForm() {
    setCustomTaskDescription('')
    setCustomTaskExamples([])
    setCustomTaskMemoryLimitMb('256')
    setCustomTaskTestCases([createDraftTaskTestCase()])
    setCustomTaskTimeLimitMs('1000')
    setCustomTaskTitle('')
  }

  function handleCreateTaskDialogOpenChange(open: boolean) {
    if (!open && !createTask.isPending) {
      resetCustomTaskForm()
    }

    setCreateTaskDialogOpen(open)
  }

  function handleCustomTaskDescriptionTextareaChange(
    e: ChangeEvent<HTMLTextAreaElement>,
  ) {
    setCustomTaskDescription(e.target.value)
  }

  function handleCustomTaskExampleInputChange(
    exampleId: string,
    value: string,
  ) {
    setCustomTaskExamples((prev) =>
      prev.map((example) =>
        example.id === exampleId ? { ...example, input: value } : example,
      ),
    )
  }

  function handleCustomTaskExampleOutputChange(
    exampleId: string,
    value: string,
  ) {
    setCustomTaskExamples((prev) =>
      prev.map((example) =>
        example.id === exampleId ? { ...example, output: value } : example,
      ),
    )
  }

  function handleCustomTaskMemoryLimitMbChange(
    e: ChangeEvent<HTMLInputElement>,
  ) {
    setCustomTaskMemoryLimitMb(e.target.value)
  }

  function handleCustomTaskTestCaseExpectedOutputChange(
    testCaseId: string,
    value: string,
  ) {
    setCustomTaskTestCases((prev) =>
      prev.map((testCase) =>
        testCase.id === testCaseId
          ? { ...testCase, expectedOutput: value }
          : testCase,
      ),
    )
  }

  function handleCustomTaskTestCaseHiddenChange(
    testCaseId: string,
    isHidden: boolean,
  ) {
    setCustomTaskTestCases((prev) =>
      prev.map((testCase) =>
        testCase.id === testCaseId ? { ...testCase, isHidden } : testCase,
      ),
    )
  }

  function handleCustomTaskTestCaseInputChange(
    testCaseId: string,
    value: string,
  ) {
    setCustomTaskTestCases((prev) =>
      prev.map((testCase) =>
        testCase.id === testCaseId ? { ...testCase, input: value } : testCase,
      ),
    )
  }

  function handleCustomTaskTimeLimitMsChange(e: ChangeEvent<HTMLInputElement>) {
    setCustomTaskTimeLimitMs(e.target.value)
  }

  function handleCustomTaskTitleChange(e: ChangeEvent<HTMLInputElement>) {
    setCustomTaskTitle(e.target.value)
  }

  function handleOpenCreateTaskDialog() {
    handleCreateTaskDialogOpenChange(true)
  }

  function handleCancelCreateTask() {
    handleCreateTaskDialogOpenChange(false)
  }

  function handleAddCustomTaskExample() {
    setCustomTaskExamples((prev) => [...prev, createDraftTaskExample()])
  }

  function handleAddCustomTaskTestCase() {
    setCustomTaskTestCases((prev) => [...prev, createDraftTaskTestCase()])
  }

  function handleRemoveCustomTaskExample(exampleId: string) {
    setCustomTaskExamples((prev) =>
      prev.filter((example) => example.id !== exampleId),
    )
  }

  function handleRemoveCustomTaskTestCase(testCaseId: string) {
    setCustomTaskTestCases((prev) =>
      prev.filter((testCase) => testCase.id !== testCaseId),
    )
  }

  async function handleCreateTaskSubmit(e: React.FormEvent) {
    e.preventDefault()

    if (!isCreateTaskValid) return

    try {
      const data = await createTask.mutateAsync({
        body: {
          description: customTaskDescription.trim(),
          examples:
            preparedTaskExamples.length > 0 ? preparedTaskExamples : undefined,
          memory_limit_mb: customTaskMemoryLimitMbNumber,
          test_cases: preparedTaskTestCases,
          time_limit_ms: customTaskTimeLimitMsNumber,
          title: customTaskTitle.trim(),
        },
      })

      setSelectedTasks((prev) =>
        prev.includes(data.id) ? prev : [...prev, data.id],
      )
      setCreateTaskDialogOpen(false)
      resetCustomTaskForm()
    } catch {
      return
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    if (!isValid) return

    try {
      const data = await createRoom.mutateAsync({
        body: {
          languages: selectedLanguages,
          task_ids: selectedTasks,
          time_limit: timeLimit,
        },
      })

      void navigate({
        params: { roomId: data.room_id },
        to: '/rooms/$roomId',
      })
    } catch {
      return
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 py-8">
      <div className="flex flex-col gap-1">
        <Button
          asChild
          className="-ml-1 w-fit text-muted-foreground"
          size="sm"
          variant="ghost"
        >
          <Link to="/">
            <ArrowLeft className="size-4" />
            Назад
          </Link>
        </Button>
        <Typography variant="h1">Создание комнаты</Typography>
        <Typography variant="muted">Настройте параметры баттла</Typography>
      </div>

      <form className="flex flex-col gap-6" onSubmit={handleSubmit}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Code2 className="size-5 text-primary" />
              Разрешённые языки
            </CardTitle>
            <CardDescription>
              Выберите языки программирования для баттла
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {!languagesQuery.data && languagesQuery.isPending && <Spinner />}
              {languagesQuery.data?.map((lang) => (
                <Label
                  className="flex items-center gap-2 font-normal"
                  key={lang.id}
                >
                  <Checkbox
                    checked={selectedLanguages.includes(lang.code)}
                    onCheckedChange={() => toggleLanguage(lang.code)}
                  />
                  {lang.name}
                </Label>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Timer className="size-5 text-primary" />
              Лимит времени
            </CardTitle>
            <CardDescription>Время на выполнение всех задач</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-4">
              <Slider
                max={30}
                min={1}
                onValueChange={([v]) => setTimeLimit(v)}
                step={1}
                value={[timeLimit]}
              />
              <div className="flex justify-between">
                <Typography variant="muted">1 мин</Typography>
                <Typography className="font-medium" variant="small">
                  {timeLimit} мин
                </Typography>
                <Typography variant="muted">30 мин</Typography>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <CardTitle className="flex items-center gap-2 text-lg">
                <ListChecks className="size-5 text-primary" />
                Задачи
              </CardTitle>
              <Button
                onClick={handleOpenCreateTaskDialog}
                size="sm"
                type="button"
                variant="outline"
              >
                <Plus className="size-4" />
                Создать
              </Button>
            </div>
            <CardDescription>Выберите задачи для баттла</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-3">
              {!tasksQuery.data && tasksQuery.isPending && <Spinner />}
              {tasksQuery.data?.map((task) => (
                <Label
                  className="flex cursor-pointer items-start gap-3 rounded-lg border p-3 font-normal has-checked:border-primary/50 has-checked:bg-primary/5"
                  key={task.id}
                >
                  <Checkbox
                    checked={selectedTasks.includes(task.id)}
                    className="mt-0.5"
                    onCheckedChange={() => toggleTask(task.id)}
                  />
                  <div>
                    <Typography as="p" className="font-medium" variant="body">
                      {task.title}
                    </Typography>
                    <Typography as="p" variant="muted">
                      {task.description}
                    </Typography>
                  </div>
                </Label>
              ))}
              {tasksQuery.isFetched && tasksQuery.data?.length === 0 && (
                <Typography variant="muted">Список задач пуст</Typography>
              )}
            </div>
          </CardContent>
        </Card>

        <Button className="w-full" disabled={!isValid} size="lg" type="submit">
          {createRoom.isPending && <Spinner />}
          Продолжить
          <ArrowRight />
        </Button>
      </form>

      <Dialog
        onOpenChange={handleCreateTaskDialogOpenChange}
        open={createTaskDialogOpen}
      >
        <DialogContent className="flex max-h-[85vh] flex-col sm:max-w-4xl">
          <DialogHeader>
            <DialogTitle>Создание задачи</DialogTitle>
            <DialogDescription>
              Новая задача сразу появится в списке и будет выбрана автоматически
            </DialogDescription>
          </DialogHeader>

          <form
            className="flex min-h-0 flex-1 flex-col"
            onSubmit={handleCreateTaskSubmit}
          >
            <div className="min-h-0 flex-1 overflow-y-auto pr-4 pb-4 pl-1">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="flex flex-col gap-2 sm:col-span-2">
                  <Label htmlFor="custom-task-title">Название</Label>
                  <Input
                    id="custom-task-title"
                    onChange={handleCustomTaskTitleChange}
                    value={customTaskTitle}
                  />
                </div>

                <div className="flex flex-col gap-2 sm:col-span-2">
                  <Label htmlFor="custom-task-description">Описание</Label>
                  <Textarea
                    className="min-h-28"
                    id="custom-task-description"
                    onChange={handleCustomTaskDescriptionTextareaChange}
                    rows={5}
                    value={customTaskDescription}
                  />
                </div>

                <div className="flex flex-col gap-2">
                  <Label htmlFor="custom-task-time-limit-ms">
                    Лимит времени, мс
                  </Label>
                  <Input
                    id="custom-task-time-limit-ms"
                    min={1}
                    onChange={handleCustomTaskTimeLimitMsChange}
                    type="number"
                    value={customTaskTimeLimitMs}
                  />
                </div>

                <div className="flex flex-col gap-2">
                  <Label htmlFor="custom-task-memory-limit-mb">
                    Лимит памяти, MB
                  </Label>
                  <Input
                    id="custom-task-memory-limit-mb"
                    min={1}
                    onChange={handleCustomTaskMemoryLimitMbChange}
                    type="number"
                    value={customTaskMemoryLimitMb}
                  />
                </div>

                <div className="flex flex-col gap-3 sm:col-span-2">
                  <Typography className="font-medium" variant="small">
                    Примеры
                  </Typography>

                  <div className="flex flex-col gap-3">
                    {customTaskExamples.map((example, index) => (
                      <TaskExampleFields
                        example={example}
                        index={index}
                        key={example.id}
                        onInputChange={handleCustomTaskExampleInputChange}
                        onOutputChange={handleCustomTaskExampleOutputChange}
                        onRemove={handleRemoveCustomTaskExample}
                      />
                    ))}
                    {customTaskExamples.length === 0 && (
                      <Typography variant="muted">
                        Пока нет примеров. Добавьте первый пример ниже
                      </Typography>
                    )}
                  </div>

                  <Button
                    className="w-fit"
                    onClick={handleAddCustomTaskExample}
                    size="sm"
                    type="button"
                    variant="outline"
                  >
                    <Plus className="size-4" />
                    Добавить пример
                  </Button>
                </div>

                <div className="flex flex-col gap-3 sm:col-span-2">
                  <Typography className="font-medium" variant="small">
                    Тест-кейсы
                  </Typography>

                  <div className="flex flex-col gap-3">
                    {customTaskTestCases.map((testCase, index) => (
                      <TaskTestCaseFields
                        canRemove={customTaskTestCases.length > 1}
                        index={index}
                        key={testCase.id}
                        onExpectedOutputChange={
                          handleCustomTaskTestCaseExpectedOutputChange
                        }
                        onHiddenChange={handleCustomTaskTestCaseHiddenChange}
                        onInputChange={handleCustomTaskTestCaseInputChange}
                        onRemove={handleRemoveCustomTaskTestCase}
                        testCase={testCase}
                      />
                    ))}
                  </div>

                  <Button
                    className="w-fit"
                    onClick={handleAddCustomTaskTestCase}
                    size="sm"
                    type="button"
                    variant="outline"
                  >
                    <Plus className="size-4" />
                    Добавить тест-кейс
                  </Button>
                </div>

                {(hasIncompleteTaskExamples || hasIncompleteTaskTestCases) && (
                  <Typography className="sm:col-span-2" variant="muted">
                    Заполните обе части у примеров и тест-кейсов или очистите
                    незаполненные поля
                  </Typography>
                )}
              </div>
            </div>

            <DialogFooter className="shrink-0 border-t pt-4">
              <Button
                onClick={handleCancelCreateTask}
                type="button"
                variant="ghost"
              >
                Отмена
              </Button>
              <Button disabled={!isCreateTaskValid} type="submit">
                {createTask.isPending && <Spinner />}
                Создать задачу
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function PagePending() {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 items-center justify-center py-8">
      <Spinner className="size-6" />
    </div>
  )
}

function TaskExampleFields({
  example,
  index,
  onInputChange,
  onOutputChange,
  onRemove,
}: {
  example: DraftTaskExample
  index: number
  onInputChange: (exampleId: string, value: string) => void
  onOutputChange: (exampleId: string, value: string) => void
  onRemove: (exampleId: string) => void
}) {
  function handleInputChange(e: ChangeEvent<HTMLTextAreaElement>) {
    onInputChange(example.id, e.target.value)
  }

  function handleOutputChange(e: ChangeEvent<HTMLTextAreaElement>) {
    onOutputChange(example.id, e.target.value)
  }

  function handleRemove() {
    onRemove(example.id)
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 px-4">
        <CardTitle className="text-base">Пример {index + 1}</CardTitle>
        <Button
          onClick={handleRemove}
          size="sm"
          type="button"
          variant="destructive"
        >
          <Trash2 className="size-4" />
          Удалить
        </Button>
      </CardHeader>
      <CardContent className="grid gap-3 px-4 pt-0 pb-4 sm:grid-cols-2">
        <div className="flex flex-col gap-2">
          <Label htmlFor={`custom-task-example-input-${example.id}`}>
            Входные данные
          </Label>
          <Textarea
            className="min-h-28"
            id={`custom-task-example-input-${example.id}`}
            onChange={handleInputChange}
            rows={5}
            value={example.input}
          />
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor={`custom-task-example-output-${example.id}`}>
            Выходные данные
          </Label>
          <Textarea
            className="min-h-28"
            id={`custom-task-example-output-${example.id}`}
            onChange={handleOutputChange}
            rows={5}
            value={example.output}
          />
        </div>
      </CardContent>
    </Card>
  )
}

function TaskTestCaseFields({
  canRemove,
  index,
  onExpectedOutputChange,
  onHiddenChange,
  onInputChange,
  onRemove,
  testCase,
}: {
  canRemove: boolean
  index: number
  onExpectedOutputChange: (testCaseId: string, value: string) => void
  onHiddenChange: (testCaseId: string, isHidden: boolean) => void
  onInputChange: (testCaseId: string, value: string) => void
  onRemove: (testCaseId: string) => void
  testCase: DraftTaskTestCase
}) {
  function handleExpectedOutputChange(e: ChangeEvent<HTMLTextAreaElement>) {
    onExpectedOutputChange(testCase.id, e.target.value)
  }

  function handleHiddenChange(checked: 'indeterminate' | boolean) {
    onHiddenChange(testCase.id, checked === true)
  }

  function handleInputChange(e: ChangeEvent<HTMLTextAreaElement>) {
    onInputChange(testCase.id, e.target.value)
  }

  function handleRemove() {
    onRemove(testCase.id)
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 px-4">
        <CardTitle className="text-base">Тест-кейс {index + 1}</CardTitle>
        <Button
          disabled={!canRemove}
          onClick={handleRemove}
          size="sm"
          type="button"
          variant="destructive"
        >
          <Trash2 className="size-4" />
          Удалить
        </Button>
      </CardHeader>
      <CardContent className="space-y-3 px-4 pt-0 pb-4">
        <Label className="flex w-fit items-center gap-2 font-normal">
          <Checkbox
            checked={testCase.isHidden}
            onCheckedChange={handleHiddenChange}
          />
          Скрытый тест
        </Label>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="flex flex-col gap-2">
            <Label htmlFor={`custom-task-test-input-${testCase.id}`}>
              Входные данные
            </Label>
            <Textarea
              className="min-h-28"
              id={`custom-task-test-input-${testCase.id}`}
              onChange={handleInputChange}
              rows={5}
              value={testCase.input}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor={`custom-task-test-output-${testCase.id}`}>
              Ожидаемый выход
            </Label>
            <Textarea
              className="min-h-28"
              id={`custom-task-test-output-${testCase.id}`}
              onChange={handleExpectedOutputChange}
              rows={5}
              value={testCase.expectedOutput}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
