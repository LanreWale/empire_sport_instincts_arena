-- ═══════════════════════════════════════════════════════════
-- EMPIRE SPORT INSTINCTS ARENA — Database Schema
-- Premium PostgreSQL 15+ | Where Data Meets Destiny
-- ═══════════════════════════════════════════════════════════

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ═══════════════════════════════════════════════════════════
-- CORE TABLES — Foundation of the ARENA
-- ═══════════════════════════════════════════════════════════

-- Sports/Leagues master data
CREATE TABLE sports (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL,
    display_name VARCHAR(50),
    icon VARCHAR(10),
    color VARCHAR(7),
    enabled BOOLEAN DEFAULT TRUE,
    tier VARCHAR(20) DEFAULT 'standard',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO sports (name, category, display_name, icon, color, tier) VALUES 
    ('football', 'team', 'Football', '⚽', '#1a5f1a', 'gold'),
    ('nba', 'team', 'NBA', '🏀', '#ff6600', 'gold'),
    ('nfl', 'team', 'NFL', '🏈', '#8B4513', 'premium'),
    ('tennis', 'individual', 'Tennis', '🎾', '#CCFF00', 'premium');

-- Teams/Players
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sport_id INTEGER REFERENCES sports(id),
    name VARCHAR(100) NOT NULL,
    entity_type VARCHAR(20) NOT NULL CHECK (entity_type IN ('team', 'player')),
    external_id VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(sport_id, external_id)
);

-- Matches/Fixtures
CREATE TABLE fixtures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sport_id INTEGER REFERENCES sports(id),
    home_entity_id UUID REFERENCES entities(id),
    away_entity_id UUID REFERENCES entities(id),
    fixture_date TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'live', 'completed', 'postponed', 'cancelled')),
    venue VARCHAR(100),
    competition VARCHAR(100),
    season VARCHAR(20),
    round VARCHAR(50),
    external_id VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_fixtures_date ON fixtures(fixture_date);
CREATE INDEX idx_fixtures_status ON fixtures(status);
CREATE INDEX idx_fixtures_sport ON fixtures(sport_id);

-- Results
CREATE TABLE results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fixture_id UUID REFERENCES fixtures(id) ON DELETE CASCADE,
    home_score NUMERIC,
    away_score NUMERIC,
    result_type VARCHAR(20) CHECK (result_type IN ('regular', 'extra_time', 'penalties')),
    home_possession NUMERIC,
    away_possession NUMERIC,
    metadata JSONB,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ═══════════════════════════════════════════════════════════
-- FEATURES & MODELS — ARENA FORGE Intelligence
-- ═══════════════════════════════════════════════════════════

-- Feature Store
CREATE TABLE features (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fixture_id UUID REFERENCES fixtures(id) ON DELETE CASCADE,
    feature_set JSONB NOT NULL,
    feature_version VARCHAR(20) NOT NULL DEFAULT 'v1.0-premium',
    feature_category VARCHAR(50),
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    module VARCHAR(50) DEFAULT 'ARENA FORGE'
);

CREATE INDEX idx_features_fixture ON features(fixture_id);
CREATE INDEX idx_features_version ON features(feature_version);

-- Model Registry
CREATE TABLE models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sport_id INTEGER REFERENCES sports(id),
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    hyperparameters JSONB,
    metrics JSONB,
    artifact_path VARCHAR(255),
    is_active BOOLEAN DEFAULT FALSE,
    tier VARCHAR(20) DEFAULT 'standard',
    trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(sport_id, model_name, model_version)
);

-- ═══════════════════════════════════════════════════════════
-- PREDICTIONS & ODDS — Market Intelligence
-- ═══════════════════════════════════════════════════════════

