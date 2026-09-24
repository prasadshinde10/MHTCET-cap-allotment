"""initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('admin_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, default=0),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )

    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'], unique=False)
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'], unique=False)
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'], unique=False)

    op.create_table('cap_rounds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('round_number', sa.Integer(), nullable=False),
        sa.Column('round_name', sa.String(length=50), nullable=False),
        sa.Column('source_filename', sa.String(length=500), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_status', sa.String(length=30), nullable=False, default='PENDING'),
        sa.Column('total_pages', sa.Integer(), nullable=False, default=0),
        sa.Column('total_records', sa.Integer(), nullable=False, default=0),
        sa.Column('error_count', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('year', 'round_number', name='uix_year_round')
    )

    op.create_table('colleges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('college_code', sa.String(length=20), nullable=False),
        sa.Column('college_name', sa.String(length=500), nullable=False),
        sa.Column('city', sa.String(length=200), nullable=True),
        sa.Column('district', sa.String(length=200), nullable=True),
        sa.Column('college_type', sa.String(length=20), nullable=False, default='Unknown'),
        sa.Column('funding_type', sa.String(length=20), nullable=False, default='Unknown'),
        sa.Column('minority_status', sa.String(length=20), nullable=False, default='Unknown'),
        sa.Column('minority_type', sa.String(length=200), nullable=True),
        sa.Column('home_university', sa.String(length=300), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='Active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_colleges_college_code'), 'colleges', ['college_code'], unique=True)

    op.create_table('courses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('college_id', sa.Integer(), nullable=False),
        sa.Column('course_code', sa.String(length=20), nullable=False),
        sa.Column('course_name', sa.String(length=500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['college_id'], ['colleges.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('college_id', 'course_code', name='uix_college_course')
    )

    op.create_table('import_batches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cap_round_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=500), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('file_path', sa.String(length=1000), nullable=True),
        sa.Column('parser_version', sa.String(length=20), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, default='PENDING'),
        sa.Column('pages_processed', sa.Integer(), nullable=False, default=0),
        sa.Column('records_created', sa.Integer(), nullable=False, default=0),
        sa.Column('records_updated', sa.Integer(), nullable=False, default=0),
        sa.Column('records_rejected', sa.Integer(), nullable=False, default=0),
        sa.Column('warning_count', sa.Integer(), nullable=False, default=0),
        sa.Column('error_count', sa.Integer(), nullable=False, default=0),
        sa.Column('summary', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['cap_round_id'], ['cap_rounds.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_import_batches_cap_round_id'), 'import_batches', ['cap_round_id'], unique=False)
    op.create_index(op.f('ix_import_batches_file_hash'), 'import_batches', ['file_hash'], unique=False)

    op.create_table('cutoffs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('cap_round_id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('import_batch_id', sa.Integer(), nullable=True),
        sa.Column('seat_section', sa.String(length=50), nullable=False),
        sa.Column('seat_section_raw', sa.String(length=200), nullable=True),
        sa.Column('category_code', sa.String(length=50), nullable=False),
        sa.Column('gender', sa.String(length=20), nullable=True),
        sa.Column('seat_category', sa.String(length=50), nullable=True),
        sa.Column('seat_location', sa.String(length=50), nullable=True),
        sa.Column('stage', sa.String(length=10), nullable=False),
        sa.Column('merit_number', sa.Integer(), nullable=True),
        sa.Column('percentile', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('source_page', sa.Integer(), nullable=True),
        sa.Column('source_pdf', sa.String(length=500), nullable=True),
        sa.Column('source_text_hash', sa.String(length=64), nullable=True),
        sa.Column('is_manually_corrected', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['cap_round_id'], ['cap_rounds.id'], ),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
        sa.ForeignKeyConstraint(['import_batch_id'], ['import_batches.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cutoffs_cap_round_id'), 'cutoffs', ['cap_round_id'], unique=False)
    op.create_index(op.f('ix_cutoffs_category_code'), 'cutoffs', ['category_code'], unique=False)
    op.create_index('ix_cutoffs_composite', 'cutoffs', ['cap_round_id', 'course_id', 'category_code', 'stage'], unique=False)
    op.create_index(op.f('ix_cutoffs_course_id'), 'cutoffs', ['course_id'], unique=False)
    op.create_index(op.f('ix_cutoffs_merit_number'), 'cutoffs', ['merit_number'], unique=False)
    op.create_index(op.f('ix_cutoffs_percentile'), 'cutoffs', ['percentile'], unique=False)
    op.create_index(op.f('ix_cutoffs_seat_section'), 'cutoffs', ['seat_section'], unique=False)
    op.create_index(op.f('ix_cutoffs_stage'), 'cutoffs', ['stage'], unique=False)
    op.create_index(op.f('ix_cutoffs_year'), 'cutoffs', ['year'], unique=False)

    op.create_table('import_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('import_batch_id', sa.Integer(), nullable=False),
        sa.Column('level', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('context', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['import_batch_id'], ['import_batches.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('parser_errors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('import_batch_id', sa.Integer(), nullable=False),
        sa.Column('source_page', sa.Integer(), nullable=True),
        sa.Column('error_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('college_code', sa.String(length=20), nullable=True),
        sa.Column('course_code', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='OPEN'),
        sa.Column('context', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['import_batch_id'], ['import_batches.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_parser_errors_batch_status_severity', 'parser_errors', ['import_batch_id', 'status', 'severity'], unique=False)

    op.create_table('staging_cutoffs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('cap_round_id', sa.Integer(), nullable=False),
        sa.Column('import_batch_id', sa.Integer(), nullable=False),
        sa.Column('college_code', sa.String(length=20), nullable=False),
        sa.Column('course_code', sa.String(length=20), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=True),
        sa.Column('seat_section', sa.String(length=50), nullable=False),
        sa.Column('seat_section_raw', sa.String(length=200), nullable=True),
        sa.Column('category_code', sa.String(length=50), nullable=False),
        sa.Column('gender', sa.String(length=20), nullable=True),
        sa.Column('seat_category', sa.String(length=50), nullable=True),
        sa.Column('seat_location', sa.String(length=50), nullable=True),
        sa.Column('stage', sa.String(length=10), nullable=False),
        sa.Column('merit_number', sa.Integer(), nullable=True),
        sa.Column('percentile', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('source_page', sa.Integer(), nullable=True),
        sa.Column('source_pdf', sa.String(length=500), nullable=True),
        sa.Column('source_text_hash', sa.String(length=64), nullable=True),
        sa.Column('validation_status', sa.String(length=20), nullable=False, default='PENDING'),
        sa.Column('validation_errors', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['cap_round_id'], ['cap_rounds.id'], ),
        sa.ForeignKeyConstraint(['import_batch_id'], ['import_batches.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('manual_corrections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cutoff_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('original_value', sa.Text(), nullable=True),
        sa.Column('corrected_value', sa.Text(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['cutoff_id'], ['cutoffs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('manual_corrections')
    op.drop_table('staging_cutoffs')
    op.drop_index('ix_parser_errors_batch_status_severity', table_name='parser_errors')
    op.drop_table('parser_errors')
    op.drop_table('import_logs')
    op.drop_index(op.f('ix_cutoffs_year'), table_name='cutoffs')
    op.drop_index(op.f('ix_cutoffs_stage'), table_name='cutoffs')
    op.drop_index(op.f('ix_cutoffs_seat_section'), table_name='cutoffs')
    op.drop_index(op.f('ix_cutoffs_percentile'), table_name='cutoffs')
    op.drop_index(op.f('ix_cutoffs_merit_number'), table_name='cutoffs')
    op.drop_index(op.f('ix_cutoffs_course_id'), table_name='cutoffs')
    op.drop_index('ix_cutoffs_composite', table_name='cutoffs')
    op.drop_index(op.f('ix_cutoffs_category_code'), table_name='cutoffs')
    op.drop_index(op.f('ix_cutoffs_cap_round_id'), table_name='cutoffs')
    op.drop_table('cutoffs')
    op.drop_index(op.f('ix_import_batches_file_hash'), table_name='import_batches')
    op.drop_index(op.f('ix_import_batches_cap_round_id'), table_name='import_batches')
    op.drop_table('import_batches')
    op.drop_table('courses')
    op.drop_index(op.f('ix_colleges_college_code'), table_name='colleges')
    op.drop_table('colleges')
    op.drop_table('cap_rounds')
    op.drop_index('ix_audit_logs_entity', table_name='audit_logs')
    op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
    op.drop_index('ix_audit_logs_action', table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_table('admin_users')
