from pydantic import BaseModel
from typing import List, Optional

class TrainingDayBase(BaseModel):
    day_id: str
    name: str
    exercises: List[str]


class TrainingDayCreate(TrainingDayBase):
    pass


class TrainingDay(TrainingDayBase):
    id: int 
    class Config:
        from_attribute = True


class WorkoutBase(BaseModel):
    workout_id: str
    day_id: str
    exercise: str
    weight: str
    reps: str
    comment: Optional[str] = ''
    date: str
    timestamp: str


class WorkoutCreate(WorkoutBase):
    pass


class Workout(WorkoutBase):
    id: int
    class Config:
        from_attribute: True


class SyncData(BaseModel):
    training_days: List[TrainingDayBase]
    workouts: List[WorkoutBase]

