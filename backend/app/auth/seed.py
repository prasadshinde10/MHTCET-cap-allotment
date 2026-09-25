import logging
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.admin_user import AdminUser
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)
settings = get_settings()

def seed_admin_user(db: Session):
    admin = db.query(AdminUser).filter(AdminUser.username == settings.ADMIN_USERNAME).first()
    if not admin:
        logger.info(f"Creating default admin user: {settings.ADMIN_USERNAME}")
        new_admin = AdminUser(
            username=settings.ADMIN_USERNAME,
            email=settings.ADMIN_EMAIL,
            password_hash=settings.ADMIN_PASSWORD_HASH
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
        logger.info("Admin user already exists, skipping seed.")
