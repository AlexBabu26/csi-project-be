"""Admin system router - system-wide administrative functions."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.common.db import get_db
from app.common.security import get_current_user, get_password_hash
from app.auth.models import (
    CustomUser,
    ClergyDistrict,
    UnitName,
    UnitRegistrationData,
    UserType,
)

router = APIRouter()


async def get_admin_user(
    current_user: CustomUser = Depends(get_current_user),
) -> CustomUser:
    """Dependency to ensure user is an admin."""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required."
        )
    return current_user


# Schemas
class DistrictCreate(BaseModel):
    """Schema for creating a district."""
    name: str = Field(..., min_length=1, max_length=255)


class UnitNameCreate(BaseModel):
    """Schema for creating a unit name."""
    clergy_district_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1, max_length=255)


class RegisteredUserCreate(BaseModel):
    """Schema for creating a registered unit user."""
    district_id: int = Field(..., gt=0)
    unit_name_id: int = Field(..., gt=0)
    phone_number: str = Field(..., min_length=1, max_length=20)
    password: str = Field(..., min_length=1)


# District Endpoints
@router.get("/districts", response_model=List[dict])
async def list_districts(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all clergy districts."""
    stmt = select(ClergyDistrict)
    result = await db.execute(stmt)
    districts = list(result.scalars().all())

    return [
        {
            "id": district.id,
            "name": district.name,
        }
        for district in districts
    ]


@router.post("/districts", response_model=dict)
async def create_district(
    data: DistrictCreate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new clergy district."""
    # Check if district already exists
    stmt = select(ClergyDistrict).where(ClergyDistrict.name == data.name)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="District with this name already exists"
        )
    
    district = ClergyDistrict(name=data.name)
    db.add(district)
    await db.commit()
    await db.refresh(district)
    
    return {
        "message": "District created successfully",
        "id": district.id,
        "name": district.name,
    }


# Unit Name Endpoints
@router.get("/unit-names", response_model=List[dict])
async def list_unit_names(
    district_id: int = None,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all unit names, optionally filtered by district."""
    stmt = select(UnitName)
    
    if district_id:
        stmt = stmt.where(UnitName.clergy_district_id == district_id)
    
    result = await db.execute(stmt)
    unit_names = list(result.scalars().all())
    
    # Get district names
    stmt = select(ClergyDistrict)
    result = await db.execute(stmt)
    districts = {d.id: d.name for d in result.scalars().all()}
    
    return [
        {
            "id": unit.id,
            "name": unit.name,
            "clergy_district_id": unit.clergy_district_id,
            "district_name": districts.get(unit.clergy_district_id, "Unknown"),
        }
        for unit in unit_names
    ]


@router.post("/unit-names", response_model=dict)
async def create_unit_name(
    data: UnitNameCreate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new unit name."""
    # Verify district exists
    stmt = select(ClergyDistrict).where(ClergyDistrict.id == data.clergy_district_id)
    result = await db.execute(stmt)
    district = result.scalar_one_or_none()
    
    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clergy district not found"
        )
    
    # Check if unit name already exists for this district
    stmt = select(UnitName).where(
        UnitName.clergy_district_id == data.clergy_district_id,
        UnitName.name == data.name
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unit name already exists for this district"
        )
    
    unit_name = UnitName(
        clergy_district_id=data.clergy_district_id,
        name=data.name,
    )
    db.add(unit_name)
    await db.commit()
    await db.refresh(unit_name)
    
    return {
        "message": "Unit name created successfully",
        "id": unit_name.id,
        "name": unit_name.name,
        "district_name": district.name,
    }


# User Registration Endpoint
@router.post("/users", response_model=dict)
async def create_registered_user(
    data: RegisteredUserCreate,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a registered unit user with auto-generated registration number."""
    # Verify district exists
    stmt = select(ClergyDistrict).where(ClergyDistrict.id == data.district_id)
    result = await db.execute(stmt)
    district = result.scalar_one_or_none()
    
    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District not found"
        )
    
    # Verify unit name exists
    stmt = select(UnitName).where(UnitName.id == data.unit_name_id)
    result = await db.execute(stmt)
    unit_name = result.scalar_one_or_none()
    
    if not unit_name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit name not found"
        )
    
    # Check if phone number already taken
    stmt = select(CustomUser).where(CustomUser.phone_number == data.phone_number)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number is already taken"
        )
    
    # Check if unit already registered
    stmt = select(CustomUser).where(CustomUser.unit_name_id == data.unit_name_id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unit has been registered already"
        )
    
    # Create user
    district_code = district.name[:3]
    
    # Create user first to get ID
    user = CustomUser(
        phone_number=data.phone_number,
        user_type=UserType.UNIT,
        unit_name_id=data.unit_name_id,
        hashed_password=get_password_hash(data.password),
        is_active=True,
        username="temp",  # Temporary, will update
        email="temp@temp.com",  # Temporary, will update
    )
    
    db.add(user)
    await db.flush()
    
    # Generate registration number
    registration_number = f"MKDYM/{district_code}/00{user.id}"
    
    # Update user with registration number
    user.email = registration_number
    user.username = registration_number
    
    # Create unit registration data
    unit_reg = UnitRegistrationData(
        registered_user_id=user.id,
        status="Registration Started",
    )
    
    db.add(unit_reg)
    await db.commit()
    await db.refresh(user)
    
    return {
        "message": "User registration successful",
        "user_id": user.id,
        "registration_number": registration_number,
        "username": registration_number,
    }

