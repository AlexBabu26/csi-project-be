"""Admin user management router - password resets and user administration."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, or_, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field

from app.common.db import get_async_db
from app.common.security import get_current_user, get_password_hash
from app.auth.models import CustomUser, UserType, ClergyDistrict, UnitName


router = APIRouter()


# ============ SCHEMAS ============

class UserListItem(BaseModel):
    """Schema for user list item."""
    id: int
    username: str
    email: str
    phone_number: Optional[str] = None
    user_type: str
    is_active: bool
    unit_name: Optional[str] = None
    district_name: Optional[str] = None

    class Config:
        from_attributes = True


class PasswordResetRequest(BaseModel):
    """Schema for individual password reset."""
    user_id: int = Field(..., gt=0)
    new_password: str = Field(..., min_length=6, max_length=128)


class BulkPasswordResetRequest(BaseModel):
    """Schema for bulk password reset."""
    user_ids: List[int] = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)


class PasswordResetResponse(BaseModel):
    """Response schema for password reset."""
    message: str
    user_id: int
    username: str


class BulkPasswordResetResponse(BaseModel):
    """Response schema for bulk password reset."""
    message: str
    total_requested: int
    total_reset: int
    reset_users: List[dict]
    failed_users: List[dict]


class DistrictOfficialCreateRequest(BaseModel):
    """Schema for creating a district official with district name as username."""
    district_id: int = Field(..., gt=0, description="ID of the clergy district")
    official_name: str = Field(..., min_length=1, max_length=255, description="Name of the official")
    phone_number: str = Field(..., min_length=10, max_length=20, description="Phone number (also used as default password)")
    password: Optional[str] = Field(None, min_length=6, max_length=128, description="Custom password (optional, defaults to phone number)")


class DistrictOfficialResponse(BaseModel):
    """Response schema for district official creation."""
    message: str
    official_id: int
    username: str
    district_name: str
    default_password_hint: str


# ============ DEPENDENCIES ============

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


# ============ USER LISTING ENDPOINTS ============

@router.get("", response_model=List[UserListItem])
async def list_users(
    user_type: Optional[str] = Query(None, description="Filter by user type: UNIT, DISTRICT_OFFICIAL, or all"),
    district_id: Optional[int] = Query(None, description="Filter by district ID"),
    search: Optional[str] = Query(None, description="Search by username, email, or phone"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    List users with optional filters.
    
    User types:
    - UNIT (2): Unit officials login users
    - DISTRICT_OFFICIAL (3): Conference/Kalamela officials
    """
    stmt = select(CustomUser).options(
        selectinload(CustomUser.unit_name).selectinload(UnitName.district),
        selectinload(CustomUser.clergy_district)
    )
    
    # Filter by user type (exclude ADMIN users from the list)
    if user_type:
        if user_type.upper() == "UNIT":
            stmt = stmt.where(CustomUser.user_type == UserType.UNIT)
        elif user_type.upper() == "DISTRICT_OFFICIAL":
            stmt = stmt.where(CustomUser.user_type == UserType.DISTRICT_OFFICIAL)
        else:
            # Return both UNIT and DISTRICT_OFFICIAL if invalid type specified
            stmt = stmt.where(CustomUser.user_type.in_([UserType.UNIT, UserType.DISTRICT_OFFICIAL]))
    else:
        # By default, exclude ADMIN users
        stmt = stmt.where(CustomUser.user_type.in_([UserType.UNIT, UserType.DISTRICT_OFFICIAL]))
    
    # Filter by district
    if district_id:
        stmt = stmt.outerjoin(UnitName, CustomUser.unit_name_id == UnitName.id).where(
            or_(
                CustomUser.clergy_district_id == district_id,
                UnitName.clergy_district_id == district_id
            )
        )
    
    # Filter by active status
    if is_active is not None:
        stmt = stmt.where(CustomUser.is_active == is_active)
    
    # Search filter
    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                CustomUser.username.ilike(search_pattern),
                CustomUser.email.ilike(search_pattern),
                CustomUser.phone_number.ilike(search_pattern),
            )
        )
    
    result = await db.execute(stmt)
    users = list(result.scalars().unique().all())
    
    return [
        UserListItem(
            id=user.id,
            username=user.username,
            email=user.email,
            phone_number=user.phone_number,
            user_type=user.user_type.name,
            is_active=user.is_active,
            unit_name=user.unit_name.name if user.unit_name else None,
            district_name=(
                user.clergy_district.name if user.clergy_district 
                else (user.unit_name.district.name if user.unit_name and user.unit_name.district else None)
            ),
        )
        for user in users
    ]


