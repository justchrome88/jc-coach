from app.db.models import Match
from app.services.ingestion.structured_import import import_rows
from app.services.report_generator import generate_report, markdown_to_html, render_markdown_report


def test_render_markdown_report(sample_rows):
    matches = [Match(**row, source="test", external_match_id=f"id-{index}") for index, row in enumerate(sample_rows)]
    from app.services.analytics import compare_periods, detect_weaknesses, get_map_stats, get_summary
    from app.services.coach_rules import build_coach_focus

    summary = get_summary(matches)
    comparison = compare_periods(matches)
    map_stats = get_map_stats(matches)
    payload = {
        "summary": summary,
        "period_comparison": comparison,
        "map_stats": map_stats,
        "detected_weaknesses": detect_weaknesses(summary, comparison, map_stats),
        "coach_focus": build_coach_focus(summary, comparison, map_stats),
    }

    markdown = render_markdown_report(payload)

    assert "# CS2 Coach Report" in markdown
    assert "## Фокус на 7 дней" in markdown


def test_generate_report_persists(db, sample_rows):
    import_rows(db, sample_rows, source="test")

    report = generate_report(db)

    assert report.id is not None
    assert report.matches_count == 2
    assert "CS2 Coach Report" in report.report_markdown
    assert "<h1>CS2 Coach Report</h1>" in markdown_to_html(report.report_markdown)