-- Odds tracking
CREATE TABLE odds (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fixture_id UUID REFERENCES fixtures(id) ON DELETE CASCADE,
    bookmaker VARCHAR(50) NOT NULL,
    market VARCHAR(50) NOT NULL,
    outcome VARCHAR(50) NOT NULL,
    odds_decimal NUMERIC NOT NULL,
    odds_american INTEGER,
    implied_probability NUMERIC,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_live BOOLEAN DEFAULT FALSE,
    tier VARCHAR(20) DEFAULT 'standard'
);

CREATE INDEX idx_odds_fixture ON odds(fixture_id);
CREATE INDEX idx_odds_bookmaker ON odds(bookmaker);
CREATE INDEX idx_odds_tier ON odds(tier);

-- Predictions
CREATE TABLE predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fixture_id UUID REFERENCES fixtures(id) ON DELETE CASCADE,
    model_id UUID REFERENCES models(id),
    predicted_home_prob NUMERIC,
    predicted_draw_prob NUMERIC,
    predicted_away_prob NUMERIC,
    predicted_spread NUMERIC,
    predicted_total NUMERIC,
    confidence_score NUMERIC,
    uncertainty_lower NUMERIC,
    uncertainty_upper NUMERIC,
    features_used JSONB,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    module VARCHAR(50) DEFAULT 'ARENA FORGE'
);

CREATE INDEX idx_predictions_fixture ON predictions(fixture_id);
CREATE INDEX idx_predictions_model ON predictions(model_id);

-- Value bets (EV analysis)
CREATE TABLE value_bets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prediction_id UUID REFERENCES predictions(id),
    odds_id UUID REFERENCES odds(id),
    expected_value NUMERIC NOT NULL,
    edge_percentage NUMERIC,
    kelly_fraction NUMERIC,
    recommended_stake NUMERIC,
    confidence_tier VARCHAR(20) CHECK (confidence_tier IN ('high', 'medium', 'low')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'tracked', 'won', 'lost', 'void')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    module VARCHAR(50) DEFAULT 'COMMAND CENTRE'
);

-- ═══════════════════════════════════════════════════════════
-- RISK MANAGEMENT — COMMAND CENTRE Capital Protection
-- ═══════════════════════════════════════════════════════════

-- Bankroll tracking
CREATE TABLE bankroll (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    balance NUMERIC NOT NULL,
    peak_balance NUMERIC NOT NULL,
    drawdown_pct NUMERIC,
    total_bets INTEGER DEFAULT 0,
    total_won INTEGER DEFAULT 0,
    total_lost INTEGER DEFAULT 0,
    total_void INTEGER DEFAULT 0,
    roi_pct NUMERIC,
    sharpe_ratio NUMERIC,
    currency VARCHAR(3) DEFAULT 'USD',
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    module VARCHAR(50) DEFAULT 'COMMAND CENTRE'
);

-- Bet history
CREATE TABLE bet_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    value_bet_id UUID REFERENCES value_bets(id),
    stake NUMERIC NOT NULL,
    odds_taken NUMERIC NOT NULL,
    potential_return NUMERIC,
    actual_return NUMERIC,
    profit_loss NUMERIC,
    bankroll_after NUMERIC,
    bet_type VARCHAR(50),
    notes TEXT,
    placed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    settled_at TIMESTAMP,
    module VARCHAR(50) DEFAULT 'COMMAND CENTRE'
);

-- Drawdown protection log
CREATE TABLE drawdown_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    peak_balance NUMERIC,
    current_balance NUMERIC,
    drawdown_pct NUMERIC,
    status VARCHAR(20) CHECK (status IN ('NORMAL', 'CAUTION', 'PROTECTED', 'LOCKED', 'LIMITED')),
    cooldown_until TIMESTAMP,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    module VARCHAR(50) DEFAULT 'COMMAND CENTRE'
);

-- ═══════════════════════════════════════════════════════════
-- AUDIT & LOGGING — ARENA System Intelligence
-- ═══════════════════════════════════════════════════════════

CREATE TABLE system_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level VARCHAR(20) NOT NULL,
    component VARCHAR(50) NOT NULL,
    module VARCHAR(50),
    message TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_logs_level ON system_logs(level);
