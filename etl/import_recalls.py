"""Import vehicle recall campaigns, affected vehicles and component source rows."""

from etl.common import eligible_rows, import_run, stage
from etl.source import SOURCES, date_value, flag, integer, normalized, source_sha256


def import_recalls(connection):
    with import_run(connection, "recalls", source_sha256("recalls")) as counts:
        def records():
            for line, row, key in eligible_rows("recalls", counts):
                if not row[0].strip() or not row[1].strip():
                    counts.rejected += 1
                    continue
                yield (row[0].strip(), normalized(row[1]), *key, normalized(row[7]),
                       normalized(row[6]), date_value(row[15]), row[19].strip(), row[20].strip(), row[21].strip(),
                       integer(row[11]), date_value(row[8]), date_value(row[9]),
                       flag(row[27]), flag(row[28]), SOURCES["recalls"][0], line)
        stage(connection, "stage_recall", """
            source_id text, campaign text, make text, model text, year integer,
            manufacturer text, component text, report_date date, summary text,
            consequence text, remedy text, affected bigint, manufacturing_started date,
            manufacturing_ended date, do_not_drive boolean, park_outside boolean,
            archive text, line bigint
        """, records())
        connection.execute("""INSERT INTO manufacturer(name)
            SELECT DISTINCT manufacturer FROM stage_recall WHERE manufacturer<>'' ON CONFLICT DO NOTHING""")
        counts.updated = connection.execute("""SELECT count(DISTINCT s.campaign)
            FROM stage_recall s JOIN recall r ON r.campaign_number=s.campaign""").fetchone()[0]
        total = connection.execute("SELECT count(DISTINCT campaign) FROM stage_recall").fetchone()[0]
        counts.inserted = total - counts.updated
        connection.execute("""INSERT INTO recall(campaign_number,reporting_manufacturer_id,
                report_date,summary,consequence,remedy,potentially_affected,do_not_drive,park_outside)
            SELECT DISTINCT ON (s.campaign) s.campaign,f.manufacturer_id,s.report_date,s.summary,
                s.consequence,s.remedy,s.affected,s.do_not_drive,s.park_outside
            FROM stage_recall s LEFT JOIN manufacturer f ON f.name=s.manufacturer
            ORDER BY s.campaign,s.source_id
            ON CONFLICT(campaign_number) DO UPDATE SET
                reporting_manufacturer_id=excluded.reporting_manufacturer_id,report_date=excluded.report_date,
                summary=excluded.summary,consequence=excluded.consequence,remedy=excluded.remedy,
                potentially_affected=excluded.potentially_affected,
                do_not_drive=excluded.do_not_drive,park_outside=excluded.park_outside""")
        connection.execute("""INSERT INTO recall_vehicle(recall_id,model_year_id)
            SELECT DISTINCT r.recall_id,v.model_year_id FROM stage_recall s
            JOIN recall r ON r.campaign_number=s.campaign
            JOIN vehicle_catalogue v ON (v.make,v.model,v.year)=(s.make,s.model,s.year)
            ON CONFLICT DO NOTHING""")
        connection.execute("""INSERT INTO recall_record(source_record_id,recall_id,model_year_id,
                component,manufacturing_started,manufacturing_ended,source_archive,source_line)
            SELECT DISTINCT ON (s.source_id) s.source_id,r.recall_id,v.model_year_id,s.component,
                s.manufacturing_started,s.manufacturing_ended,s.archive,s.line
            FROM stage_recall s JOIN recall r ON r.campaign_number=s.campaign
            JOIN vehicle_catalogue v ON (v.make,v.model,v.year)=(s.make,s.model,s.year)
            ORDER BY s.source_id,s.line DESC
            ON CONFLICT(source_record_id) DO UPDATE SET recall_id=excluded.recall_id,
                model_year_id=excluded.model_year_id,component=excluded.component,
                manufacturing_started=excluded.manufacturing_started,manufacturing_ended=excluded.manufacturing_ended,
                source_archive=excluded.source_archive,source_line=excluded.source_line""")

