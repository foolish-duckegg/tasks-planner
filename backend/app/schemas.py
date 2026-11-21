from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OutModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _check_minute_range(start_minute: int, end_minute: int) -> None:
    if end_minute <= start_minute:
        raise ValueError("end_minute 必须大于 start_minute")


# ---------------------------------------------------------------------------
# 任务状态
# ---------------------------------------------------------------------------
class TaskStatusCreate(StrictModel):
    code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="唯一代码，如 todo、doing、blocked",
        examples=["todo"],
    )
    name: str = Field(..., min_length=1, max_length=100, description="显示名")
    sort_order: int = Field(0, description="排序值，越小越靠前")
    remark: str | None = Field(None, description="备注")
    is_active: bool = Field(True, description="是否启用")
    is_initial_filter: bool = Field(
        True, description="是否纳入任务列表的初始状态筛选"
    )


class TaskStatusUpdate(StrictModel):
    name: str | None = Field(None, min_length=1, max_length=100, description="显示名")
    sort_order: int | None = Field(None, description="排序值")
    remark: str | None = Field(None, description="备注")
    is_active: bool | None = Field(None, description="是否启用")
    is_initial_filter: bool | None = Field(
        None, description="是否纳入任务列表的初始状态筛选"
    )


class TaskStatusOut(OutModel):
    id: int
    code: str
    name: str
    sort_order: int
    remark: str | None
    is_active: bool
    is_initial_filter: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


# ---------------------------------------------------------------------------
# 优先级
# ---------------------------------------------------------------------------
class PriorityLevelCreate(StrictModel):
    level: int = Field(..., ge=1, description="优先级等级，1 最高")
    name: str = Field(..., min_length=1, max_length=50, description="显示名，如 P0")
    usage: str | None = Field(None, description="用法说明：什么情况下使用该等级")
    remark: str | None = Field(None, description="备注")
    color: str | None = Field(
        None,
        pattern=r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$",
        description="前端颜色，如 #e5484d",
    )
    is_active: bool = Field(True, description="是否启用")


class PriorityLevelUpdate(StrictModel):
    level: int | None = Field(None, ge=1, description="优先级等级，1 最高")
    name: str | None = Field(None, min_length=1, max_length=50, description="显示名")
    usage: str | None = Field(None, description="用法说明")
    remark: str | None = Field(None, description="备注")
    color: str | None = Field(
        None,
        pattern=r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$",
        description="前端颜色，如 #e5484d",
    )
    is_active: bool | None = Field(None, description="是否启用")


class PriorityLevelOut(OutModel):
    id: int
    level: int
    name: str
    usage: str | None
    remark: str | None
    color: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


# ---------------------------------------------------------------------------
# 任务
# ---------------------------------------------------------------------------
class TaskCreate(StrictModel):
    title: str = Field(..., min_length=1, max_length=500, description="任务标题")
    priority_level_id: int | None = Field(None, description="优先级 ID")
    status_id: int = Field(1, description="状态 ID，内置 1=待办")
    deadline_at: datetime | None = Field(
        None,
        description="截止时间，ISO 8601；不传或 null 表示无截止时间",
        examples=["2026-11-30T18:00:00+08:00"],
    )
    progress: str | None = Field(None, description="进度文字描述")
    remark: str | None = Field(None, description="备注")


class TaskUpdate(StrictModel):
    title: str | None = Field(None, min_length=1, max_length=500, description="任务标题")
    priority_level_id: int | None = Field(None, description="优先级 ID")
    status_id: int | None = Field(None, description="状态 ID")
    deadline_at: datetime | None = Field(None, description="截止时间，ISO 8601")
    progress: str | None = Field(None, description="进度文字描述")
    remark: str | None = Field(None, description="备注")


class TaskOut(OutModel):
    id: int
    title: str
    priority_level_id: int | None
    status_id: int
    deadline_at: datetime | None
    progress: str | None
    remark: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    completed_at: datetime | None
    status_code: str
    status_name: str
    priority_level: int | None = Field(None, description="优先级等级，1 最高")
    priority_name: str | None
    priority_color: str | None


# ---------------------------------------------------------------------------
# 每日基础时间划分
# ---------------------------------------------------------------------------
class DayBlockCreate(StrictModel):
    start_minute: int = Field(
        ..., ge=0, le=1439, description="开始分钟，00:00 = 0"
    )
    end_minute: int = Field(
        ..., ge=1, le=1440, description="结束分钟，24:00 = 1440"
    )
    label: str | None = Field(None, max_length=100, description="名称")
    kind: str | None = Field(None, max_length=50, description="分类，如 work/rest/sleep")
    remark: str | None = Field(None, description="备注")
    is_active: bool = Field(True, description="是否启用")

    @model_validator(mode="after")
    def _validate_range(self) -> "DayBlockCreate":
        _check_minute_range(self.start_minute, self.end_minute)
        return self


