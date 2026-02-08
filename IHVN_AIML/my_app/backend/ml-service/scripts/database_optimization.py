#!/usr/bin/env python3
"""
Database performance optimization script for IIT ML Service
Adds indexes, optimizes queries, and implements performance monitoring
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import os
import psycopg2
from psycopg2.extras import execute_values
import sqlalchemy as sa
from sqlalchemy import text, Index, func, desc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from ..app.config import get_settings
from ..app.core.db import get_db_session
from ..app.models import Base, Patient, Observation, IITPrediction, Visit, Encounter

logger = logging.getLogger(__name__)
settings = get_settings()


class DatabaseOptimizer:
    """
    Comprehensive database optimization and performance monitoring
    """

    def __init__(self):
        self.engine = None
        self.session_factory = None

    async def initialize(self):
        """Initialize database connection"""
        if settings.database_url.startswith("postgresql"):
            # Async PostgreSQL connection
            self.engine = create_async_engine(
                settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=3600
            )
            self.session_factory = sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
        else:
            # Fallback to sync connection for SQLite
            from ..app.core.db import engine
            self.engine = engine

    async def create_performance_indexes(self):
        """
        Create comprehensive indexes for optimal query performance
        """
        logger.info("Creating performance indexes...")

        async with self.session_factory() as session:
            try:
                # Patient table indexes
                await session.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_patients_composite_search
                    ON patients (state_province, city_village, gender, birthdate);
                """))

                await session.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_patients_phone_search
                    ON patients (phone_number) WHERE phone_number IS NOT NULL;
                """))

                await session.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_patients_age_computed
                    ON patients (EXTRACT(YEAR FROM AGE(birthdate)));
                """))

                # Observation table indexes
                await session.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_observations_composite_query
                    ON observations (patient_uuid, obs_datetime DESC, variable_name);
                """))

                await session.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_observations_value_range
                    ON observations (variable_name, value_numeric)
                    WHERE value_numeric IS NOT NULL;
                """))

                await session.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_observations_recent
                    ON observations (obs_datetime DESC)
                    WHERE obs_datetime >= CURRENT_DATE - INTERVAL '90 days';
                """))

                # IIT Features table indexes
                await session.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_iit_features_prediction_ready
                    ON iit_features (last_feature_update DESC, age, gender)
                    WHERE last_feature_update IS NOT NULL;
                """))

                # IIT Predictions table indexes
                await session.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_performance
                    ON iit_predictions (prediction_timestamp DESC, risk_level, prediction_score);
                """))

                await session.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_model_version
                    ON iit_predictions (model_version, prediction_timestamp DESC);
                """))

                # Visit and Encounter optimization
                await session.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_visits_encounters_joined
                    ON visits (patient_uuid, date_started DESC);
                """))

                await session.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_encounters_temporal
                    ON encounters (patient_uuid, encounter_datetime DESC, encounter_type);
                """))

                # Intervention system indexes
                await session.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_interventions_active
                    ON interventions (status, priority DESC, due_date)
                    WHERE status IN ('pending', 'in_progress');
                """))

                await session.execute(text("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_alerts_active_critical
                    ON alerts (severity DESC, status, created_at DESC)
                    WHERE status = 'active' AND severity IN ('high', 'critical');
                """))

                await session.commit()
                logger.info("Performance indexes created successfully")

            except Exception as e:
                logger.error(f"Failed to create performance indexes: {str(e)}")
                await session.rollback()
                raise

    async def create_partitioned_tables(self):
        """
        Create partitioned tables for large datasets (PostgreSQL only)
        """
        if not settings.database_url.startswith("postgresql"):
            logger.info("Partitioning not supported for non-PostgreSQL databases")
            return

        logger.info("Creating partitioned tables for large datasets...")

        async with self.session_factory() as session:
            try:
                # Partition observations by month
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS observations_y2024m10 PARTITION OF observations
                    FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');
                """))

                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS observations_y2024m11 PARTITION OF observations
                    FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
                """))

                # Partition predictions by quarter
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS iit_predictions_q4_2024 PARTITION OF iit_predictions
                    FOR VALUES FROM ('2024-10-01') TO ('2025-01-01');
                """))

                await session.commit()
                logger.info("Partitioned tables created successfully")

            except Exception as e:
                logger.error(f"Failed to create partitioned tables: {str(e)}")
                await session.rollback()

    async def optimize_query_performance(self):
        """
        Implement query optimization strategies
        """
        logger.info("Optimizing query performance...")

        async with self.session_factory() as session:
            try:
                # Update table statistics for better query planning
                await session.execute(text("ANALYZE;"))

                # Create materialized views for common analytics queries
                await session.execute(text("""
                    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_patient_risk_summary AS
                    SELECT
                        p.patient_uuid,
                        p.pepfar_id,
                        p.state_province,
                        p.city_village,
                        EXTRACT(YEAR FROM AGE(p.birthdate)) as age,
                        p.gender,
                        COALESCE(ip.risk_level, 'unknown') as current_risk_level,
                        COALESCE(ip.prediction_score, 0) as latest_score,
                        ip.prediction_timestamp as last_prediction_date,
                        COUNT(DISTINCT v.id) as total_visits,
                        MAX(v.date_started) as last_visit_date,
                        COUNT(DISTINCT CASE WHEN o.variable_name = 'ARV Dispensed' THEN o.id END) as total_dispenses,
                        MAX(CASE WHEN o.variable_name = 'Days Supply' THEN o.value_numeric END) as last_days_supply
                    FROM patients p
                    LEFT JOIN iit_predictions ip ON p.patient_uuid = ip.patient_uuid
                        AND ip.prediction_timestamp = (
                            SELECT MAX(prediction_timestamp)
                            FROM iit_predictions
                            WHERE patient_uuid = p.patient_uuid
                        )
                    LEFT JOIN visits v ON p.patient_uuid = v.patient_uuid
                    LEFT JOIN encounters e ON p.patient_uuid = e.patient_uuid
                    LEFT JOIN observations o ON e.id = o.encounter_id
                    GROUP BY p.patient_uuid, p.pepfar_id, p.state_province, p.city_village,
                             p.birthdate, p.gender, ip.risk_level, ip.prediction_score, ip.prediction_timestamp;
                """))

                # Create index on materialized view
                await session.execute(text("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_patient_risk_summary_uuid
                    ON mv_patient_risk_summary (patient_uuid);
                """))

                await session.commit()
                logger.info("Query performance optimizations completed")

            except Exception as e:
                logger.error(f"Failed to optimize query performance: {str(e)}")
                await session.rollback()

    async def create_database_maintenance_procedures(self):
        """
        Create stored procedures for database maintenance
        """
        if not settings.database_url.startswith("postgresql"):
            logger.info("Stored procedures not supported for non-PostgreSQL databases")
            return

        logger.info("Creating database maintenance procedures...")

        async with self.session_factory() as session:
            try:
                # Procedure for cleaning old audit logs
                await session.execute(text("""
                    CREATE OR REPLACE PROCEDURE clean_old_audit_logs(days_old INTEGER DEFAULT 365)
                    LANGUAGE plpgsql
                    AS $$
                    BEGIN
                        DELETE FROM audit_logs
                        WHERE created_at < CURRENT_DATE - INTERVAL '1 day' * days_old;

                        RAISE NOTICE 'Cleaned % old audit log entries', FOUND;
                    END;
                    $$;
                """))

                # Procedure for updating patient risk summaries
                await session.execute(text("""
                    CREATE OR REPLACE PROCEDURE refresh_patient_risk_summaries()
                    LANGUAGE plpgsql
                    AS $$
                    BEGIN
                        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_patient_risk_summary;

                        RAISE NOTICE 'Refreshed patient risk summary materialized view';
                    END;
                    $$;
                """))

                # Procedure for archiving old observations
                await session.execute(text("""
                    CREATE OR REPLACE PROCEDURE archive_old_observations(months_old INTEGER DEFAULT 24)
                    LANGUAGE plpgsql
                    AS $$
                    BEGIN
                        INSERT INTO observations_archive
                        SELECT * FROM observations
                        WHERE obs_datetime < CURRENT_DATE - INTERVAL '1 month' * months_old;

                        DELETE FROM observations
                        WHERE obs_datetime < CURRENT_DATE - INTERVAL '1 month' * months_old;

                        RAISE NOTICE 'Archived % old observation records', FOUND;
                    END;
                    $$;
                """))

                await session.commit()
                logger.info("Database maintenance procedures created")

            except Exception as e:
                logger.error(f"Failed to create maintenance procedures: {str(e)}")
                await session.rollback()

    async def setup_performance_monitoring(self):
        """
        Set up performance monitoring and alerting
        """
        logger.info("Setting up performance monitoring...")

        async with self.session_factory() as session:
            try:
                # Create performance monitoring table
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id SERIAL PRIMARY KEY,
                        metric_name VARCHAR(100) NOT NULL,
                        metric_value NUMERIC,
                        metric_unit VARCHAR(20),
                        collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        metadata JSONB
                    );
                """))

                # Create indexes for performance metrics
                await session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_performance_metrics_name_time
                    ON performance_metrics (metric_name, collected_at DESC);
                """))

                # Create slow query log table
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS slow_queries (
                        id SERIAL PRIMARY KEY,
                        query_text TEXT NOT NULL,
                        execution_time INTERVAL NOT NULL,
                        rows_affected INTEGER,
                        executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        user_id INTEGER,
                        client_ip INET
                    );
                """))

                await session.commit()
                logger.info("Performance monitoring setup completed")

            except Exception as e:
                logger.error(f"Failed to setup performance monitoring: {str(e)}")
                await session.rollback()

    async def run_performance_audit(self) -> Dict[str, Any]:
        """
        Run comprehensive performance audit
        """
        logger.info("Running performance audit...")

        audit_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "database_size": {},
            "index_usage": {},
            "table_statistics": {},
            "slow_queries": [],
            "recommendations": []
        }

        async with self.session_factory() as session:
            try:
                # Get database size information
                if settings.database_url.startswith("postgresql"):
                    result = await session.execute(text("""
                        SELECT schemaname, tablename,
                               pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                        FROM pg_tables
                        WHERE schemaname = 'public'
                        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                        LIMIT 10;
                    """))
                    audit_results["database_size"] = [
                        {"table": row[1], "size": row[2]} for row in result.fetchall()
                    ]

                # Get index usage statistics
                result = await session.execute(text("""
                    SELECT schemaname, tablename, indexname,
                           idx_scan, idx_tup_read, idx_tup_fetch
                    FROM pg_stat_user_indexes
                    WHERE schemaname = 'public'
                    ORDER BY idx_scan DESC
                    LIMIT 20;
                """))
                audit_results["index_usage"] = [
                    {
                        "table": row[1],
                        "index": row[2],
                        "scans": row[3],
                        "tuples_read": row[4],
                        "tuples_fetched": row[5]
                    } for row in result.fetchall()
                ]

                # Get table statistics
                result = await session.execute(text("""
                    SELECT schemaname, tablename,
                           n_tup_ins, n_tup_upd, n_tup_del, n_live_tup, n_dead_tup
                    FROM pg_stat_user_tables
                    WHERE schemaname = 'public'
                    ORDER BY n_live_tup DESC
                    LIMIT 10;
                """))
                audit_results["table_statistics"] = [
                    {
                        "table": row[1],
                        "inserts": row[2],
                        "updates": row[3],
                        "deletes": row[4],
                        "live_tuples": row[5],
                        "dead_tuples": row[6]
                    } for row in result.fetchall()
                ]

                # Generate recommendations
                audit_results["recommendations"] = self._generate_recommendations(audit_results)

                logger.info("Performance audit completed")
                return audit_results

            except Exception as e:
                logger.error(f"Failed to run performance audit: {str(e)}")
                return audit_results

    def _generate_recommendations(self, audit_results: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations based on audit results"""
        recommendations = []

        # Check for unused indexes
        for index_info in audit_results.get("index_usage", []):
            if index_info["scans"] == 0:
                recommendations.append(f"Consider dropping unused index: {index_info['index']} on {index_info['table']}")

        # Check for tables with high dead tuple ratio
        for table_info in audit_results.get("table_statistics", []):
            total_tuples = table_info["live_tuples"] + table_info["dead_tuples"]
            if total_tuples > 0:
                dead_ratio = table_info["dead_tuples"] / total_tuples
                if dead_ratio > 0.2:  # More than 20% dead tuples
                    recommendations.append(f"Consider VACUUM on table {table_info['table']} (dead tuple ratio: {dead_ratio:.2%})")

        # General recommendations
        recommendations.extend([
            "Consider implementing table partitioning for large tables (> 10M rows)",
            "Review and optimize slow queries using EXPLAIN ANALYZE",
            "Consider increasing shared_buffers if memory allows",
            "Implement connection pooling for high-traffic scenarios",
            "Regularly update table statistics with ANALYZE"
        ])

        return recommendations

    async def export_performance_report(self, audit_results: Dict[str, Any], output_file: str):
        """Export performance audit results to file"""
        try:
            with open(output_file, 'w') as f:
                json.dump(audit_results, f, indent=2, default=str)

            logger.info(f"Performance report exported to {output_file}")

        except Exception as e:
            logger.error(f"Failed to export performance report: {str(e)}")


async def main():
    """Main execution function"""
    optimizer = DatabaseOptimizer()
    await optimizer.initialize()

    try:
        # Run all optimizations
        await optimizer.create_performance_indexes()
        await optimizer.create_partitioned_tables()
        await optimizer.optimize_query_performance()
        await optimizer.create_database_maintenance_procedures()
        await optimizer.setup_performance_monitoring()

        # Run performance audit
        audit_results = await optimizer.run_performance_audit()

        # Export results
        output_file = f"performance_audit_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        await optimizer.export_performance_report(audit_results, output_file)

        logger.info("Database optimization completed successfully")

    except Exception as e:
        logger.error(f"Database optimization failed: {str(e)}")
        raise
    finally:
        if optimizer.engine:
            await optimizer.engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
