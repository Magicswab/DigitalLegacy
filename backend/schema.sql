PRAGMA foreign_keys = ON;

-- 1. users
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('owner', 'legal_advisor', 'trustee', 'beneficiary')),
    public_key TEXT,
    public_key_status TEXT NOT NULL DEFAULT 'active'
        CHECK (public_key_status IN ('active', 'pending', 'rotated', 'disabled')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);


-- 2. legacy_plans
CREATE TABLE IF NOT EXISTS legacy_plans (
    plan_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'drafting'
        CHECK (status IN ('drafting', 'active', 'inheritance_ready', 'closed')),
    share_threshold INTEGER NOT NULL DEFAULT 3,
    share_total INTEGER NOT NULL DEFAULT 5,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    finalized_at TEXT,
    FOREIGN KEY (owner_id) REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_legacy_plans_owner_id ON legacy_plans(owner_id);
CREATE INDEX IF NOT EXISTS idx_legacy_plans_status ON legacy_plans(status);


-- 3. plan_participants
CREATE TABLE IF NOT EXISTS plan_participants (
    participant_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    participant_role TEXT NOT NULL
        CHECK (participant_role IN ('legal_advisor', 'trustee', 'beneficiary')),
    is_required INTEGER NOT NULL DEFAULT 1 CHECK (is_required IN (0, 1)),
    invited_at TEXT NOT NULL,
    accepted_at TEXT,
    status TEXT NOT NULL DEFAULT 'invited'
        CHECK (status IN ('invited', 'accepted', 'revoked')),
    FOREIGN KEY (plan_id) REFERENCES legacy_plans(plan_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    UNIQUE (plan_id, user_id, participant_role)
);

CREATE INDEX IF NOT EXISTS idx_plan_participants_plan_id ON plan_participants(plan_id);
CREATE INDEX IF NOT EXISTS idx_plan_participants_user_id ON plan_participants(user_id);
CREATE INDEX IF NOT EXISTS idx_plan_participants_role ON plan_participants(participant_role);


-- 4. assets
CREATE TABLE IF NOT EXISTS assets (
    asset_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    asset_name TEXT NOT NULL,
    asset_type TEXT NOT NULL
        CHECK (asset_type IN ('credential', 'document', 'media')),
    mime_type TEXT,
    storage_path TEXT NOT NULL,
    original_size INTEGER,
    encrypted_size INTEGER,
    file_hash TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
    FOREIGN KEY (plan_id) REFERENCES legacy_plans(plan_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (owner_id) REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_assets_plan_id ON assets(plan_id);
CREATE INDEX IF NOT EXISTS idx_assets_owner_id ON assets(owner_id);
CREATE INDEX IF NOT EXISTS idx_assets_asset_type ON assets(asset_type);


-- 5. key_vault
CREATE TABLE IF NOT EXISTS key_vault (
    vault_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL UNIQUE,
    owner_id TEXT NOT NULL,
    encrypted_vault_blob BLOB NOT NULL,
    vault_nonce BLOB NOT NULL,
    vault_version INTEGER NOT NULL DEFAULT 1,
    mk_version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL,
    integrity_hash TEXT,
    FOREIGN KEY (plan_id) REFERENCES legacy_plans(plan_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (owner_id) REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_key_vault_owner_id ON key_vault(owner_id);


-- 6. system_state
CREATE TABLE IF NOT EXISTS system_state (
    state_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL UNIQUE,
    owner_id TEXT NOT NULL,
    current_state TEXT NOT NULL CHECK (
    current_state IN (
        'active',
        'pending_confirmation',
        'escalated',
        'inheritance_activated',
        'recovered'
    )
    ) DEFAULT 'active',
    last_activity_at TEXT NOT NULL,
    pending_started_at TEXT,
    last_checkin_at TEXT,
    escalated_at TEXT,
    recovered_at TEXT
    escalated_at TEXT,
    inheritance_activated_at TEXT,
    inactivity_threshold_sec INTEGER NOT NULL DEFAULT 300,
    grace_period_sec INTEGER NOT NULL DEFAULT 120,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (plan_id) REFERENCES legacy_plans(plan_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (owner_id) REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_system_state_owner_id ON system_state(owner_id);
CREATE INDEX IF NOT EXISTS idx_system_state_current_state ON system_state(current_state);


-- 7. assigned_shares
CREATE TABLE IF NOT EXISTS assigned_shares (
    share_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    recipient_id TEXT NOT NULL,
    recipient_role TEXT NOT NULL CHECK (recipient_role IN ('owner', 'legal_advisor', 'trustee', 'beneficiary')),
    share_scope TEXT NOT NULL DEFAULT 'inheritance' CHECK (share_scope IN ('inheritance', 'operational')),
    encrypted_share_blob BLOB NOT NULL,
    share_index INTEGER NOT NULL,
    issued_at TEXT NOT NULL,
    viewed_at TEXT,
    delivery_status TEXT NOT NULL DEFAULT 'issued'
        CHECK (delivery_status IN ('issued', 'viewed', 'expired')),
    FOREIGN KEY (plan_id) REFERENCES legacy_plans(plan_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (recipient_id) REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    UNIQUE (plan_id, recipient_id),
    UNIQUE (plan_id, share_scope, share_index)
);

CREATE INDEX IF NOT EXISTS idx_assigned_shares_plan_id ON assigned_shares(plan_id);
CREATE INDEX IF NOT EXISTS idx_assigned_shares_recipient_id ON assigned_shares(recipient_id);


-- 8. recovery_sessions
CREATE TABLE IF NOT EXISTS recovery_sessions (
    recovery_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'completed', 'expired', 'cancelled')),
    threshold_required INTEGER NOT NULL DEFAULT 3,
    trustee_required INTEGER NOT NULL DEFAULT 1 CHECK (trustee_required IN (0, 1)),
    beneficiary_required_count INTEGER NOT NULL DEFAULT 2,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY (plan_id) REFERENCES legacy_plans(plan_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_recovery_sessions_plan_id ON recovery_sessions(plan_id);
CREATE INDEX IF NOT EXISTS idx_recovery_sessions_status ON recovery_sessions(status);


-- 9. submitted_shares
CREATE TABLE IF NOT EXISTS submitted_shares (
    submission_id TEXT PRIMARY KEY,
    recovery_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    actor_role TEXT NOT NULL
        CHECK (actor_role IN ('trustee', 'beneficiary')),
    share_id TEXT NOT NULL,
    submitted_share_payload TEXT,
    submitted_at TEXT NOT NULL,
    is_valid INTEGER NOT NULL DEFAULT 1 CHECK (is_valid IN (0, 1)),
    validation_note TEXT,
    FOREIGN KEY (recovery_id) REFERENCES recovery_sessions(recovery_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (actor_id) REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (share_id) REFERENCES assigned_shares(share_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    UNIQUE (recovery_id, actor_id),
    UNIQUE (recovery_id, share_id)
);

CREATE INDEX IF NOT EXISTS idx_submitted_shares_recovery_id ON submitted_shares(recovery_id);
CREATE INDEX IF NOT EXISTS idx_submitted_shares_actor_id ON submitted_shares(actor_id);
CREATE INDEX IF NOT EXISTS idx_submitted_shares_actor_role ON submitted_shares(actor_role);


-- 10. recovery_packages
CREATE TABLE IF NOT EXISTS recovery_packages (
    package_id TEXT PRIMARY KEY,
    recovery_id TEXT NOT NULL,
    recipient_id TEXT NOT NULL,
    recipient_role TEXT NOT NULL
        CHECK (recipient_role = 'beneficiary'),
    encrypted_package_blob BLOB NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    delivered_at TEXT,
    package_status TEXT NOT NULL DEFAULT 'available'
        CHECK (package_status IN ('available', 'viewed', 'expired')),
    FOREIGN KEY (recovery_id) REFERENCES recovery_sessions(recovery_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (recipient_id) REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    UNIQUE (recovery_id, recipient_id)
);

CREATE INDEX IF NOT EXISTS idx_recovery_packages_recovery_id ON recovery_packages(recovery_id);
CREATE INDEX IF NOT EXISTS idx_recovery_packages_recipient_id ON recovery_packages(recipient_id);


-- 11. audit_logs
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id TEXT PRIMARY KEY,
    plan_id TEXT,
    actor_id TEXT,
    action_type TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    occurred_at TEXT NOT NULL,
    details_json TEXT,
    integrity_hash TEXT,
    FOREIGN KEY (plan_id) REFERENCES legacy_plans(plan_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    FOREIGN KEY (actor_id) REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_plan_id ON audit_logs(plan_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_id ON audit_logs(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action_type ON audit_logs(action_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_occurred_at ON audit_logs(occurred_at);

CREATE TABLE IF NOT EXISTS plan_master_keys_temp (
    plan_id TEXT PRIMARY KEY,
    mk_blob BLOB NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (plan_id) REFERENCES legacy_plans(plan_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS plan_recovery_secrets_temp (
    plan_id TEXT PRIMARY KEY,
    recovery_secret_blob BLOB NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (plan_id) REFERENCES legacy_plans(plan_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS plan_inheritance_keys_temp (
    plan_id TEXT PRIMARY KEY,
    ik_key_blob BLOB NOT NULL,
    wrapped_mk_ik_blob BLOB NOT NULL,
    wrapped_mk_ik_nonce BLOB NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (plan_id) REFERENCES legacy_plans(plan_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS plan_operational_keys_temp (
    plan_id TEXT PRIMARY KEY,
    ok_key_blob BLOB NOT NULL,
    wrapped_mk_ok_blob BLOB NOT NULL,
    wrapped_mk_ok_nonce BLOB NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (plan_id) REFERENCES legacy_plans(plan_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS deadman_policies (
    policy_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL UNIQUE,
    checkin_interval_days INTEGER NOT NULL,
    grace_period_days INTEGER NOT NULL,
    is_enabled INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (plan_id) REFERENCES legacy_plans(plan_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS notifications (
    notification_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    plan_id TEXT NOT NULL,
    notification_type TEXT NOT NULL,
    message TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES legacy_plans(plan_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS state_transition_approvals (
    approval_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    requested_transition TEXT NOT NULL,
    approver_id TEXT NOT NULL,
    approver_role TEXT NOT NULL,
    approval_status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(plan_id, requested_transition, approver_id),
    FOREIGN KEY (plan_id) REFERENCES legacy_plans(plan_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (approver_id) REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);


