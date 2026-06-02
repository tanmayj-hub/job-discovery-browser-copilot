from browser.placeholder import describe as describe_browser
from classifier.placeholder import describe as describe_classifier
from collectors.placeholder import describe as describe_collectors
from importer.placeholder import describe as describe_importer
from processing.placeholder import describe as describe_processing
from reports.placeholder import describe as describe_reports
from storage.placeholder import describe as describe_storage


def test_placeholder_modules_are_importable() -> None:
    assert describe_importer() == "importer placeholder"
    assert describe_classifier() == "classifier placeholder"
    assert describe_collectors() == "collectors placeholder"
    assert describe_browser() == "browser placeholder"
    assert describe_processing() == "processing placeholder"
    assert describe_storage() == "storage placeholder"
    assert describe_reports() == "reports placeholder"
