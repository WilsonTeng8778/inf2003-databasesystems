"""Owner-scoped SQL CRUD. Every saved-record lookup/mutation includes user_id."""

from psycopg.errors import UniqueViolation


class AlreadySaved(ValueError):
    pass


class VehicleNotFound(ValueError):
    pass


def saved_vehicle(row):
    if row is None:
        return None
    identifier, model_year_id, nickname, saved_at, make, model, year = row
    return {"savedVehicleId": identifier, "modelYearId": model_year_id,
            "nickname": nickname, "savedAt": saved_at.isoformat(),
            "vehicle": {"make": make, "model": model, "year": year}}


DETAIL_QUERY = """SELECT s.saved_vehicle_id,s.model_year_id,s.nickname,s.saved_at,v.make,v.model,v.year
    FROM saved_vehicle s JOIN vehicle_catalogue v USING(model_year_id)"""


class PostgresSavedVehicleStore:
    def __init__(self, connection):
        self.connection = connection

    def get(self, user_id, saved_id):
        row = self.connection.execute(DETAIL_QUERY + " WHERE s.user_id=%s AND s.saved_vehicle_id=%s",
                                      (user_id, saved_id)).fetchone()
        return saved_vehicle(row)

    def list(self, user_id, page, page_size):
        total = self.connection.execute("SELECT count(*) FROM saved_vehicle WHERE user_id=%s", (user_id,)).fetchone()[0]
        rows = self.connection.execute(DETAIL_QUERY + """ WHERE s.user_id=%s
            ORDER BY s.saved_at DESC,s.saved_vehicle_id DESC LIMIT %s OFFSET %s""",
            (user_id, page_size, (page - 1) * page_size)).fetchall()
        return {"items": [saved_vehicle(row) for row in rows],
                "pagination": {"page": page, "pageSize": page_size, "total": total,
                               "totalPages": (total + page_size - 1) // page_size}}

    def create(self, user_id, model_year_id, nickname):
        try:
            row = self.connection.execute("""INSERT INTO saved_vehicle(user_id,model_year_id,nickname)
                SELECT %s,model_year_id,%s FROM vehicle_catalogue WHERE model_year_id=%s
                RETURNING saved_vehicle_id""", (user_id, nickname, model_year_id)).fetchone()
        except UniqueViolation:
            self.connection.rollback()
            raise AlreadySaved("This vehicle is already in your saved vehicles") from None
        if row is None:
            raise VehicleNotFound("Vehicle not found in the imported catalogue")
        return self.get(user_id, row[0])

    def rename(self, user_id, saved_id, nickname):
        row = self.connection.execute("""UPDATE saved_vehicle SET nickname=%s
            WHERE user_id=%s AND saved_vehicle_id=%s RETURNING saved_vehicle_id""",
            (nickname, user_id, saved_id)).fetchone()
        return self.get(user_id, row[0]) if row else None

    def delete(self, user_id, saved_id):
        return self.connection.execute("""DELETE FROM saved_vehicle
            WHERE user_id=%s AND saved_vehicle_id=%s RETURNING saved_vehicle_id""",
            (user_id, saved_id)).fetchone() is not None

    def commit(self):
        self.connection.commit()
