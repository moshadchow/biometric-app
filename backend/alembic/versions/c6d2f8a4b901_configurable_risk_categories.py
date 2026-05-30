"""configurable risk categories

Revision ID: c6d2f8a4b901
Revises: a9c1e5f2b8d3
Create Date: 2026-05-30 00:00:00.000000

"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c6d2f8a4b901"
down_revision: Union[str, Sequence[str], None] = "a9c1e5f2b8d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BUSINESS_SEEDS = [
    ("JEWELER_GOLD_VALUABLE_METALS", "Jeweler / Gold / Valuable Metals Business", 5),
    ("MONEY_CHANGER_COURIER_MFS_AGENT", "Money Changer / Courier Service / Mobile Banking Agent", 5),
    ("REAL_ESTATE_DEVELOPER_AGENT", "Real Estate Developer / Agent", 5),
    ("EXPORT_IMPORT", "Export / Import", 5),
    ("TRAVEL_AGENT", "Travel Agent", 4),
    ("BUSINESS_AGENT", "Business Agent", 3),
    ("SMALL_BUSINESS_BELOW_BDT_5M", "Small Business (Investment below BDT 5 million)", 2),
    ("MANUFACTURER_EXCEPT_WEAPONS", "Manufacturer (except weapons)", 2),
    ("DEFAULT", "default", 3),
    ("INDIVIDUAL_INVESTOR", "individual_investor", 2),
]

PROFESSION_SEEDS = [
    ("PILOT_FLIGHT_ATTENDANT", "Pilot / Flight Attendant", 5),
    ("TRUSTEE", "Trustee", 5),
    ("LAWYER_DOCTOR_ENGINEER_CA", "Lawyer / Doctor / Engineer / Chartered Accountant", 4),
    ("GOVERNMENT_SERVICE", "Government Service", 3),
    ("TEACHER", "Teacher", 2),
    ("STUDENT", "Student", 2),
    ("RETIREE", "Retiree", 1),
    ("FARMER_LABORER", "Farmer / Laborer", 1),
    ("DEFAULT", "default", 3),
    ("SERVICE", "service", 2),
    ("BUSINESS", "business", 3),
]


def upgrade() -> None:
    now = datetime.utcnow()

    op.add_column("risk_business_categories", sa.Column("category_code", sa.String(), nullable=True))
    op.add_column("risk_business_categories", sa.Column("category_name", sa.String(), nullable=True))
    op.add_column("risk_business_categories", sa.Column("risk_score", sa.Integer(), nullable=True))
    op.add_column("risk_business_categories", sa.Column("description", sa.String(), nullable=True))
    op.add_column("risk_business_categories", sa.Column("is_active", sa.Boolean(), nullable=True))
    op.add_column("risk_business_categories", sa.Column("created_by", sa.Integer(), nullable=True))

    op.add_column("risk_profession_categories", sa.Column("profession_code", sa.String(), nullable=True))
    op.add_column("risk_profession_categories", sa.Column("profession_name", sa.String(), nullable=True))
    op.add_column("risk_profession_categories", sa.Column("risk_score", sa.Integer(), nullable=True))
    op.add_column("risk_profession_categories", sa.Column("description", sa.String(), nullable=True))
    op.add_column("risk_profession_categories", sa.Column("is_active", sa.Boolean(), nullable=True))
    op.add_column("risk_profession_categories", sa.Column("created_by", sa.Integer(), nullable=True))

    op.execute(
        """
        UPDATE risk_business_categories
        SET category_name = category,
            category_code = upper(regexp_replace(category, '[^a-zA-Z0-9]+', '_', 'g')),
            risk_score = score,
            is_active = status = 'ACTIVE'
        WHERE category_name IS NULL
        """
    )
    op.execute(
        """
        UPDATE risk_profession_categories
        SET profession_name = profession,
            profession_code = upper(regexp_replace(profession, '[^a-zA-Z0-9]+', '_', 'g')),
            risk_score = score,
            is_active = status = 'ACTIVE'
        WHERE profession_name IS NULL
        """
    )

    op.create_index(op.f("ix_risk_business_categories_category_code"), "risk_business_categories", ["category_code"], unique=True)
    op.create_index(op.f("ix_risk_business_categories_category_name"), "risk_business_categories", ["category_name"], unique=True)
    op.create_index(op.f("ix_risk_business_categories_is_active"), "risk_business_categories", ["is_active"], unique=False)
    op.create_index(op.f("ix_risk_profession_categories_profession_code"), "risk_profession_categories", ["profession_code"], unique=True)
    op.create_index(op.f("ix_risk_profession_categories_profession_name"), "risk_profession_categories", ["profession_name"], unique=True)
    op.create_index(op.f("ix_risk_profession_categories_is_active"), "risk_profession_categories", ["is_active"], unique=False)

    business_table = sa.table(
        "risk_business_categories",
        sa.column("category", sa.String),
        sa.column("score", sa.Integer),
        sa.column("status", sa.String),
        sa.column("category_code", sa.String),
        sa.column("category_name", sa.String),
        sa.column("risk_score", sa.Integer),
        sa.column("description", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    profession_table = sa.table(
        "risk_profession_categories",
        sa.column("profession", sa.String),
        sa.column("score", sa.Integer),
        sa.column("status", sa.String),
        sa.column("profession_code", sa.String),
        sa.column("profession_name", sa.String),
        sa.column("risk_score", sa.Integer),
        sa.column("description", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )

    for code, name, score in BUSINESS_SEEDS:
        op.execute(
            postgresql.insert(business_table)
            .values(
                category=name,
                score=score,
                status="ACTIVE",
                category_code=code,
                category_name=name,
                risk_score=score,
                description="Seeded from approved risk category examples.",
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=["category_code"],
                set_={
                    "category": name,
                    "score": score,
                    "status": "ACTIVE",
                    "category_name": name,
                    "risk_score": score,
                    "is_active": True,
                    "updated_at": now,
                },
            )
        )

    for code, name, score in PROFESSION_SEEDS:
        op.execute(
            postgresql.insert(profession_table)
            .values(
                profession=name,
                score=score,
                status="ACTIVE",
                profession_code=code,
                profession_name=name,
                risk_score=score,
                description="Seeded from approved risk profession examples.",
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=["profession_code"],
                set_={
                    "profession": name,
                    "score": score,
                    "status": "ACTIVE",
                    "profession_name": name,
                    "risk_score": score,
                    "is_active": True,
                    "updated_at": now,
                },
            )
        )

    op.alter_column("risk_business_categories", "category_code", nullable=False)
    op.alter_column("risk_business_categories", "category_name", nullable=False)
    op.alter_column("risk_business_categories", "risk_score", nullable=False)
    op.alter_column("risk_business_categories", "is_active", nullable=False)
    op.alter_column("risk_profession_categories", "profession_code", nullable=False)
    op.alter_column("risk_profession_categories", "profession_name", nullable=False)
    op.alter_column("risk_profession_categories", "risk_score", nullable=False)
    op.alter_column("risk_profession_categories", "is_active", nullable=False)

    op.create_foreign_key("fk_risk_business_categories_created_by_user", "risk_business_categories", "user", ["created_by"], ["id"])
    op.create_foreign_key("fk_risk_profession_categories_created_by_user", "risk_profession_categories", "user", ["created_by"], ["id"])

    op.drop_index(op.f("ix_risk_business_categories_category"), table_name="risk_business_categories")
    op.drop_index(op.f("ix_risk_business_categories_status"), table_name="risk_business_categories")
    op.drop_constraint("risk_business_categories_category_key", "risk_business_categories", type_="unique")
    op.drop_column("risk_business_categories", "category")
    op.drop_column("risk_business_categories", "score")
    op.drop_column("risk_business_categories", "status")

    op.drop_index(op.f("ix_risk_profession_categories_profession"), table_name="risk_profession_categories")
    op.drop_index(op.f("ix_risk_profession_categories_status"), table_name="risk_profession_categories")
    op.drop_constraint("risk_profession_categories_profession_key", "risk_profession_categories", type_="unique")
    op.drop_column("risk_profession_categories", "profession")
    op.drop_column("risk_profession_categories", "score")
    op.drop_column("risk_profession_categories", "status")


def downgrade() -> None:
    op.add_column("risk_business_categories", sa.Column("category", sa.String(), nullable=True))
    op.add_column("risk_business_categories", sa.Column("score", sa.Integer(), nullable=True))
    op.add_column("risk_business_categories", sa.Column("status", sa.String(), nullable=True))
    op.add_column("risk_profession_categories", sa.Column("profession", sa.String(), nullable=True))
    op.add_column("risk_profession_categories", sa.Column("score", sa.Integer(), nullable=True))
    op.add_column("risk_profession_categories", sa.Column("status", sa.String(), nullable=True))

    op.execute(
        """
        UPDATE risk_business_categories
        SET category = category_name,
            score = risk_score,
            status = CASE WHEN is_active THEN 'ACTIVE' ELSE 'INACTIVE' END
        """
    )
    op.execute(
        """
        UPDATE risk_profession_categories
        SET profession = profession_name,
            score = risk_score,
            status = CASE WHEN is_active THEN 'ACTIVE' ELSE 'INACTIVE' END
        """
    )

    op.alter_column("risk_business_categories", "category", nullable=False)
    op.alter_column("risk_business_categories", "score", nullable=False)
    op.alter_column("risk_business_categories", "status", nullable=False)
    op.alter_column("risk_profession_categories", "profession", nullable=False)
    op.alter_column("risk_profession_categories", "score", nullable=False)
    op.alter_column("risk_profession_categories", "status", nullable=False)

    op.drop_constraint("fk_risk_profession_categories_created_by_user", "risk_profession_categories", type_="foreignkey")
    op.drop_constraint("fk_risk_business_categories_created_by_user", "risk_business_categories", type_="foreignkey")
    op.drop_index(op.f("ix_risk_profession_categories_is_active"), table_name="risk_profession_categories")
    op.drop_index(op.f("ix_risk_profession_categories_profession_name"), table_name="risk_profession_categories")
    op.drop_index(op.f("ix_risk_profession_categories_profession_code"), table_name="risk_profession_categories")
    op.drop_index(op.f("ix_risk_business_categories_is_active"), table_name="risk_business_categories")
    op.drop_index(op.f("ix_risk_business_categories_category_name"), table_name="risk_business_categories")
    op.drop_index(op.f("ix_risk_business_categories_category_code"), table_name="risk_business_categories")

    op.drop_column("risk_profession_categories", "created_by")
    op.drop_column("risk_profession_categories", "is_active")
    op.drop_column("risk_profession_categories", "description")
    op.drop_column("risk_profession_categories", "risk_score")
    op.drop_column("risk_profession_categories", "profession_name")
    op.drop_column("risk_profession_categories", "profession_code")
    op.drop_column("risk_business_categories", "created_by")
    op.drop_column("risk_business_categories", "is_active")
    op.drop_column("risk_business_categories", "description")
    op.drop_column("risk_business_categories", "risk_score")
    op.drop_column("risk_business_categories", "category_name")
    op.drop_column("risk_business_categories", "category_code")

    op.create_index(op.f("ix_risk_profession_categories_status"), "risk_profession_categories", ["status"], unique=False)
    op.create_index(op.f("ix_risk_profession_categories_profession"), "risk_profession_categories", ["profession"], unique=True)
    op.create_unique_constraint("risk_profession_categories_profession_key", "risk_profession_categories", ["profession"])
    op.create_index(op.f("ix_risk_business_categories_status"), "risk_business_categories", ["status"], unique=False)
    op.create_index(op.f("ix_risk_business_categories_category"), "risk_business_categories", ["category"], unique=True)
    op.create_unique_constraint("risk_business_categories_category_key", "risk_business_categories", ["category"])
