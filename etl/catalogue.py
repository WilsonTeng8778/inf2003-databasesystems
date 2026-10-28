"""Build shared vehicle identities from the union of all selected source files."""

from etl.common import eligible_rows, import_run, stage
from etl.source import SOURCES, normalized


def import_catalogue(connection):
    with import_run(connection, "vehicle_catalogue") as counts:
        records = set()
        for source in SOURCES:
            for _, row, key in eligible_rows(source, counts):
                manufacturer = row[14] if source == "recalls" else row[5] if source == "investigations" else row[2]
                records.add((*key, normalized(manufacturer), source))
        stage(connection, "stage_vehicle", "make text, model text, year integer, manufacturer text, source text",
              sorted(records))
        connection.execute("INSERT INTO vehicle_make(name) SELECT DISTINCT make FROM stage_vehicle ON CONFLICT DO NOTHING")
        connection.execute("""INSERT INTO manufacturer(name)
            SELECT DISTINCT manufacturer FROM stage_vehicle WHERE manufacturer<>'' ON CONFLICT DO NOTHING""")
        connection.execute("""INSERT INTO vehicle_model(make_id,name)
            SELECT DISTINCT k.make_id,s.model FROM stage_vehicle s JOIN vehicle_make k ON k.name=s.make
            ON CONFLICT DO NOTHING""")
        before = connection.execute("SELECT count(*) FROM model_year").fetchone()[0]
        connection.execute("""INSERT INTO model_year(model_id,year)
            SELECT DISTINCT m.model_id,s.year FROM stage_vehicle s
            JOIN vehicle_make k ON k.name=s.make JOIN vehicle_model m ON m.make_id=k.make_id AND m.name=s.model
            ON CONFLICT DO NOTHING""")
        after = connection.execute("SELECT count(*) FROM model_year").fetchone()[0]
        counts.inserted = after - before
        distinct = connection.execute("SELECT count(DISTINCT (make,model,year)) FROM stage_vehicle").fetchone()[0]
        counts.updated = distinct - counts.inserted
        connection.execute("""INSERT INTO manufacturer_make(manufacturer_id,make_id)
            SELECT DISTINCT f.manufacturer_id,k.make_id FROM stage_vehicle s
            JOIN manufacturer f ON f.name=s.manufacturer JOIN vehicle_make k ON k.name=s.make
            ON CONFLICT DO NOTHING""")
        connection.execute("""INSERT INTO vehicle_source(model_year_id,source_name)
            SELECT DISTINCT v.model_year_id,s.source FROM stage_vehicle s
            JOIN vehicle_catalogue v ON (v.make,v.model,v.year)=(s.make,s.model,s.year)
            ON CONFLICT DO NOTHING""")

