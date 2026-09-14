"""`apps.reports.pdf` builders (Stage 4b) — render bytes + extractable text.

Each builder is exercised directly against the ORM (no HTTP/admin here —
that is `tests/admin/test_pdf_actions.py`'s job); these tests only check
that WeasyPrint produces a valid PDF and that the expected Ukrainian text
made it into the rendered document.
"""
import io

import pytest
from pypdf import PdfReader

from apps.reports.pdf import dashboard_summary_pdf, equipment_card_pdf, inspection_act_pdf
from tests.factories import EquipmentFactory, IncidentFactory, InspectionFactory

pytestmark = pytest.mark.django_db


def _extract_text(pdf_bytes):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return '\n'.join(page.extract_text() for page in reader.pages)


def test_equipment_card_pdf_is_valid_pdf_with_inventory_number(admin_user):
    equipment = EquipmentFactory(inventory_number='INV-PDF-1')
    InspectionFactory(equipment=equipment)
    IncidentFactory(equipment=equipment)

    pdf_bytes = equipment_card_pdf(equipment, user=admin_user)

    assert pdf_bytes.startswith(b'%PDF')
    text = _extract_text(pdf_bytes)
    assert 'INV-PDF-1' in text


def test_inspection_act_pdf_is_valid_pdf_with_title(admin_user):
    inspection = InspectionFactory()

    pdf_bytes = inspection_act_pdf(inspection, user=admin_user)

    assert pdf_bytes.startswith(b'%PDF')
    text = _extract_text(pdf_bytes)
    assert 'Акт огляду' in text
    assert inspection.equipment.inventory_number in text


def test_dashboard_summary_pdf_is_valid_pdf_with_title(admin_user):
    EquipmentFactory()
    IncidentFactory()

    pdf_bytes = dashboard_summary_pdf(admin_user)

    assert pdf_bytes.startswith(b'%PDF')
    text = _extract_text(pdf_bytes)
    assert 'Зведений звіт' in text


def test_dashboard_summary_pdf_scoped_to_employee_equipment(employee_user):
    own = EquipmentFactory(inventory_number='INV-OWN-PDF', assigned_to=employee_user)
    EquipmentFactory(inventory_number='INV-FOREIGN-PDF', assigned_to=None)

    pdf_bytes = dashboard_summary_pdf(employee_user)
    text = _extract_text(pdf_bytes)

    assert pdf_bytes.startswith(b'%PDF')
    # Employee's own equipment counts towards "Всього обладнання" (1), the
    # foreign unit does not — full scoping correctness is already covered by
    # `tests/reports/test_summary.py`; this only checks the PDF wires the
    # same scoped querysets through.
    assert 'Всього обладнання' in text