@router.get("/summary", response_model=dict)
async def get_users_summary(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get summary counts of users by type."""
    # Count users by type
    stmt = select(
        CustomUser.user_type,
        func.count(CustomUser.id).label('count')
    ).where(
        CustomUser.user_type.in_([UserType.UNIT, UserType.DISTRICT_OFFICIAL])
    ).group_by(CustomUser.user_type)
    
    result = await db.execute(stmt)
    counts = {row[0].name: row[1] for row in result.all()}
    
    return {
        "unit_officials": counts.get("UNIT", 0),
        "district_officials": counts.get("DISTRICT_OFFICIAL", 0),
        "total": sum(counts.values()),
    }


# ============ PASSWORD RESET ENDPOINTS ============

@router.post("/reset-password", response_model=PasswordResetResponse)
async def reset_user_password(
    data: PasswordResetRequest,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Reset password for a single user.
    
    Only allows resetting passwords for UNIT and DISTRICT_OFFICIAL users.
    """
    # Fetch the user
    stmt = select(CustomUser).where(CustomUser.id == data.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent resetting admin passwords through this endpoint
    if user.user_type == UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot reset admin passwords through this endpoint"
        )
    
    # Hash and update the password
    user.hashed_password = get_password_hash(data.new_password)
    await db.commit()
    
    return PasswordResetResponse(
        message="Password reset successfully",
        user_id=user.id,
        username=user.username,
    )


@router.post("/bulk-reset-password", response_model=BulkPasswordResetResponse)
async def bulk_reset_passwords(
    data: BulkPasswordResetRequest,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Reset passwords for multiple users at once.
    
    All selected users will be assigned the same new password.
    Only allows resetting passwords for UNIT and DISTRICT_OFFICIAL users.
    """
    # Fetch all requested users
    stmt = select(CustomUser).where(CustomUser.id.in_(data.user_ids))
    result = await db.execute(stmt)
    users = list(result.scalars().all())
    
    # Track results
    reset_users = []
    failed_users = []
    hashed_password = get_password_hash(data.new_password)
    
    # Find users that weren't found
    found_ids = {user.id for user in users}
    not_found_ids = set(data.user_ids) - found_ids
    
    for user_id in not_found_ids:
        failed_users.append({
            "user_id": user_id,
            "reason": "User not found"
        })
    
    # Process found users
    for user in users:
        # Skip admin users
        if user.user_type == UserType.ADMIN:
            failed_users.append({
                "user_id": user.id,
                "username": user.username,
                "reason": "Cannot reset admin passwords"
            })
            continue
        
        # Reset password
        user.hashed_password = hashed_password
        reset_users.append({
            "user_id": user.id,
            "username": user.username,
            "user_type": user.user_type.name,
        })
    
    await db.commit()
    
    return BulkPasswordResetResponse(
        message=f"Password reset completed for {len(reset_users)} users",
        total_requested=len(data.user_ids),
        total_reset=len(reset_users),
        reset_users=reset_users,
        failed_users=failed_users,
    )


@router.post("/reset-all-by-type", response_model=BulkPasswordResetResponse)
async def reset_all_passwords_by_type(
    user_type: str = Query(..., description="User type: UNIT or DISTRICT_OFFICIAL"),
    new_password: str = Query(..., min_length=6, max_length=128),
    district_id: Optional[int] = Query(None, description="Optional: limit to specific district"),
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Reset passwords for all users of a specific type.
    
    Use with caution - this affects all users of the specified type.
    
    User types:
    - UNIT: All unit officials
    - DISTRICT_OFFICIAL: All conference/kalamela officials
    """
    # Validate user type
    if user_type.upper() == "UNIT":
        target_type = UserType.UNIT
    elif user_type.upper() == "DISTRICT_OFFICIAL":
        target_type = UserType.DISTRICT_OFFICIAL
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user_type. Must be UNIT or DISTRICT_OFFICIAL"
        )
    
    # Build query
    stmt = select(CustomUser).where(CustomUser.user_type == target_type)
    
    # Optionally filter by district
    if district_id:
        if target_type == UserType.UNIT:
            stmt = stmt.join(UnitName, CustomUser.unit_name_id == UnitName.id).where(
                UnitName.clergy_district_id == district_id
            )
        else:
            stmt = stmt.where(CustomUser.clergy_district_id == district_id)
    
    result = await db.execute(stmt)
    users = list(result.scalars().all())
    
    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No users found for type {user_type}"
        )
    
    # Reset all passwords
    hashed_password = get_password_hash(new_password)
    reset_users = []
    
    for user in users:
        user.hashed_password = hashed_password
        reset_users.append({
            "user_id": user.id,
            "username": user.username,
            "user_type": user.user_type.name,
        })
    
    await db.commit()
    
    return BulkPasswordResetResponse(
        message=f"Password reset completed for all {user_type} users",
        total_requested=len(users),
        total_reset=len(users),
        reset_users=reset_users,
        failed_users=[],
    )


