"""Tests for the rule-based chart suggestion."""

from app.chart import suggest_chart


def test_month_plus_number_is_a_line_chart():
    chart = suggest_chart(["OrderMonth", "Orders"], [["2026-01", 34], ["2026-02", 64], ["2026-03", 102]])
    assert chart == {"type": "line", "x": "OrderMonth", "y": ["Orders"]}


def test_hour_of_day_is_a_line_chart():
    chart = suggest_chart(["HourOfDay", "Orders"], [[h, h * 10] for h in range(24)])
    assert chart["type"] == "line" and chart["x"] == "HourOfDay"


def test_categories_plus_numbers_is_a_bar_chart():
    rows = [[city, 1000 + i, 900 + i] for i, city in enumerate("ABCDEFGH")]
    chart = suggest_chart(["CityName", "Orders", "DeliveredOrders"], rows)
    assert chart == {"type": "bar", "x": "CityName", "y": ["Orders", "DeliveredOrders"]}


def test_few_categories_with_one_total_is_a_pie_chart():
    chart = suggest_chart(["Status", "Orders"], [["Delivered", 73632], ["Cancelled", 5395], ["Failed", 1611]])
    assert chart["type"] == "pie"


def test_averages_are_never_a_pie():
    chart = suggest_chart(["Rider", "AvgDeliveryMins"], [["A", 60], ["B", 41]])
    assert chart["type"] == "bar"


def test_very_different_scales_plot_only_the_first_number():
    rows = [["Cancelled", 5395, 6.69], ["Delivered", 73632, 91.31], ["Failed", 1611, 2.0]]
    chart = suggest_chart(["OrderStatus", "OrderCount", "SharePct"], rows)
    assert chart["y"] == ["OrderCount"]


def test_id_columns_are_not_plotted():
    chart = suggest_chart(["PartnerID", "FullName", "Deliveries"], [[1, "A", 50], [2, "B", 60]])
    assert chart["y"] == ["Deliveries"]


def test_single_row_or_no_numbers_gives_none():
    assert suggest_chart(["CityName", "Orders"], [["Bengaluru", 1283]])["type"] == "none"
    assert suggest_chart(["FullName", "Email"], [["a", "b"], ["c", "d"]])["type"] == "none"
    assert suggest_chart([], [])["type"] == "none"
