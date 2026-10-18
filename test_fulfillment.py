"""Checks for errors that would change a manager's queue or monetary exposure."""
import unittest
import pandas as pd
from fulfillment import overdue_orders, replay_cohort, headline


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame([
            {"order_id": "seller", "purchase_at": "2018-01-01", "approved_at": "2018-01-01", "handoff_at": "2018-01-12", "delivered_at": "2018-01-15", "promised_date": "2018-01-05", "final_status": "delivered", "destination_state": "SP", "merchandise_brl": 100},
            {"order_id": "carrier", "purchase_at": "2018-01-01", "approved_at": "2018-01-02", "handoff_at": "2018-01-03", "delivered_at": None, "promised_date": "2018-01-05", "final_status": "shipped", "destination_state": "RJ", "merchandise_brl": 200},
            {"order_id": "delivered", "purchase_at": "2018-01-01", "approved_at": "2018-01-02", "handoff_at": "2018-01-03", "delivered_at": "2018-01-04", "promised_date": "2018-01-05", "final_status": "delivered", "destination_state": "SP", "merchandise_brl": 300},
            {"order_id": "unapproved", "purchase_at": "2018-01-01", "approved_at": "2018-01-12", "handoff_at": None, "delivered_at": None, "promised_date": "2018-01-05", "final_status": "approved", "destination_state": "SP", "merchandise_brl": 400},
        ])
        for c in ["purchase_at", "approved_at", "handoff_at", "delivered_at", "promised_date"]:
            self.df[c] = pd.to_datetime(self.df[c])

    def test_future_delivery_does_not_remove_historical_order(self):
        q = overdue_orders(self.df, "2018-01-10")
        self.assertEqual(set(q.order_id), {"seller", "carrier"})
        self.assertEqual(headline(q), {"overdue_orders": 2, "merchandise_brl": 300., "awaiting_handoff": 1})

    def test_future_handoff_does_not_leak_into_stage(self):
        q = overdue_orders(self.df, "2018-01-10").set_index("order_id")
        self.assertEqual(q.loc["seller", "stage"], "Awaiting seller handoff")
        self.assertEqual(q.loc["carrier", "stage"], "With carrier")

    def test_due_today_is_not_late_at_start_of_day(self):
        self.assertTrue(overdue_orders(self.df, "2018-01-05").empty)

    def test_region_and_empty_scope(self):
        self.assertEqual(overdue_orders(self.df, "2018-01-10", "SP").order_id.tolist(), ["seller"])
        self.assertEqual(headline(overdue_orders(self.df, "2018-01-10", "AC"))["overdue_orders"], 0)

    def test_cancellation_and_invalid_approval_are_excluded(self):
        self.df.loc[0, "final_status"] = "canceled"
        self.df.loc[1, "approved_at"] = pd.NaT
        self.assertEqual(set(replay_cohort(self.df).order_id), {"delivered", "unapproved"})

    def test_event_at_cutoff_is_not_yet_observed(self):
        q = overdue_orders(self.df, "2018-01-12").set_index("order_id")
        self.assertEqual(q.loc["seller", "stage"], "Awaiting seller handoff")


if __name__ == "__main__":
    unittest.main()
