import unittest

from etl.import_complaints import merge_complaint
from etl.source import date_value, flag, integer, normalized, vehicle_key


def complaint(component="STEERING"):
    row = [""] * 51
    for index, value in {0:"100",1:"12345678",2:"Example Manufacturer",3:"Honda",4:"Civic",5:"2022",
                         6:"Y",7:"20250102",8:"N",9:"2",10:"0",11:component,
                         16:"20250103",17:"",19:"Example public complaint narrative",45:"V"}.items():
        row[index] = value
    return row


class TransformationTests(unittest.TestCase):
    def test_component_rows_merge_without_multiplying_incident_counts(self):
        first = complaint()
        second = complaint("ELECTRICAL SYSTEM")
        second[0] = "101"
        document = merge_complaint([("complaints_2025_2026", first), ("complaints_2025_2026", second)],
                                   {("HONDA", "CIVIC", 2022): 42})
        self.assertEqual(document["components"], ["ELECTRICAL SYSTEM", "STEERING"])
        self.assertEqual(document["incident"]["injuries"], 2)
        self.assertEqual(document["source"]["rowIds"], ["100", "101"])
        self.assertEqual(document["source"]["componentRowCount"], 2)
        self.assertIsNone(document["mileage"])
        self.assertEqual(document["receivedDate"].isoformat(), "2025-01-03T00:00:00+00:00")

    def test_same_odi_for_different_vehicle_is_rejected(self):
        first, second = complaint(), complaint()
        second[4] = "ACCORD"
        with self.assertRaisesRegex(ValueError, "Conflicting vehicle identities"):
            merge_complaint([("complaints_2025_2026", first), ("complaints_2025_2026", second)],
                            {("HONDA", "CIVIC", 2022): 42})

    def test_conflicting_scalar_values_are_not_silently_summed(self):
        first, second = complaint(), complaint("SERVICE BRAKES")
        second[9] = "3"
        document = merge_complaint([("complaints_2025_2026", first), ("complaints_2025_2026", second)],
                                   {("HONDA", "CIVIC", 2022): 42})
        self.assertEqual(document["incident"]["injuries"], 2)
        self.assertIn(10, document["source"]["conflictingScalarColumns"])

    def test_unknown_year_and_nonvehicle_products_are_excluded(self):
        row = complaint()
        row[5] = "9999"
        self.assertIsNone(vehicle_key(row, "complaints_2025_2026"))
        row[5], row[45] = "2022", "E"
        self.assertIsNone(vehicle_key(row, "complaints_2025_2026"))

    def test_nulls_invalid_dates_and_normalization(self):
        self.assertIsNone(integer(""))
        self.assertEqual(integer("0"), 0)
        self.assertIsNone(integer("-1"))
        self.assertIsNone(flag(""))
        self.assertFalse(flag("N"))
        self.assertIsNone(date_value("20250230"))
        self.assertIsNone(date_value("00000000"))
        self.assertEqual(normalized("  Land   Rover "), "LAND ROVER")


if __name__ == "__main__":
    unittest.main()
