from sqlalchemy import inspect, text

BUSINESS_CATEGORY_SEEDS = [
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

PROFESSION_CATEGORY_SEEDS = [
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


def ensure_schema_compatibility(sync_conn) -> None:
    inspector = inspect(sync_conn)
    table_names = set(inspector.get_table_names())
    if "risk_business_categories" in table_names:
        business_columns = {column["name"] for column in inspector.get_columns("risk_business_categories")}
        if "category_code" not in business_columns:
            sync_conn.execute(text("ALTER TABLE risk_business_categories ADD COLUMN category_code VARCHAR NULL"))
            business_columns.add("category_code")
        if "category_name" not in business_columns:
            sync_conn.execute(text("ALTER TABLE risk_business_categories ADD COLUMN category_name VARCHAR NULL"))
            business_columns.add("category_name")
        if "risk_score" not in business_columns:
            sync_conn.execute(text("ALTER TABLE risk_business_categories ADD COLUMN risk_score INTEGER NULL"))
            business_columns.add("risk_score")
        if "description" not in business_columns:
            sync_conn.execute(text("ALTER TABLE risk_business_categories ADD COLUMN description VARCHAR NULL"))
            business_columns.add("description")
        if "is_active" not in business_columns:
            sync_conn.execute(text("ALTER TABLE risk_business_categories ADD COLUMN is_active BOOLEAN NULL"))
            business_columns.add("is_active")
        if "created_by" not in business_columns:
            sync_conn.execute(text("ALTER TABLE risk_business_categories ADD COLUMN created_by INTEGER NULL"))
            business_columns.add("created_by")
        if {"category", "score", "status"}.issubset(business_columns):
            sync_conn.execute(
                text(
                    """
                    UPDATE risk_business_categories
                    SET category_name = COALESCE(category_name, category),
                        category_code = COALESCE(NULLIF(category_code, ''), upper(regexp_replace(category, '[^a-zA-Z0-9]+', '_', 'g'))),
                        risk_score = COALESCE(risk_score, score),
                        is_active = COALESCE(is_active, status = 'ACTIVE')
                    WHERE category_name IS NULL OR category_code IS NULL OR risk_score IS NULL OR is_active IS NULL
                    """
                )
            )
        sync_conn.execute(text("UPDATE risk_business_categories SET is_active = TRUE WHERE is_active IS NULL"))
        sync_conn.execute(text("UPDATE risk_business_categories SET risk_score = 3 WHERE risk_score IS NULL"))
        sync_conn.execute(
            text(
                """
                UPDATE risk_business_categories
                SET category_name = COALESCE(category_name, category_code, 'Uncategorized ' || id::text),
                    category_code = COALESCE(category_code, 'UNCATEGORIZED_' || id::text)
                WHERE category_name IS NULL OR category_code IS NULL
                """
            )
        )
        sync_conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_risk_business_categories_category_code ON risk_business_categories (category_code)"))
        sync_conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_risk_business_categories_category_name ON risk_business_categories (category_name)"))
        sync_conn.execute(text("CREATE INDEX IF NOT EXISTS ix_risk_business_categories_is_active ON risk_business_categories (is_active)"))
        for code, name, score in BUSINESS_CATEGORY_SEEDS:
            if {"category", "score", "status"}.issubset(business_columns):
                sync_conn.execute(
                    text(
                        """
                        INSERT INTO risk_business_categories
                            (category, score, status, category_code, category_name, risk_score, description, is_active, created_at, updated_at)
                        VALUES
                            (:name, :score, 'ACTIVE', :code, :name, :score, 'Seeded from approved risk category examples.', TRUE, NOW(), NOW())
                        ON CONFLICT (category_code) DO UPDATE
                        SET category_name = EXCLUDED.category_name,
                            risk_score = EXCLUDED.risk_score,
                            category = EXCLUDED.category,
                            score = EXCLUDED.score,
                            status = 'ACTIVE',
                            is_active = TRUE,
                            updated_at = NOW()
                        """
                    ),
                    {"code": code, "name": name, "score": score},
                )
            else:
                sync_conn.execute(
                    text(
                        """
                        INSERT INTO risk_business_categories
                            (category_code, category_name, risk_score, description, is_active, created_at, updated_at)
                        VALUES
                            (:code, :name, :score, 'Seeded from approved risk category examples.', TRUE, NOW(), NOW())
                        ON CONFLICT (category_code) DO UPDATE
                        SET category_name = EXCLUDED.category_name,
                            risk_score = EXCLUDED.risk_score,
                            is_active = TRUE,
                            updated_at = NOW()
                        """
                    ),
                    {"code": code, "name": name, "score": score},
                )
        if {"category", "score", "status"}.issubset(business_columns):
            sync_conn.execute(text("ALTER TABLE risk_business_categories ALTER COLUMN category DROP NOT NULL"))
            sync_conn.execute(text("ALTER TABLE risk_business_categories ALTER COLUMN score DROP NOT NULL"))
            sync_conn.execute(text("ALTER TABLE risk_business_categories ALTER COLUMN status DROP NOT NULL"))

    if "risk_profession_categories" in table_names:
        profession_columns = {column["name"] for column in inspector.get_columns("risk_profession_categories")}
        if "profession_code" not in profession_columns:
            sync_conn.execute(text("ALTER TABLE risk_profession_categories ADD COLUMN profession_code VARCHAR NULL"))
            profession_columns.add("profession_code")
        if "profession_name" not in profession_columns:
            sync_conn.execute(text("ALTER TABLE risk_profession_categories ADD COLUMN profession_name VARCHAR NULL"))
            profession_columns.add("profession_name")
        if "risk_score" not in profession_columns:
            sync_conn.execute(text("ALTER TABLE risk_profession_categories ADD COLUMN risk_score INTEGER NULL"))
            profession_columns.add("risk_score")
        if "description" not in profession_columns:
            sync_conn.execute(text("ALTER TABLE risk_profession_categories ADD COLUMN description VARCHAR NULL"))
            profession_columns.add("description")
        if "is_active" not in profession_columns:
            sync_conn.execute(text("ALTER TABLE risk_profession_categories ADD COLUMN is_active BOOLEAN NULL"))
            profession_columns.add("is_active")
        if "created_by" not in profession_columns:
            sync_conn.execute(text("ALTER TABLE risk_profession_categories ADD COLUMN created_by INTEGER NULL"))
            profession_columns.add("created_by")
        if {"profession", "score", "status"}.issubset(profession_columns):
            sync_conn.execute(
                text(
                    """
                    UPDATE risk_profession_categories
                    SET profession_name = COALESCE(profession_name, profession),
                        profession_code = COALESCE(NULLIF(profession_code, ''), upper(regexp_replace(profession, '[^a-zA-Z0-9]+', '_', 'g'))),
                        risk_score = COALESCE(risk_score, score),
                        is_active = COALESCE(is_active, status = 'ACTIVE')
                    WHERE profession_name IS NULL OR profession_code IS NULL OR risk_score IS NULL OR is_active IS NULL
                    """
                )
            )
        sync_conn.execute(text("UPDATE risk_profession_categories SET is_active = TRUE WHERE is_active IS NULL"))
        sync_conn.execute(text("UPDATE risk_profession_categories SET risk_score = 3 WHERE risk_score IS NULL"))
        sync_conn.execute(
            text(
                """
                UPDATE risk_profession_categories
                SET profession_name = COALESCE(profession_name, profession_code, 'Uncategorized ' || id::text),
                    profession_code = COALESCE(profession_code, 'UNCATEGORIZED_' || id::text)
                WHERE profession_name IS NULL OR profession_code IS NULL
                """
            )
        )
        sync_conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_risk_profession_categories_profession_code ON risk_profession_categories (profession_code)"))
        sync_conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_risk_profession_categories_profession_name ON risk_profession_categories (profession_name)"))
        sync_conn.execute(text("CREATE INDEX IF NOT EXISTS ix_risk_profession_categories_is_active ON risk_profession_categories (is_active)"))
        for code, name, score in PROFESSION_CATEGORY_SEEDS:
            if {"profession", "score", "status"}.issubset(profession_columns):
                sync_conn.execute(
                    text(
                        """
                        INSERT INTO risk_profession_categories
                            (profession, score, status, profession_code, profession_name, risk_score, description, is_active, created_at, updated_at)
                        VALUES
                            (:name, :score, 'ACTIVE', :code, :name, :score, 'Seeded from approved risk profession examples.', TRUE, NOW(), NOW())
                        ON CONFLICT (profession_code) DO UPDATE
                        SET profession_name = EXCLUDED.profession_name,
                            risk_score = EXCLUDED.risk_score,
                            profession = EXCLUDED.profession,
                            score = EXCLUDED.score,
                            status = 'ACTIVE',
                            is_active = TRUE,
                            updated_at = NOW()
                        """
                    ),
                    {"code": code, "name": name, "score": score},
                )
            else:
                sync_conn.execute(
                    text(
                        """
                        INSERT INTO risk_profession_categories
                            (profession_code, profession_name, risk_score, description, is_active, created_at, updated_at)
                        VALUES
                            (:code, :name, :score, 'Seeded from approved risk profession examples.', TRUE, NOW(), NOW())
                        ON CONFLICT (profession_code) DO UPDATE
                        SET profession_name = EXCLUDED.profession_name,
                            risk_score = EXCLUDED.risk_score,
                            is_active = TRUE,
                            updated_at = NOW()
                        """
                    ),
                    {"code": code, "name": name, "score": score},
                )
        if {"profession", "score", "status"}.issubset(profession_columns):
            sync_conn.execute(text("ALTER TABLE risk_profession_categories ALTER COLUMN profession DROP NOT NULL"))
            sync_conn.execute(text("ALTER TABLE risk_profession_categories ALTER COLUMN score DROP NOT NULL"))
            sync_conn.execute(text("ALTER TABLE risk_profession_categories ALTER COLUMN status DROP NOT NULL"))

    if "customer_identity_profiles" in table_names:
        profile_columns = {column["name"] for column in inspector.get_columns("customer_identity_profiles")}
        for column_name in ("product_type", "business_category", "residency_status", "onboarding_channel"):
            if column_name not in profile_columns:
                sync_conn.execute(text(f"ALTER TABLE customer_identity_profiles ADD COLUMN {column_name} VARCHAR NULL"))

    if "customer_risk_factor_scores" in table_names:
        factor_columns = {column["name"] for column in inspector.get_columns("customer_risk_factor_scores")}
        nullable_columns = {
            "factor_code": "VARCHAR",
            "source_table": "VARCHAR",
            "selected_value": "VARCHAR",
            "rule_id": "INTEGER",
        }
        for column_name, column_type in nullable_columns.items():
            if column_name not in factor_columns:
                sync_conn.execute(text(f"ALTER TABLE customer_risk_factor_scores ADD COLUMN {column_name} {column_type} NULL"))
        if "match_status" not in factor_columns:
            sync_conn.execute(text("ALTER TABLE customer_risk_factor_scores ADD COLUMN match_status VARCHAR NOT NULL DEFAULT 'matched'"))
        sync_conn.execute(text("CREATE INDEX IF NOT EXISTS ix_customer_risk_factor_scores_factor_code ON customer_risk_factor_scores (factor_code)"))
        sync_conn.execute(text("CREATE INDEX IF NOT EXISTS ix_customer_risk_factor_scores_source_table ON customer_risk_factor_scores (source_table)"))
        sync_conn.execute(text("CREATE INDEX IF NOT EXISTS ix_customer_risk_factor_scores_selected_value ON customer_risk_factor_scores (selected_value)"))
        sync_conn.execute(text("CREATE INDEX IF NOT EXISTS ix_customer_risk_factor_scores_rule_id ON customer_risk_factor_scores (rule_id)"))
        sync_conn.execute(text("CREATE INDEX IF NOT EXISTS ix_customer_risk_factor_scores_match_status ON customer_risk_factor_scores (match_status)"))

    if "risk_rule_versions" in table_names:
        rule_columns = {column["name"] for column in inspector.get_columns("risk_rule_versions")}
        if "created_by" not in rule_columns:
            sync_conn.execute(text("ALTER TABLE risk_rule_versions ADD COLUMN created_by INTEGER NULL"))
        if "change_notes" not in rule_columns:
            sync_conn.execute(text("ALTER TABLE risk_rule_versions ADD COLUMN change_notes VARCHAR NULL"))
        if "activated_at" not in rule_columns:
            sync_conn.execute(text("ALTER TABLE risk_rule_versions ADD COLUMN activated_at TIMESTAMP NULL"))
        if "retired_at" not in rule_columns:
            sync_conn.execute(text("ALTER TABLE risk_rule_versions ADD COLUMN retired_at TIMESTAMP NULL"))

    if "onboarding_session" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("onboarding_session")}
    if "activation_status" not in columns:
        sync_conn.execute(
            text(
                """
                ALTER TABLE onboarding_session
                ADD COLUMN activation_status VARCHAR NOT NULL DEFAULT 'blocked'
                """
            )
        )
        columns.add("activation_status")

    if "workflow_state" not in columns:
        sync_conn.execute(
            text(
                """
                ALTER TABLE onboarding_session
                ADD COLUMN workflow_state VARCHAR NOT NULL DEFAULT 'ONBOARDING_STARTED'
                """
            )
        )
        sync_conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_onboarding_session_workflow_state
                ON onboarding_session (workflow_state)
                """
            )
        )
        columns.add("workflow_state")

    if "completed_steps" not in columns:
        sync_conn.execute(
            text(
                """
                ALTER TABLE onboarding_session
                ADD COLUMN completed_steps JSON NOT NULL DEFAULT '[]'::json
                """
            )
        )
        columns.add("completed_steps")

    if "last_resumed_at" not in columns:
        sync_conn.execute(
            text(
                """
                ALTER TABLE onboarding_session
                ADD COLUMN last_resumed_at TIMESTAMP NULL
                """
            )
        )
        columns.add("last_resumed_at")

    if "resume_count" not in columns:
        sync_conn.execute(
            text(
                """
                ALTER TABLE onboarding_session
                ADD COLUMN resume_count INTEGER NOT NULL DEFAULT 0
                """
            )
        )
        columns.add("resume_count")

    if {"workflow_state", "completed_steps"}.issubset(columns):
        sync_conn.execute(
            text(
                """
                UPDATE onboarding_session AS s
                SET workflow_state = CASE
                    WHEN s.status = 'completed' THEN 'ONBOARDING_COMPLETED'
                    WHEN sr.status = 'REJECTED' THEN 'ONBOARDING_REJECTED'
                    WHEN cra.edd_required = TRUE AND cc.status = 'OPEN' THEN 'EDD_IN_REVIEW'
                    WHEN cra.edd_required = TRUE THEN 'EDD_REQUIRED'
                    WHEN sr.status = 'REVIEW_REQUIRED' THEN 'EDD_IN_REVIEW'
                    WHEN sr.status = 'SCREENING_IN_PROGRESS' THEN 'SCREENING_IN_PROGRESS'
                    WHEN sr.status = 'SCREENING_PENDING' THEN 'SCREENING_PENDING'
                    WHEN sr.status = 'APPROVED' THEN 'SCREENING_COMPLETED'
                    WHEN sig.id IS NOT NULL THEN 'SIGNATURE_COMPLETED'
                    WHEN cip.status = 'IDENTITY_FORM_COMPLETED' THEN 'IDENTITY_FORM_COMPLETED'
                    WHEN cip.status IN ('IDENTITY_FORM_DRAFT_SAVED', 'IDENTITY_FORM_IN_PROGRESS') THEN 'IDENTITY_FORM_IN_PROGRESS'
                    WHEN cip.status = 'IDENTITY_FORM_PENDING' THEN 'IDENTITY_FORM_PENDING'
                    WHEN ocr.id IS NOT NULL THEN 'OCR_COMPLETED'
                    WHEN face.id IS NOT NULL THEN 'FACE_VERIFICATION_COMPLETED'
                    ELSE COALESCE(NULLIF(s.workflow_state, 'ONBOARDING_STARTED'), 'ONBOARDING_STARTED')
                END,
                completed_steps = CASE
                    WHEN s.status = 'completed' THEN '["face_verification", "ocr_extraction", "identity_form", "signature_capture", "screening"]'::json
                    WHEN sig.id IS NOT NULL THEN '["face_verification", "ocr_extraction", "identity_form", "signature_capture"]'::json
                    WHEN cip.status = 'IDENTITY_FORM_COMPLETED' THEN '["face_verification", "ocr_extraction", "identity_form"]'::json
                    WHEN ocr.id IS NOT NULL THEN '["face_verification", "ocr_extraction"]'::json
                    WHEN face.id IS NOT NULL THEN '["face_verification"]'::json
                    ELSE COALESCE(s.completed_steps, '[]'::json)
                END
                FROM onboarding_session AS base
                LEFT JOIN onboarding_face_verification AS face ON face.session_id = base.id
                LEFT JOIN onboarding_ocr_extraction AS ocr ON ocr.session_id = base.id
                LEFT JOIN customer_identity_profiles AS cip ON cip.session_id = base.id
                LEFT JOIN onboarding_signature_capture AS sig ON sig.session_id = base.id
                LEFT JOIN LATERAL (
                    SELECT *
                    FROM screening_request AS sr_inner
                    WHERE sr_inner.session_id = base.id
                    ORDER BY sr_inner.created_at DESC, sr_inner.id DESC
                    LIMIT 1
                ) AS sr ON TRUE
                LEFT JOIN LATERAL (
                    SELECT *
                    FROM customer_risk_assessments AS cra_inner
                    WHERE cra_inner.session_id = base.id
                    ORDER BY cra_inner.calculated_at DESC, cra_inner.id DESC
                    LIMIT 1
                ) AS cra ON TRUE
                LEFT JOIN compliance_case AS cc ON cc.screening_request_id = sr.id
                WHERE s.id = base.id
                """
            )
        )
        sync_conn.execute(text("ALTER TABLE onboarding_session ALTER COLUMN workflow_state DROP DEFAULT"))
        sync_conn.execute(text("ALTER TABLE onboarding_session ALTER COLUMN completed_steps DROP DEFAULT"))
        sync_conn.execute(text("ALTER TABLE onboarding_session ALTER COLUMN resume_count DROP DEFAULT"))
        sync_conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_onboarding_session_activation_status
                ON onboarding_session (activation_status)
                """
            )
        )
        sync_conn.execute(text("ALTER TABLE onboarding_session ALTER COLUMN activation_status DROP DEFAULT"))
