import pytest
import os
from datetime import datetime

def main():
    """Runs pytest and generates a timestamped HTML report."""
    # Create the reports directory if it doesn't exist
    reports_dir = 'reports'
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)

    # Generate a timestamped filename for the report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = os.path.join(reports_dir, f"test_report_{timestamp}.html")

    # Run pytest with the html report argument
    print(f"Running tests and generating report at: {report_filename}")
    exit_code = pytest.main(['--html=' + report_filename, '--self-contained-html'])
    
    print(f"Tests finished with exit code: {exit_code}")

if __name__ == "__main__":
    main()
