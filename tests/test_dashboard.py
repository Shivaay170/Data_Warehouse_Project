"""Tests for Streamlit dashboard import and component integrity."""

def test_dashboard_import():
    """Verify that dashboard module imports without exceptions."""
    import src.dashboard.app as app
    assert hasattr(app, "render_dashboard")
    assert hasattr(app, "load_kpis")
    assert hasattr(app, "load_rollup")
    assert hasattr(app, "load_country_data")
    assert hasattr(app, "load_segmentation")
    assert hasattr(app, "load_market_basket")
    assert hasattr(app, "load_churn")
    assert hasattr(app, "load_forecast")
