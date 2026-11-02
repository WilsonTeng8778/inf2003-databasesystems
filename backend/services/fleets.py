"""Owner-scoped SQL fleet CRUD and model-year recall work orders."""

from datetime import datetime

from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row


STATUSES = ('OPEN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')
INTERPRETATION = ('Recall matches are by model year/make/model, not VIN. Work-order status is user-maintained; '
                  'it does not verify recall applicability or prove repair completion.')
FLEET_SELECT = '''SELECT f.*,
    (SELECT count(*) FROM fleet_vehicle fv WHERE fv.fleet_id=f.fleet_id) AS vehicle_count,
    (SELECT count(*) FROM work_order w JOIN fleet_vehicle fv USING(fleet_vehicle_id)
     WHERE fv.fleet_id=f.fleet_id) AS work_order_count FROM fleet f'''
VEHICLE_SELECT = '''SELECT fv.*,v.make,v.model,v.year FROM fleet_vehicle fv
    JOIN fleet f USING(fleet_id) JOIN vehicle_catalogue v USING(model_year_id)'''
ORDER_SELECT = '''SELECT w.*,fv.fleet_id,fv.label,v.make,v.model,v.year,m.campaign_number FROM work_order w
    JOIN fleet_vehicle fv USING(fleet_vehicle_id) JOIN fleet f USING(fleet_id)
    JOIN vehicle_catalogue v ON v.model_year_id=fv.model_year_id
    JOIN fleet_recall_matches m ON m.work_order_id=w.work_order_id'''


