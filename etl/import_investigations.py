"""Import investigations without discarding multiple manufacturers or campaigns."""

import re

from etl.common import eligible_rows, import_run, stage
from etl.source import date_value, normalized, source_sha256


def import_investigations(connection):
    with import_run(connection, "investigations", source_sha256("investigations")) as counts:
        def records():
            for line, row, key in eligible_rows("investigations", counts):
                identifier = normalized(row[0])
                if not identifier:
                    counts.rejected += 1
                    continue
                prefix = re.match(r"[A-Z]+", identifier)
                yield (identifier, prefix.group() if prefix else "UNKNOWN", *key, normalized(row[4]),
                       normalized(row[5]), date_value(row[6]), date_value(row[7]),
                       normalized(row[8]), row[9].strip(), row[10].strip(), line)
        stage(connection, "stage_investigation", """
            number text, type text, make text, model text, year integer, component text,
            manufacturer text, opened date, closed date, campaign text, subject text, summary text, line bigint
        """, records())
        counts.updated = connection.execute("""SELECT count(DISTINCT s.number)
            FROM stage_investigation s JOIN official_investigation i ON i.investigation_number=s.number""").fetchone()[0]
        total = connection.execute("SELECT count(DISTINCT number) FROM stage_investigation").fetchone()[0]
        counts.inserted = total - counts.updated
        connection.execute("""INSERT INTO official_investigation(investigation_number,investigation_type,
                subject,summary,opened_date,closed_date)
            SELECT DISTINCT ON (number) number,type,subject,summary,opened,closed
            FROM stage_investigation ORDER BY number,line
            ON CONFLICT(investigation_number) DO UPDATE SET investigation_type=excluded.investigation_type,
                subject=excluded.subject,summary=excluded.summary,
                opened_date=excluded.opened_date,closed_date=excluded.closed_date""")
        connection.execute("""INSERT INTO investigation_vehicle(investigation_id,model_year_id)
            SELECT DISTINCT i.investigation_id,v.model_year_id FROM stage_investigation s
            JOIN official_investigation i ON i.investigation_number=s.number
            JOIN vehicle_catalogue v ON (v.make,v.model,v.year)=(s.make,s.model,s.year)
            ON CONFLICT DO NOTHING""")
        connection.execute("""INSERT INTO investigation_manufacturer(investigation_id,manufacturer_id)
            SELECT DISTINCT i.investigation_id,f.manufacturer_id FROM stage_investigation s
            JOIN official_investigation i ON i.investigation_number=s.number
            JOIN manufacturer f ON f.name=s.manufacturer ON CONFLICT DO NOTHING""")
        connection.execute("""INSERT INTO investigation_component(investigation_id,component)
            SELECT DISTINCT i.investigation_id,s.component FROM stage_investigation s
            JOIN official_investigation i ON i.investigation_number=s.number
            WHERE s.component<>'' ON CONFLICT DO NOTHING""")
        connection.execute("""INSERT INTO investigation_recall(investigation_id,campaign_number)
            SELECT DISTINCT i.investigation_id,s.campaign FROM stage_investigation s
            JOIN official_investigation i ON i.investigation_number=s.number
            WHERE s.campaign<>'' ON CONFLICT DO NOTHING""")

