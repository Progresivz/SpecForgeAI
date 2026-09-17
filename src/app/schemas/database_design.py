from pydantic import BaseModel, ConfigDict, Field, model_validator


class DatabaseColumnCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    data_type: str = Field(min_length=1, max_length=50)
    position: int = Field(default=1, ge=1)
    nullable: bool = True
    primary_key: bool = False
    unique: bool = False
    default_value: str | None = Field(default=None, max_length=200)
    description: str | None = None


class DatabaseColumnResponse(DatabaseColumnCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class DatabaseTableCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    columns: list[DatabaseColumnCreate] = Field(default_factory=list)


class DatabaseTableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None
    columns: list[DatabaseColumnResponse] = Field(default_factory=list)


class DatabaseRelationshipCreate(BaseModel):
    from_table: str = Field(min_length=1, max_length=100)
    from_column: str = Field(min_length=1, max_length=100)
    to_table: str = Field(min_length=1, max_length=100)
    to_column: str = Field(min_length=1, max_length=100)
    cardinality: str = Field(default="many-to-one", max_length=20)
    on_delete: str = Field(default="CASCADE", max_length=20)
    notes: str | None = None


class DatabaseRelationshipResponse(DatabaseRelationshipCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class DatabaseDesignCreate(BaseModel):
    name: str = Field(default="Primary Database Design", min_length=1, max_length=200)
    target_dialect: str = Field(default="postgresql", max_length=30)
    notes: str | None = None
    tables: list[DatabaseTableCreate] = Field(default_factory=list)
    relationships: list[DatabaseRelationshipCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_names(self):
        names = [t.name.lower() for t in self.tables]
        if len(names) != len(set(names)):
            raise ValueError("Table names must be unique within a database design")
        return self


class DatabaseDesignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    name: str
    target_dialect: str
    notes: str | None
    tables: list[DatabaseTableResponse] = Field(default_factory=list)
    relationships: list[DatabaseRelationshipResponse] = Field(default_factory=list)


class SQLExportResponse(BaseModel):
    project_id: int
    dialect: str
    sql: str
