#!/usr/bin/env python
"""Create feature_flags table directly"""
from sqlalchemy import create_engine, text

# Use the same database URL as the app
engine = create_engine("sqlite:///./iit_ml_service.db")

# Create the feature_flags table
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS feature_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) UNIQUE NOT NULL,
            description TEXT,
            enabled BOOLEAN DEFAULT FALSE,
            user_percentage INTEGER DEFAULT 0,
            user_whitelist TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    conn.commit()
    print("Feature flags table created successfully!")
