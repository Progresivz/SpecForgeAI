from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class BackupResponse(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id:int; job_id:int|None; database_type:str; path:str; status:str; size_bytes:int; verified:bool; retention_deleted:bool; created_at:datetime; message:str

class OperationJobResponse(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id:int; job_type:str; status:str; started_at:datetime; finished_at:datetime|None; duration_ms:float|None; output_path:str|None; message:str

class RetentionResponse(BaseModel):
    kept:int; deleted:int; retention_days:int; retention_count:int