class DayBlockUpdate(StrictModel):
    start_minute: int | None = Field(None, ge=0, le=1439, description="开始分钟")
    end_minute: int | None = Field(None, ge=1, le=1440, description="结束分钟")
    label: str | None = Field(None, max_length=100, description="名称")
    kind: str | None = Field(None, max_length=50, description="分类")
    remark: str | None = Field(None, description="备注")
    is_active: bool | None = Field(None, description="是否启用")


class DayBlockOut(OutModel):
    id: int
    start_minute: int
    end_minute: int
    label: str | None
    kind: str | None
    remark: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class DayBlockBulkReplace(StrictModel):
    blocks: list[DayBlockCreate] = Field(
        default_factory=list,
        description="新的完整每日划分；空数组表示清空模板",
    )


# ---------------------------------------------------------------------------
# 固定块
# ---------------------------------------------------------------------------
class FixedBlockCreate(StrictModel):
    title: str = Field(..., min_length=1, max_length=200, description="固定块名称")
    recurrence: Literal["daily", "weekly", "monthly"] = Field(
        ..., description="重复类型"
    )
    recurrence_value: int | None = Field(
        None,
        description="循环值：daily 为 null；weekly 为 ISO 星期 1..7；monthly 为日号 1..31",
        examples=[5],
    )
    start_minute: int = Field(..., ge=0, le=1439, description="开始分钟")
    end_minute: int = Field(..., ge=1, le=1440, description="结束分钟")
    effective_from: date | None = Field(None, description="生效起始日期，含端点")
    effective_to: date | None = Field(None, description="生效结束日期，含端点")
    overlap_priority: int = Field(0, description="固定块冲突时的优先级，越大越优先")
    allow_task_schedule: bool = Field(
        True, description="是否允许在该固定块时段内添加任务排期"
    )
    remark: str | None = Field(None, description="备注")
    is_active: bool = Field(True, description="是否启用")

    @model_validator(mode="after")
    def _validate_values(self) -> "FixedBlockCreate":
        _check_minute_range(self.start_minute, self.end_minute)
        if self.recurrence == "daily" and self.recurrence_value is not None:
            raise ValueError("daily 的 recurrence_value 必须为 null")
        if self.recurrence == "weekly" and (
            self.recurrence_value is None or not 1 <= self.recurrence_value <= 7
        ):
            raise ValueError("weekly 的 recurrence_value 必须在 1..7")
        if self.recurrence == "monthly" and (
            self.recurrence_value is None or not 1 <= self.recurrence_value <= 31
        ):
            raise ValueError("monthly 的 recurrence_value 必须在 1..31")
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_from > self.effective_to
        ):
            raise ValueError("effective_from 不能晚于 effective_to")
        return self


class FixedBlockUpdate(StrictModel):
    title: str | None = Field(None, min_length=1, max_length=200, description="固定块名称")
    recurrence: Literal["daily", "weekly", "monthly"] | None = Field(
        None, description="重复类型"
    )
    recurrence_value: int | None = Field(None, description="循环值")
    start_minute: int | None = Field(None, ge=0, le=1439, description="开始分钟")
    end_minute: int | None = Field(None, ge=1, le=1440, description="结束分钟")
    effective_from: date | None = Field(None, description="生效起始日期")
    effective_to: date | None = Field(None, description="生效结束日期")
    overlap_priority: int | None = Field(None, description="冲突优先级")
    allow_task_schedule: bool | None = Field(
        None, description="是否允许在该固定块时段内添加任务排期"
    )
    remark: str | None = Field(None, description="备注")
    is_active: bool | None = Field(None, description="是否启用")


class FixedBlockOut(OutModel):
    id: int
    title: str
    recurrence: str
    recurrence_value: int | None
    start_minute: int
    end_minute: int
    effective_from: date | None
    effective_to: date | None
    overlap_priority: int
    allow_task_schedule: bool
    remark: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