# ============ DISTRICT OFFICIAL MANAGEMENT ENDPOINTS ============

@router.post("/district-officials", response_model=DistrictOfficialResponse)
async def create_district_official(
    data: DistrictOfficialCreateRequest,
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Create a district official with DISTRICT NAME as username.
    
    This enables district-wise login for Kalamela and Conference modules.
    Each district can have only ONE district official account.
    
    Login credentials:
    - Username: District name (e.g., 'THIRUVALLA', 'ADOOR')
    - Password: Phone number (or custom password if provided)
    """
    # Get district
    stmt = select(ClergyDistrict).where(ClergyDistrict.id == data.district_id)
    result = await db.execute(stmt)
    district = result.scalar_one_or_none()
    
    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District not found"
        )
    
    # Check if district already has an official
    stmt = select(CustomUser).where(
        and_(
            CustomUser.clergy_district_id == data.district_id,
            CustomUser.user_type == UserType.DISTRICT_OFFICIAL
        )
    )
    result = await db.execute(stmt)
    existing_official = result.scalar_one_or_none()
    
    if existing_official:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"District '{district.name}' already has an official. "
                   f"Use password reset to update credentials."
        )
    
    # Check if username (district name) is already taken
    stmt = select(CustomUser).where(CustomUser.username == district.name)
    result = await db.execute(stmt)
    existing_username = result.scalar_one_or_none()
    
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{district.name}' is already in use"
        )
    
    # Check if phone number is already taken
    stmt = select(CustomUser).where(CustomUser.phone_number == data.phone_number)
    result = await db.execute(stmt)
    existing_phone = result.scalar_one_or_none()
    
    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number is already in use"
        )
    
    # Use custom password or phone number as default
    password = data.password if data.password else data.phone_number
    
    # Create district official with DISTRICT NAME as username
    official = CustomUser(
        username=district.name,  # District name as username
        email=f"{district.name.lower().replace(' ', '_')}@district.local",
        first_name=data.official_name,
        phone_number=data.phone_number,
        clergy_district_id=data.district_id,
        user_type=UserType.DISTRICT_OFFICIAL,
        hashed_password=get_password_hash(password),
        is_active=True,
    )
    
    db.add(official)
    await db.commit()
    await db.refresh(official)
    
    return DistrictOfficialResponse(
        message="District official created successfully",
        official_id=official.id,
        username=official.username,
        district_name=district.name,
        default_password_hint="Phone number" if not data.password else "Custom password provided",
    )


@router.get("/district-officials", response_model=List[dict])
async def list_district_officials(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    List all district officials.
    
    Shows username (district name), official name, phone, and district info.
    """
    stmt = select(CustomUser).where(
        CustomUser.user_type == UserType.DISTRICT_OFFICIAL
    ).options(selectinload(CustomUser.clergy_district))
    
    result = await db.execute(stmt)
    officials = list(result.scalars().all())
    
    return [
        {
            "id": official.id,
            "username": official.username,  # District name
            "official_name": official.first_name,
            "phone_number": official.phone_number,
            "district_id": official.clergy_district_id,
            "district_name": official.clergy_district.name if official.clergy_district else None,
            "is_active": official.is_active,
            "conference_id": official.conference_id,
        }
        for official in officials
    ]


@router.get("/districts", response_model=List[dict])
async def list_districts_for_officials(
    current_user: CustomUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    List all districts with their official status.
    
    Shows which districts have officials and which don't.
    """
    # Get all districts
    stmt = select(ClergyDistrict)
    result = await db.execute(stmt)
    districts = list(result.scalars().all())
    
    # Get districts that have officials
    stmt = select(CustomUser.clergy_district_id).where(
        CustomUser.user_type == UserType.DISTRICT_OFFICIAL
    ).distinct()
    result = await db.execute(stmt)
    districts_with_officials = {row[0] for row in result.all()}
    
    return [
        {
            "id": district.id,
            "name": district.name,
            "has_official": district.id in districts_with_officials,
            "login_username": district.name if district.id in districts_with_officials else None,
        }
        for district in districts
    ]


