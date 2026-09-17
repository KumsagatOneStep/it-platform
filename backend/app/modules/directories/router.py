from fastapi import APIRouter

from app.core.db import SessionDep
from app.modules.directories import departments
from app.modules.directories.reference_router import build_reference_routers
from app.modules.directories.references import REFERENCE_SPECS
from app.modules.directories.schemas import DepartmentCreate, DepartmentRead, DepartmentUpdate
from app.modules.users_auth.service import AdminDep, CurrentUserDep

departments_router = APIRouter(prefix="/departments", tags=["departments"])
admin_departments_router = APIRouter(prefix="/admin/departments", tags=["admin: departments"])


@departments_router.get("", response_model=list[DepartmentRead])
async def list_departments(session: SessionDep, user: CurrentUserDep) -> list[DepartmentRead]:
    items = await departments.list_departments(session)
    return [DepartmentRead.model_validate(item) for item in items]


@admin_departments_router.post("", response_model=DepartmentRead, status_code=201)
async def create_department(
    body: DepartmentCreate, session: SessionDep, admin: AdminDep
) -> DepartmentRead:
    department = await departments.create_department(
        session, actor_id=admin.id, name=body.name, head_id=body.head_id
    )
    return DepartmentRead.model_validate(department)


@admin_departments_router.patch("/{department_id}", response_model=DepartmentRead)
async def update_department(
    department_id: int, body: DepartmentUpdate, session: SessionDep, admin: AdminDep
) -> DepartmentRead:
    department = await departments.update_department(
        session,
        actor_id=admin.id,
        department_id=department_id,
        updates=body.model_dump(exclude_unset=True),
    )
    return DepartmentRead.model_validate(department)


routers = [departments_router, admin_departments_router]
for _spec in REFERENCE_SPECS:
    routers.extend(build_reference_routers(_spec))
