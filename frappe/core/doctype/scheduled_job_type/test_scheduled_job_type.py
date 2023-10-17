# Copyright (c) 2019, Frappe Technologies and Contributors
# License: MIT. See LICENSE
import frappe
from frappe.core.doctype.scheduled_job_type.scheduled_job_type import sync_jobs
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_datetime
from frappe.utils.data import add_to_date


class TestScheduledJobType(FrappeTestCase):
	def setUp(self):
		frappe.db.rollback()
		frappe.db.truncate("Scheduled Job Type")
		sync_jobs()
		frappe.db.commit()

	def test_sync_jobs(self):
		all_job = frappe.get_doc("Scheduled Job Type", dict(method="frappe.email.queue.flush"))
		self.assertEqual(all_job.frequency, "All")

		daily_job = frappe.get_doc(
			"Scheduled Job Type", dict(method="frappe.desk.notifications.clear_notifications")
		)
		self.assertEqual(daily_job.frequency, "Daily")

		# check if cron jobs are synced
		cron_job = frappe.get_doc("Scheduled Job Type", dict(method="frappe.oauth.delete_oauth2_data"))
		self.assertEqual(cron_job.frequency, "Cron")
		self.assertEqual(cron_job.cron_format, "0/15 * * * *")

		# check if jobs are synced after change in hooks
		updated_scheduler_events = {"hourly": ["frappe.email.queue.flush"]}
		sync_jobs(updated_scheduler_events)
		updated_scheduled_job = frappe.get_doc(
			"Scheduled Job Type", {"method": "frappe.email.queue.flush"}
		)
		self.assertEqual(updated_scheduled_job.frequency, "Hourly")

	def test_daily_job(self):
		job = frappe.get_doc(
			"Scheduled Job Type", dict(method="frappe.desk.notifications.clear_notifications")
		)
		job.db_set("last_execution", "2019-01-01 00:00:00")
		self.assertTrue(job.is_event_due(get_datetime("2019-01-02 00:00:06")))
		self.assertFalse(job.is_event_due(get_datetime("2019-01-01 00:00:06")))
		self.assertFalse(job.is_event_due(get_datetime("2019-01-01 23:59:59")))

	def test_weekly_job(self):
		job = frappe.get_doc(
			"Scheduled Job Type",
			dict(method="frappe.social.doctype.energy_point_log.energy_point_log.send_weekly_summary"),
		)
		job.db_set("last_execution", "2019-01-01 00:00:00")
		self.assertTrue(job.is_event_due(get_datetime("2019-01-06 00:00:01")))
		self.assertFalse(job.is_event_due(get_datetime("2019-01-02 00:00:06")))
		self.assertFalse(job.is_event_due(get_datetime("2019-01-05 23:59:59")))

	def test_monthly_job(self):
		job = frappe.get_doc(
			"Scheduled Job Type",
			dict(method="frappe.email.doctype.auto_email_report.auto_email_report.send_monthly"),
		)
		job.db_set("last_execution", "2019-01-01 00:00:00")
		self.assertTrue(job.is_event_due(get_datetime("2019-02-01 00:00:01")))
		self.assertFalse(job.is_event_due(get_datetime("2019-01-15 00:00:06")))
		self.assertFalse(job.is_event_due(get_datetime("2019-01-31 23:59:59")))

	def test_cron_job(self):
		# Daily but offset by 45 minutes
		job = frappe.get_doc("Scheduled Job Type", dict(method="frappe.core.doctype.log_settings.log_settings.run_log_clean_up"))
		self.assertEqual(
			job.next_execution,
			add_to_date(None, days=1).replace(hour=0, minute=45, second=0, microsecond=0)
		)
		# runs every 15 mins
		job = frappe.get_doc("Scheduled Job Type", dict(method="frappe.oauth.delete_oauth2_data"))
		job.db_set("last_execution", "2019-01-01 00:00:00")
		self.assertEqual(job.next_execution, get_datetime("2019-01-01 00:15:00"))
		self.assertTrue(job.is_event_due(get_datetime("2019-01-01 00:15:01")))
		self.assertFalse(job.is_event_due(get_datetime("2019-01-01 00:05:06")))
		self.assertFalse(job.is_event_due(get_datetime("2019-01-01 00:14:59")))