# ---------------------------------------------------------------------------
# 固定块例外（只跳过）
# ---------------------------------------------------------------------------
class FixedBlockExceptionCreate(StrictModel):
    effective_from: date | None = Field(None, description="例外生效起始日期，含端点")
    effective_to: date | None = Field(None, description="例外生效结束日期，含端点")
    skip_date: date | None = Field(None, description="只匹配该具体日期")
    weekday: int | None = Field(None, ge=1, le=7, description="只匹配 ISO 星期 1..7")
    day_of_month: int | None = Field(None, ge=1, le=31, description="只匹配日号 1..31")
    start_minute: int | None = Field(
        None, ge=0, le=1439, description="可选；只跳过与该时段重叠的部分"
    )
    end_minute: int | None = Field(
        None, ge=1, le=1440, description="可选；必须与 start_minute 同时出现"
    )
    remark: str | None = Field(None, description="备注")
    is_active: bool = Field(True, description="是否启用")

    @model_validator(mode="after")
    def _validate_values(self) -> "FixedBlockExceptionCreate":
        if (self.start_minute is None) != (self.end_minute is None):
            raise ValueError("start_minute 和 end_minute 必须同时为空或同时填写")
        if self.start_minute is not None and self.end_minute is not None:
            _check_minute_range(self.start_minute, self.end_minute)
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_from > self.effective_to
        ):
            raise ValueError("effective_from 不能晚于 effective_to")
        return self


class FixedBlockExceptionUpdate(StrictModel):
    effective_from: date | None = Field(None, description="例外生效起始日期")
    effective_to: date | None = Field(None, description="例外生效结束日期")
    skip_date: date | None = Field(None, description="具体日期")
    weekday: int | None = Field(None, ge=1, le=7, description="ISO 星期")
    day_of_month: int | None = Field(None, ge=1, le=31, description="日号")
    start_minute: int | None = Field(None, ge=0, le=1439, description="跳过时段开始")
    end_minute: int | None = Field(None, ge=1, le=1440, description="跳过时段结束")
    remark: str | None = Field(None, description="备注")
    is_active: bool | None = Field(None, description="是否启用")


class FixedBlockExceptionOut(OutModel):
    id: int
    fixed_block_id: int
    effective_from: date | None
    effective_to: date | None
    skip_date: date | None
    weekday: int | None
    day_of_month: int | None
    start_minute: int | None
    end_minute: int | None
    remark: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


# ---------------------------------------------------------------------------
# 每日备忘录
# ---------------------------------------------------------------------------
class DailyMemoCreate(StrictModel):
    memo_date: date = Field(..., description="备忘录日期，YYYY-MM-DD")
    content: str = Field(
        ..., min_length=1, max_length=20000, description="备忘录内容"
    )


class DailyMemoOut(OutModel):
    id: int
    memo_date: date
    content: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


# ---------------------------------------------------------------------------
# 任务排期
# ---------------------------------------------------------------------------
class TaskScheduleCreate(StrictModel):
    task_id: int = Field(..., description="任务 ID")
    plan_date: date = Field(..., description="排期日期")
    start_minute: int = Field(..., ge=0, le=1439, description="开始分钟")
    end_minute: int = Field(..., ge=1, le=1440, description="结束分钟")
    status: Literal["planned", "done", "skipped"] = Field(
        "planned", description="排期状态"
    )
    allow_override: bool = Field(True, description="是否允许被同层更高优先级任务挤占")
    note: str | None = Field(None, description="备注")

    @model_validator(mode="after")
    def _validate_range(self) -> "TaskScheduleCreate":
        _check_minute_range(self.start_minute, self.end_minute)
        return self


class TaskScheduleUpdate(StrictModel):
    task_id: int | None = Field(None, description="任务 ID")
    plan_date: date | None = Field(None, description="排期日期")
    start_minute: int | None = Field(None, ge=0, le=1439, description="开始分钟")
    end_minute: int | None = Field(None, ge=1, le=1440, description="结束分钟")
    status: Literal["planned", "done", "skipped"] | None = Field(
        None, description="排期状态"
    )
    allow_override: bool | None = Field(None, description="是否允许被挤占")
    note: str | None = Field(None, description="备注")


class TaskScheduleOut(OutModel):
    id: int
    task_id: int
    task_title: str
    plan_date: date
    start_minute: int
    end_minute: int
    status: str
    allow_override: bool
    note: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


# ---------------------------------------------------------------------------
# 元信息
# ---------------------------------------------------------------------------
class MetaValueUpdate(StrictModel):
    value: str = Field(..., max_length=2000, description="配置值")


# ---------------------------------------------------------------------------
# 固定块发生实例
# ---------------------------------------------------------------------------
class FixedOccurrenceOut(BaseModel):
    fixed_block_id: int
    title: str
    date: date
    start_minute: int
    end_minute: int
    overlap_priority: int
    allow_task_schedule: bool
    remark: str | None
