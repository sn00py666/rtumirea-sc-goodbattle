from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class RegisterRequest(ApiModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=6)


class LoginRequest(ApiModel):
    email: EmailStr
    password: str = Field(min_length=1)


class UserResponse(ApiModel):
    id: str
    email: EmailStr
    username: str
    is_admin: bool


class LanguageResponse(ApiModel):
    id: int
    code: str
    name: str


class ProfileResponse(ApiModel):
    email: EmailStr
    username: str
    created_at: datetime
    top_language: Optional[str]
    battles_played: int
    battles_organized: int
    win_rate: int
    wins_count: int


class TaskResponse(ApiModel):
    id: str
    title: str
    description: str
    time_limit_ms: int
    memory_limit_mb: int
    creator: Optional['TaskCreatorResponse']
    examples: List['TaskExampleResponse']


class TaskDetailResponse(TaskResponse):
    test_cases: List['TaskTestCaseResponse']


class CreateRoomRequest(ApiModel):
    languages: List[str] = Field(min_length=1)
    task_ids: List[str] = Field(min_length=1)
    time_limit: int = Field(ge=1, le=30)


class CreateRoomResponse(ApiModel):
    room_id: str
    code: str


class JoinRoomRequest(ApiModel):
    code: str = Field(min_length=1)


class JoinRoomResponse(ApiModel):
    participant_id: str
    room_id: str


class TaskExampleResponse(ApiModel):
    input: str
    output: str


class TaskExampleRequest(ApiModel):
    input: str = Field(min_length=1)
    output: str = Field(min_length=1)


class TaskTestCaseResponse(ApiModel):
    input: str
    expected_output: str
    is_hidden: bool


class TaskTestCaseRequest(ApiModel):
    input: str = Field(min_length=1)
    expected_output: str = Field(min_length=1)
    is_hidden: bool = True


class TaskCreatorResponse(ApiModel):
    id: str
    username: str