class FleetError(ValueError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def dto(row, fields):
    return {key: value.isoformat() if isinstance(value, datetime) else value
            for key, column in fields.items() for value in [row[column]]}


def vehicle_labels(row):
    return {key: row[key] for key in ('make', 'model', 'year')}


def fleet_record(row):
    return dto(row, {'fleetId': 'fleet_id', 'name': 'name', 'createdAt': 'created_at',
                     'vehicleCount': 'vehicle_count', 'workOrderCount': 'work_order_count'})


def vehicle_record(row):
    return {**dto(row, {'fleetVehicleId': 'fleet_vehicle_id', 'fleetId': 'fleet_id',
                        'modelYearId': 'model_year_id', 'label': 'label', 'createdAt': 'created_at'}),
            'vehicle': vehicle_labels(row)}


def order_record(row):
    return {**dto(row, {'workOrderId': 'work_order_id', 'fleetVehicleId': 'fleet_vehicle_id',
                        'fleetId': 'fleet_id', 'label': 'label', 'modelYearId': 'model_year_id',
                        'recallId': 'recall_id', 'campaignNumber': 'campaign_number', 'status': 'status',
                        'notes': 'notes', 'createdAt': 'created_at', 'completedAt': 'completed_at'}),
            'vehicle': vehicle_labels(row)}


def match_record(row):
    return {**dto(row, {'fleetId': 'fleet_id', 'fleetVehicleId': 'fleet_vehicle_id', 'label': 'label',
                        'modelYearId': 'model_year_id', 'recallId': 'recall_id', 'campaignNumber': 'campaign_number',
                        'workOrderId': 'work_order_id', 'workOrderStatus': 'work_order_status'}),
            'vehicle': vehicle_labels(row)}


def required(row, message):
    if row is None:
        raise FleetError(404, message)
    return row


class PostgresFleetStore:
    def __init__(self, connection):
        self.connection = connection
        # This is a separate request connection from the saved-vehicle store.
        connection.autocommit = True
        connection.row_factory = dict_row

    def page(self, select, count, values, mapper, order, page, size):
        total = self.connection.execute(count, values).fetchone()['n']
        rows = self.connection.execute(select + ' ORDER BY ' + order + ' LIMIT %s OFFSET %s',
                                       [*values, size, (page-1)*size]).fetchall()
        return {'items': [mapper(row) for row in rows], 'pagination': {
            'page': page, 'pageSize': size, 'total': total, 'totalPages': (total+size-1)//size}}

    def fleet(self, owner, fleet_id, *, lock=False):
        if lock:
            required(self.connection.execute('SELECT fleet_id FROM fleet WHERE owner_id=%s AND fleet_id=%s FOR UPDATE',
                                             (owner, fleet_id)).fetchone(), 'Fleet not found')
        return required(self.connection.execute(FLEET_SELECT + ' WHERE f.owner_id=%s AND f.fleet_id=%s',
                                                (owner, fleet_id)).fetchone(), 'Fleet not found')

    def get_fleet(self, owner, fleet_id):
        return fleet_record(self.fleet(owner, fleet_id))

    def list_fleets(self, owner, page, size):
        return self.page(FLEET_SELECT + ' WHERE f.owner_id=%s', 'SELECT count(*) AS n FROM fleet WHERE owner_id=%s',
                         [owner], fleet_record, 'f.created_at DESC,f.fleet_id DESC', page, size)

    def create_fleet(self, owner, name):
        try:
            with self.connection.transaction():
                row = self.connection.execute('INSERT INTO fleet(owner_id,name) VALUES (%s,%s) RETURNING fleet_id', (owner, name)).fetchone()
                return self.get_fleet(owner, row['fleet_id'])
        except UniqueViolation:
            raise FleetError(409, 'You already have a fleet with this name') from None

    def rename_fleet(self, owner, fleet_id, name):
        try:
            with self.connection.transaction():
                self.fleet(owner, fleet_id, lock=True)
                self.connection.execute('UPDATE fleet SET name=%s WHERE owner_id=%s AND fleet_id=%s', (name, owner, fleet_id))
                return self.get_fleet(owner, fleet_id)
        except UniqueViolation:
            raise FleetError(409, 'You already have a fleet with this name') from None

    def delete_fleet(self, owner, fleet_id):
        with self.connection.transaction():
            self.fleet(owner, fleet_id, lock=True)
            self.connection.execute('DELETE FROM fleet WHERE owner_id=%s AND fleet_id=%s', (owner, fleet_id))

    def vehicle(self, owner, vehicle_id, *, lock=False):
        if lock:
            # All API writers lock the owning fleet first, including deletions.
            required(self.connection.execute('''SELECT f.fleet_id FROM fleet f JOIN fleet_vehicle fv USING(fleet_id)
                WHERE f.owner_id=%s AND fv.fleet_vehicle_id=%s FOR UPDATE OF f''', (owner, vehicle_id)).fetchone(), 'Fleet vehicle not found')
        return required(self.connection.execute(VEHICLE_SELECT + ' WHERE f.owner_id=%s AND fv.fleet_vehicle_id=%s',
                                                (owner, vehicle_id)).fetchone(), 'Fleet vehicle not found')

    def get_vehicle(self, owner, vehicle_id):
        return vehicle_record(self.vehicle(owner, vehicle_id))

    def list_vehicles(self, owner, fleet_id, page, size):
        self.fleet(owner, fleet_id)
        where = ' WHERE f.owner_id=%s AND fv.fleet_id=%s'
        return self.page(VEHICLE_SELECT + where, 'SELECT count(*) AS n FROM fleet_vehicle fv JOIN fleet f USING(fleet_id)' + where,
                         [owner, fleet_id], vehicle_record, 'fv.created_at DESC,fv.fleet_vehicle_id DESC', page, size)

    def create_vehicle(self, owner, fleet_id, model_year_id, label):
        try:
            with self.connection.transaction():
                self.fleet(owner, fleet_id, lock=True)
                row = self.connection.execute('''INSERT INTO fleet_vehicle(fleet_id,model_year_id,label)
                    SELECT f.fleet_id,v.model_year_id,%s FROM fleet f CROSS JOIN vehicle_catalogue v
                    WHERE f.owner_id=%s AND f.fleet_id=%s AND v.model_year_id=%s RETURNING fleet_vehicle_id''',
                    (label, owner, fleet_id, model_year_id)).fetchone()
                required(row, 'Vehicle not found in the imported catalogue')
                return self.get_vehicle(owner, row['fleet_vehicle_id'])
        except UniqueViolation:
            raise FleetError(409, 'This fleet already has a vehicle with this label') from None

    def rename_vehicle(self, owner, vehicle_id, label):
        try:
            with self.connection.transaction():
                self.vehicle(owner, vehicle_id, lock=True)
                self.connection.execute('''UPDATE fleet_vehicle SET label=%s WHERE fleet_vehicle_id=%s
                    AND fleet_id IN (SELECT fleet_id FROM fleet WHERE owner_id=%s)''', (label, vehicle_id, owner))
                return self.get_vehicle(owner, vehicle_id)
        except UniqueViolation:
            raise FleetError(409, 'This fleet already has a vehicle with this label') from None

    def delete_vehicle(self, owner, vehicle_id):
        with self.connection.transaction():
            self.vehicle(owner, vehicle_id, lock=True)
            self.connection.execute('''DELETE FROM fleet_vehicle WHERE fleet_vehicle_id=%s
                AND fleet_id IN (SELECT fleet_id FROM fleet WHERE owner_id=%s)''', (vehicle_id, owner))

    def matches(self, owner, fleet_id, vehicle_id, tracked, page, size):
        self.fleet(owner, fleet_id)
        if vehicle_id is not None and self.vehicle(owner, vehicle_id)['fleet_id'] != fleet_id:
            raise FleetError(404, 'Fleet vehicle not found')
        conditions, values = ['owner_id=%s', 'fleet_id=%s'], [owner, fleet_id]
        if vehicle_id is not None:
            conditions.append('fleet_vehicle_id=%s')
            values.append(vehicle_id)
        if tracked is not None:
            conditions.append('work_order_id IS NOT NULL' if tracked else 'work_order_id IS NULL')
        where = ' WHERE ' + ' AND '.join(conditions)
        result = self.page('SELECT * FROM fleet_recall_matches' + where, 'SELECT count(*) AS n FROM fleet_recall_matches' + where,
                           values, match_record, 'fleet_vehicle_id,campaign_number,recall_id', page, size)
        result['interpretation'] = INTERPRETATION
        return result

    def order(self, owner, order_id, *, lock=False):
        if lock:
            required(self.connection.execute('''SELECT f.fleet_id FROM work_order w JOIN fleet_vehicle fv USING(fleet_vehicle_id)
                JOIN fleet f USING(fleet_id) WHERE f.owner_id=%s AND w.work_order_id=%s FOR UPDATE OF f''',
                (owner, order_id)).fetchone(), 'Work order not found')
        return required(self.connection.execute(ORDER_SELECT + ' WHERE f.owner_id=%s AND w.work_order_id=%s',
                                                (owner, order_id)).fetchone(), 'Work order not found')

    def get_order(self, owner, order_id):
        return order_record(self.order(owner, order_id))

    def list_orders(self, owner, fleet_id, vehicle_id, status, page, size):
        conditions, values = ['f.owner_id=%s'], [owner]
        for column, value in [('f.fleet_id', fleet_id), ('w.fleet_vehicle_id', vehicle_id), ('w.status', status)]:
            if value is not None:
                conditions.append(column + '=%s')
                values.append(value)
        where = ' WHERE ' + ' AND '.join(conditions)
        return self.page(ORDER_SELECT + where, '''SELECT count(*) AS n FROM work_order w
            JOIN fleet_vehicle fv USING(fleet_vehicle_id) JOIN fleet f USING(fleet_id)''' + where,
            values, order_record, 'w.created_at DESC,w.work_order_id DESC', page, size)

    def create_order(self, owner, vehicle_id, recall_id, notes):
        try:
            with self.connection.transaction():
                self.vehicle(owner, vehicle_id, lock=True)
                row = self.connection.execute('''INSERT INTO work_order(fleet_vehicle_id,model_year_id,recall_id,notes)
                    SELECT fleet_vehicle_id,model_year_id,recall_id,%s FROM fleet_recall_matches
                    WHERE owner_id=%s AND fleet_vehicle_id=%s AND recall_id=%s RETURNING work_order_id''',
                    (notes, owner, vehicle_id, recall_id)).fetchone()
                required(row, 'Matching recall not found for this fleet vehicle')
                return self.get_order(owner, row['work_order_id'])
        except UniqueViolation:
            raise FleetError(409, 'This vehicle already has a work order for this recall; update that order instead') from None

    def update_order(self, owner, order_id, fields):
        with self.connection.transaction():
            row = self.order(owner, order_id, lock=True)
            status = fields.get('status', row['status'])
            self.connection.execute('''UPDATE work_order SET status=%s,notes=%s,
                completed_at=CASE WHEN %s='COMPLETED' THEN COALESCE(completed_at,now()) ELSE NULL END
                WHERE work_order_id=%s AND fleet_vehicle_id IN (SELECT fv.fleet_vehicle_id FROM fleet_vehicle fv
                    JOIN fleet f USING(fleet_id) WHERE f.owner_id=%s)''',
                (status, fields.get('notes', row['notes']), status, order_id, owner))
            return self.get_order(owner, order_id)

    def delete_order(self, owner, order_id):
        with self.connection.transaction():
            self.order(owner, order_id, lock=True)
            self.connection.execute('''DELETE FROM work_order WHERE work_order_id=%s AND fleet_vehicle_id IN
                (SELECT fv.fleet_vehicle_id FROM fleet_vehicle fv JOIN fleet f USING(fleet_id) WHERE f.owner_id=%s)''',
                (order_id, owner))
