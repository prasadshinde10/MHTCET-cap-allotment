import logging
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.admin_user import AdminUser
from app.models.audit_log import AuditLog

from app.auth.security import hash_password

logger = logging.getLogger(__name__)
settings = get_settings()


def get_target_password_hash() -> str:
    # 1. Plain text password setting takes highest priority
    if settings.ADMIN_PASSWORD and settings.ADMIN_PASSWORD.strip():
        return hash_password(settings.ADMIN_PASSWORD.strip())

    # 2. Check ADMIN_PASSWORD_HASH setting
    if settings.ADMIN_PASSWORD_HASH and settings.ADMIN_PASSWORD_HASH.strip():
        raw = settings.ADMIN_PASSWORD_HASH.strip()
        if raw.startswith(("$2a$", "$2b$", "$2y$")):
            return raw
        # If user passed plaintext into ADMIN_PASSWORD_HASH, hash it automatically
        return hash_password(raw)

    return hash_password("Admin@12345")


def seed_admin_user(db: Session):
    target_hash = get_target_password_hash()
    admin = db.query(AdminUser).filter(AdminUser.username == settings.ADMIN_USERNAME).first()
    if not admin:
        logger.info(f"Creating default admin user: {settings.ADMIN_USERNAME}")
        new_admin = AdminUser(
            username=settings.ADMIN_USERNAME,
            email=settings.ADMIN_EMAIL,
            password_hash=target_hash
        )
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        
        audit = AuditLog(
            action="admin_user_seeded",
            entity_type="AdminUser",
            entity_id=new_admin.id,
            details={"username": new_admin.username}
        )
        db.add(audit)
        db.commit()
    else:
        # Sync updated password hash & unlock account on startup if needed
        needs_update = (
            admin.password_hash != target_hash
            or admin.locked_until is not None
            or admin.failed_login_attempts > 0
            or not admin.password_hash.startswith(("$2a$", "$2b$", "$2y$"))
        )
        if needs_update:
            admin.password_hash = target_hash
            admin.email = settings.ADMIN_EMAIL
            admin.failed_login_attempts = 0
            admin.locked_until = None
            db.commit()
            logger.info("Admin user credentials synced from environment settings and unlocked.")
        else:
            logger.info("Admin user already up to date.")