class CreateTaskRequest(ApiModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    time_limit_ms: int = Field(ge=1)
    memory_limit_mb: int = Field(ge=1)
    examples: List[TaskExampleRequest] = Field(default_factory=list)
    test_cases: List[TaskTestCaseRequest] = Field(min_length=1)


class UpdateTaskRequest(ApiModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    time_limit_ms: int = Field(ge=1)
    memory_limit_mb: int = Field(ge=1)
    examples: List[TaskExampleRequest] = Field(default_factory=list)
    test_cases: List[TaskTestCaseRequest] = Field(min_length=1)


class BattleTaskResponse(ApiModel):
    id: str
    title: str
    description: str
    examples: List[TaskExampleResponse]


class ParticipantResponse(ApiModel):
    id: str
    user_id: str
    username: str
    role: str
    language: str
    code: str


class ParticipantSolvedTasksResponse(ApiModel):
    user_id: str
    solved_task_ids: List[str]


class RoomAiHintInfoResponse(ApiModel):
    task_id: Optional[str] = None
    used: bool
    question: Optional[str] = None
    answer: Optional[str] = None


class RoomResponse(ApiModel):
    id: str
    code: str
    status: str
    role: str
    current_task_index: int
    total_tasks: int
    time_limit: int
    remaining_seconds: int
    languages: List[str]
    tasks: List[BattleTaskResponse]
    participants: List[ParticipantResponse]
    participants_solved_tasks: List[ParticipantSolvedTasksResponse]
    ai_hint: RoomAiHintInfoResponse


class RoomStatusResponse(ApiModel):
    status: str


class NextTaskResponse(ApiModel):
    current_task_index: int
    status: str


class BattleResultResponse(ApiModel):
    place: int
    username: str
    participant_id: str
    solved_tasks: int
    total_tasks: int
    total_time: int


class FinishBattleResponse(ApiModel):
    results: List[BattleResultResponse]
    status: str


class RunCodeRequest(ApiModel):
    code: str
    language: str
    task_id: str


class AskAiHintRequest(ApiModel):
    task_id: str
    question: str = Field(min_length=1, max_length=100)


class RunCodeExecutionLogResponse(ApiModel):
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool


class RunCodeResultResponse(ApiModel):
    input: Optional[str] = None
    expected: Optional[str] = None
    actual: Optional[str] = None
    passed: bool
    error: Optional[str] = None
    log: RunCodeExecutionLogResponse


class BattleHistoryItemResponse(ApiModel):
    id: str
    title: str
    date: str
    status: str
    role: str
    participants: int
    languages: List[str]
    total_tasks: int
    solved_tasks: int
    place: Optional[int] = None


class WebSocketEnvelope(ApiModel):
    type: str
    data: Dict[str, Any]


class AnalyticsFrequencyResponse(ApiModel):
    key: str
    count: int


class AnalyticsHeatmapCellResponse(ApiModel):
    date: str
    count: int


class AnalyticsBattleListItemResponse(ApiModel):
    id: str
    title: str
    date: str
    status: str
    role: str
    participants: int
    languages: List[str]
    total_tasks: int
    solved_tasks: int
    place: Optional[int] = None
    attempts: int


class ParticipantAnalyticsResponse(ApiModel):
    user_id: str
    username: str
    is_self: bool
    battles_count: int
    win_rate: int
    solved_tasks_count: int
    average_attempts_per_task: float
    average_place: Optional[float] = None
    error_frequencies: List[AnalyticsFrequencyResponse]
    heatmap: List[AnalyticsHeatmapCellResponse]
    battles: List[AnalyticsBattleListItemResponse]


class BattleParticipantAnalyticsResponse(ApiModel):
    participant_id: str
    user_id: str
    username: str
    place: int
    solved_tasks: int
    total_time_seconds: int
    submissions_count: int
    hint_used: bool


class BattleTaskAnalyticsResponse(ApiModel):
    task_id: str
    title: str
    average_time_to_ac_seconds: Optional[float] = None
    average_submissions: float
    solved_percent: float
    error_frequencies: List[AnalyticsFrequencyResponse]
    first_ac_time_seconds: Optional[int] = None


class BattleSubmissionAnalyticsResponse(ApiModel):
    submission_id: str
    user_id: str
    username: str
    task_id: str
    language: str
    verdict: str
    created_at: datetime
    execution_time_ms: int
    execution_memory_kb: int
    passed_tests: int
    failed_tests: int
    total_tests: int
    test_results: List['BattleSubmissionTestResultAnalyticsResponse']
    source_code: str


class BattleSubmissionTestResultAnalyticsResponse(ApiModel):
    test_id: str
    verdict: str
    execution_time_ms: int
    execution_memory_kb: int
    error_message: Optional[str] = None


class BattleDetailAnalyticsResponse(ApiModel):
    battle_id: str
    title: str
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    participants: List[BattleParticipantAnalyticsResponse]
    tasks: List[BattleTaskAnalyticsResponse]
    submissions: List[BattleSubmissionAnalyticsResponse]
    participants_without_ac_count: int
    hint_usage_share: float
    problematic_tasks: List[BattleTaskAnalyticsResponse]


class OrganizerAnalyticsResponse(ApiModel):
    organized_battles_count: int
    average_participants: float
    average_solved_percent: float
    average_time_to_solve_seconds: Optional[float] = None
    average_submissions_per_task: float
    average_battle_duration_seconds: Optional[float] = None
    finish_by_timer_share: float
    finish_early_share: float
    retention_percent: float
    hint_usage_share: float
    average_skill_spread: Optional[float] = None
    language_frequencies: List[AnalyticsFrequencyResponse]
    battles: List[AnalyticsBattleListItemResponse]


class AdminFunnelResponse(ApiModel):
    created_rooms: int
    started_battles: int
    finished_battles: int


class TaskPlatformAnalyticsResponse(ApiModel):
    task_id: str
    title: str
    rooms_count: int
    submissions_count: int
    solved_percent: float


class PeakLoadBucketResponse(ApiModel):
    bucket: str
    count: int


class AdminPlatformAnalyticsResponse(ApiModel):
    total_users: int
    dau: int
    wau: int
    mau: int
    total_battles: int
    finished_battles: int
    unique_participants: int
    average_participants_per_battle: float
    average_solved_percent: float
    total_submissions: int
    verdict_frequencies: List[AnalyticsFrequencyResponse]
    language_frequencies: List[AnalyticsFrequencyResponse]
    ai_hints_total: int
    ai_hint_users_share: float
    first_battle_conversion_percent: float
    organizer_funnel: AdminFunnelResponse
    top_tasks_by_difficulty: List[TaskPlatformAnalyticsResponse]
    top_tasks_by_popularity: List[TaskPlatformAnalyticsResponse]
    peaks_by_hour: List[PeakLoadBucketResponse]
    peaks_by_weekday: List[PeakLoadBucketResponse]


class AiAnalyticsQueryRequest(ApiModel):
    question: str = Field(min_length=3, max_length=700)


class AiAnalyticsQueryResponse(ApiModel):
    question: str
    sql: str
    sql_explanation: str
    report_markdown: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    truncated: bool
    model: str
    generated_at: datetime
