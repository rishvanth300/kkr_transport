from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from fleet.models import Vehicle, Driver
from trips.forms import TripSheetForm
from trips.models import TripSheet, get_default_bata_percentage
from trips.services import calculate_trip_financials


User = get_user_model()


class TripSheetFeatureTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username="admin", password="pass12345", email="admin@example.com")
        self.client = Client()
        self.client.force_login(self.user)
        self.vehicle = Vehicle.objects.create(
            vehicle_number="TN01AB1234",
            vehicle_make="Tata",
            vehicle_model="Ace",
            manufacturing_year=2020,
            wheel_configuration=6,
            fc_expiry_date=timezone.localdate(),
            insurance_expiry_date=timezone.localdate(),
            pollution_certificate_expiry_date=timezone.localdate(),
        )
        self.driver = Driver.objects.create(
            driver_name="Driver One",
            mobile_number="9999999999",
            address="Addr",
            driving_licence_number="DL12345",
            licence_expiry_date=timezone.localdate(),
            assigned_vehicle=self.vehicle,
        )

    def _base_trip_payload(self, **overrides):
        data = {
            "trip_date": timezone.localdate().isoformat(),
            "company_name": "ACME",
            "driver": str(self.driver.id),
            "vehicle": str(self.vehicle.id),
            "from_location": "A",
            "to_location": "B",
            "load_type": "Goods",
            "starting_km": "100.00",
            "closing_km": "150.00",
            "total_revenue": "1000.00",
            "diesel_quantity": "10.000",
            "diesel_price_per_litre": "100.00",
            "bata_percentage": "15.00",
            "loading_cost": "0",
            "unloading_cost": "0",
            "toll_cost": "0",
            "load_commission": "0",
            "maintenance_cost": "0",
            "other_expenses": "0",
            "other_expense_note": "",
        }
        data.update({k: str(v) for k, v in overrides.items()})
        return data

    def test_default_bata_percentage_is_15(self):
        self.assertEqual(get_default_bata_percentage(), Decimal("15.00"))

    def test_trip_sheet_form_initial_bata_percentage_is_15_for_new_trip(self):
        form = TripSheetForm(selected_vehicle=self.vehicle)
        self.assertEqual(form.fields["bata_percentage"].initial, Decimal("15.00"))

    def test_new_trip_creation_uses_default_bata_15_when_omitted(self):
        payload = self._base_trip_payload()
        payload.pop("bata_percentage", None)
        resp = self.client.post(reverse("trips:create") + f"?vehicle={self.vehicle.id}", payload)
        self.assertEqual(resp.status_code, 302)
        trip = TripSheet.objects.latest("id")
        self.assertEqual(trip.bata_percentage, Decimal("15.00"))
        self.assertEqual(trip.driver_bata, Decimal("150.00"))  # 15% of 1000

    def test_manual_bata_percentage_can_be_updated(self):
        trip = TripSheet(
            trip_date=timezone.localdate(),
            company_name="ACME",
            driver=self.driver,
            vehicle=self.vehicle,
            from_location="A",
            to_location="B",
            starting_km=Decimal("0"),
            closing_km=Decimal("10"),
            total_revenue=Decimal("1000"),
            bata_percentage=Decimal("20.00"),
            created_by=self.user,
        )
        calculate_trip_financials(trip)
        trip.save()
        self.assertEqual(trip.driver_bata, Decimal("200.00"))

    def test_existing_trip_record_bata_unchanged_when_creating_new_trip(self):
        old = TripSheet.objects.create(
            trip_date=timezone.localdate(),
            company_name="OldCo",
            driver=self.driver,
            vehicle=self.vehicle,
            from_location="X",
            to_location="Y",
            starting_km=Decimal("0"),
            closing_km=Decimal("10"),
            total_revenue=Decimal("1000.00"),
            bata_percentage=Decimal("10.00"),
            driver_bata=Decimal("100.00"),
            created_by=self.user,
        )
        payload = self._base_trip_payload(company_name="NewCo")
        self.client.post(reverse("trips:create") + f"?vehicle={self.vehicle.id}", payload)
        old.refresh_from_db()
        self.assertEqual(old.bata_percentage, Decimal("10.00"))
        self.assertEqual(old.driver_bata, Decimal("100.00"))

    def test_create_trip_associates_correct_vehicle(self):
        payload = self._base_trip_payload()
        resp = self.client.post(reverse("trips:create") + f"?vehicle={self.vehicle.id}", payload)
        self.assertEqual(resp.status_code, 302)
        trip = TripSheet.objects.latest("id")
        self.assertEqual(trip.vehicle_id, self.vehicle.id)
        self.assertEqual(trip.created_by_id, self.user.id)

    def test_required_field_validation_empty_company(self):
        payload = self._base_trip_payload(company_name="")
        resp = self.client.post(reverse("trips:create") + f"?vehicle={self.vehicle.id}", payload)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Company name is required", status_code=200)

    def test_closing_km_validation(self):
        payload = self._base_trip_payload(starting_km="200", closing_km="100")
        resp = self.client.post(reverse("trips:create") + f"?vehicle={self.vehicle.id}", payload)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Closing KM cannot be less than Starting KM")

    def test_trip_calculations_correct(self):
        payload = self._base_trip_payload(
            starting_km="100", closing_km="160", total_revenue="2000",
            diesel_quantity="20", diesel_price_per_litre="100",
            bata_percentage="15", loading_cost="50", unloading_cost="50",
            toll_cost="25", load_commission="25", maintenance_cost="10", other_expenses="40"
        )
        resp = self.client.post(reverse("trips:create") + f"?vehicle={self.vehicle.id}", payload)
        self.assertEqual(resp.status_code, 302)
        trip = TripSheet.objects.latest("id")
        self.assertEqual(trip.distance_km, Decimal("60.00"))
        self.assertEqual(trip.diesel_cost, Decimal("2000.00"))
        self.assertEqual(trip.driver_bata, Decimal("300.00"))
        # total cost = diesel + loading + unloading + toll + bata + commission + maintenance + other
        self.assertEqual(trip.total_cost, Decimal("2500.00"))
        self.assertEqual(trip.profit, Decimal("-500.00"))

    def test_select_truck_page_has_direct_select_links(self):
        resp = self.client.get(reverse("trips:select_truck"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, reverse("trips:create") + f"?vehicle={self.vehicle.id}")
        self.assertNotContains(resp, ">Continue<")

    def test_create_trip_get_resolves_selected_vehicle_and_populates_form(self):
        resp = self.client.get(reverse("trips:create") + f"?vehicle={self.vehicle.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.vehicle.vehicle_number)
        # session should be synced
        session = self.client.session
        self.assertEqual(session.get("trip_selected_vehicle_id"), self.vehicle.id)

    def test_trip_sheet_form_renders_enter_nav_and_explicit_submit(self):
        resp = self.client.get(reverse("trips:create") + f"?vehicle={self.vehicle.id}")
        self.assertContains(resp, 'data-enter-nav="1"')
        self.assertContains(resp, 'type="submit"')
        self.assertContains(resp, 'Save Trip Sheet')

    def test_number_inputs_rendered_without_browser_spinner_dependency(self):
        # Inputs remain type=number for validation/keyboard entry; spinner removal is handled via CSS.
        form = TripSheetForm(selected_vehicle=self.vehicle)
        html = str(form["bata_percentage"])
        self.assertIn('type="number"', html)

    def test_hamburger_menu_markup_present(self):
        resp = self.client.get(reverse("trips:select_truck"))
        self.assertContains(resp, 'data-sidebar-toggle')
        self.assertContains(resp, 'id="sidebar"')
        self.assertContains(resp, 'sidebar-backdrop')


class FrontendBehaviorStaticTests(TestCase):
    def _read(self, relpath):
        from pathlib import Path
        from django.conf import settings
        p = Path(settings.BASE_DIR) / relpath
        return p.read_text(encoding="utf-8")

    def test_number_input_spinner_css_removed(self):
        css = self._read("static/css/app.css")
        self.assertIn('input[type="number"]::-webkit-outer-spin-button', css)
        self.assertIn('input[type="number"]::-webkit-inner-spin-button', css)
        self.assertIn('-moz-appearance: textfield', css)
        self.assertIn('appearance: textfield', css)

    def test_enter_navigation_js_present_and_prevents_submit(self):
        js = self._read("static/js/app.js")
        self.assertIn('form[data-enter-nav]', js)
        self.assertIn('e.key !== "Enter"', js)
        self.assertIn('e.preventDefault()', js)
        self.assertIn('This field is required before moving to the next field.', js)
        self.assertIn('fields[idx + 1].focus()', js)

    def test_hamburger_scroll_behavior_js_and_css_present(self):
        js = self._read("static/js/app.js")
        css = self._read("static/css/app.css")
        self.assertIn('classList.toggle("sidebar-open"', js)
        self.assertIn('sidebarToggles.forEach', js)
        self.assertIn('body.sidebar-open', css)
        self.assertIn('overflow: hidden', css)

    def test_responsive_layout_css_has_breakpoints(self):
        css = self._read("static/css/app.css")
        self.assertIn('@media (max-width: 767px)', css)
        self.assertIn('@media (max-width: 480px)', css)
        self.assertIn('grid-template-columns: 1fr', css)
        self.assertIn('.table-wrap', css)