CREATE INDEX idx_logs_component ON system_logs(component);
CREATE INDEX idx_logs_module ON system_logs(module);
CREATE INDEX idx_logs_created ON system_logs(created_at);

-- ═══════════════════════════════════════════════════════════
-- VIEWS — Premium ARENA Analytics
-- ═══════════════════════════════════════════════════════════

CREATE VIEW upcoming_fixtures AS
SELECT 
    f.id,
    s.name as sport,
    s.display_name,
    s.icon,
    s.color,
    f.fixture_date,
    f.competition,
    f.season,
    f.status,
    h.name as home_team,
    a.name as away_team
FROM fixtures f
JOIN sports s ON f.sport_id = s.id
LEFT JOIN entities h ON f.home_entity_id = h.id
LEFT JOIN entities a ON f.away_entity_id = a.id
WHERE f.fixture_date > CURRENT_TIMESTAMP
AND f.status = 'scheduled'
ORDER BY f.fixture_date;

CREATE VIEW model_performance AS
SELECT 
    m.sport_id,
    m.model_name,
    m.model_version,
    m.model_type,
    m.tier,
    m.metrics->>'accuracy' as accuracy,
    m.metrics->>'precision' as precision,
    m.metrics->>'recall' as recall,
    m.metrics->>'f1' as f1_score,
    m.metrics->>'log_loss' as log_loss,
    m.metrics->>'roc_auc' as roc_auc,
    m.is_active,
    m.trained_at
FROM models m
ORDER BY m.trained_at DESC;

CREATE VIEW active_value_opportunities AS
SELECT 
    v.id,
    f.fixture_date,
    s.name as sport,
    s.display_name,
    s.icon,
    s.color,
    h.name as home_team,
    a.name as away_team,
    v.expected_value,
    v.edge_percentage,
    v.kelly_fraction,
    v.recommended_stake,
    v.confidence_tier,
    o.bookmaker,
    o.market,
    o.odds_decimal,
    o.tier as odds_tier
FROM value_bets v
JOIN predictions p ON v.prediction_id = p.id
JOIN fixtures f ON p.fixture_id = f.id
JOIN sports s ON f.sport_id = s.id
LEFT JOIN entities h ON f.home_entity_id = h.id
LEFT JOIN entities a ON f.away_entity_id = a.id
JOIN odds o ON v.odds_id = o.id
WHERE v.status = 'pending'
AND v.expected_value > 0
ORDER BY v.expected_value DESC;

CREATE VIEW bankroll_summary AS
SELECT 
    b.balance,
    b.peak_balance,
    b.drawdown_pct,
    b.total_bets,
    b.total_won,
    b.total_lost,
    b.total_void,
    b.roi_pct,
    b.sharpe_ratio,
    b.currency,
    b.recorded_at,
    CASE 
        WHEN b.drawdown_pct >= 0.20 THEN 'LOCKED'
        WHEN b.drawdown_pct >= 0.15 THEN 'PROTECTED'
        WHEN b.drawdown_pct >= 0.10 THEN 'CAUTION'
        ELSE 'NORMAL'
    END as status
FROM bankroll b
ORDER BY b.recorded_at DESC
LIMIT 1;

CREATE VIEW daily_performance AS
SELECT 
    DATE(bh.placed_at) as date,
    COUNT(*) as total_bets,
    SUM(CASE WHEN bh.profit_loss > 0 THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN bh.profit_loss < 0 THEN 1 ELSE 0 END) as losses,
    SUM(CASE WHEN bh.profit_loss = 0 THEN 1 ELSE 0 END) as voids,
    SUM(bh.profit_loss) as net_profit,
    SUM(bh.stake) as total_staked,
    ROUND(SUM(bh.profit_loss) / NULLIF(SUM(bh.stake), 0) * 100, 2) as roi_pct
FROM bet_history bh
GROUP BY DATE(bh.placed_at)
ORDER BY date DESC;
