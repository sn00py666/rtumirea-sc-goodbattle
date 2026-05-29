# WebSocket events

Endpoint: `/ws/rooms/{room_id}`

Envelope format for every event:

```json
{
  "type": "event_name",
  "data": {}
}
```

## Client -> server events

### `code_update`

```json
{
  "type": "code_update",
  "data": {
    "code": "print('hello')"
  }
}
```

### `language_change`

```json
{
  "type": "language_change",
  "data": {
    "language": "python"
  }
}
```

### `run_code`

```json
{
  "type": "run_code",
  "data": {
    "task_id": "<task-id>",
    "language": "python",
    "code": "print(input())"
  }
}
```

### `ask_ai_hint`

One hint per participant per task.

```json
{
  "type": "ask_ai_hint",
  "data": {
    "task_id": "<task-id>",
    "question": "Почему падает на некоторых тестах?"
  }
}
```

Constraints:
- `question` max length: `100`
- hint can be used once for each task by each participant
- user must have non-empty code
- if there are no run/test logs yet, server runs tests automatically before AI request

### Organizer-only events

- `start_battle`
- `pause_battle`
- `next_task`
- `finish_battle`

## Server -> client events

### Common room events

- `participant_joined`
- `participant_left`
- `code_update`
- `language_change`
- `status_change`
- `next_task`
- `participant_task_solved`
- `battle_finished`

### `run_code_result`

Response to `run_code`.

```json
{
  "type": "run_code_result",
  "data": {
    "task_id": "<task-id>",
    "results": [
      {
        "input": "1 2",
        "expected": "3",
        "actual": "3",
        "passed": true,
        "error": null,
        "log": {
          "stdout": "3\n",
          "stderr": "",
          "exit_code": 0,
          "timed_out": false
        }
      }
    ]
  }
}
```

For hidden tests, `input`/`expected`/`actual` can be `null`.

### AI hint streaming events

`ask_ai_hint` now returns the hint as stream of token chunks:

1. `ai_hint_started`
2. one or many `ai_hint_chunk`
3. final `ai_hint_result`

`ai_hint_started`:

```json
{
  "type": "ai_hint_started",
  "data": {
    "task_id": "<task-id>"
  }
}
```

`ai_hint_chunk`:

```json
{
  "type": "ai_hint_chunk",
  "data": {
    "delta": "Попробуй проверить"
  }
}
```

`ai_hint_result`:

```json
{
  "type": "ai_hint_result",
  "data": {
    "task_id": "<task-id>",
    "hint": "Полный собранный текст подсказки",
    "remaining": 0
  }
}
```

### `error`

Error for invalid payloads, permissions, room/task constraints, Docker/AI failures, etc.

```json
{
  "type": "error",
  "data": {
    "detail": "Unsupported language",
    "status": 400
  }
}
```
