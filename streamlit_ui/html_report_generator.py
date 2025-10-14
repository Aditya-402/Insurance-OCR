import os
from datetime import datetime

def generate_html_report(claim_id, procedure, l1_results, l2_results, charts, output_dir):
    """Generates a styled HTML report from rule evaluation results with embedded charts."""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"report_{claim_id}_{timestamp}.html")

    # --- CSS Styles ---
    html_style = """
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f9f9f9; }
        h1, h2 { color: #333; text-align: center; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; box-shadow: 0 2px 3px rgba(0,0,0,0.1); }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #e9ecef; color: #495057; }
        tr:nth-child(even) { background-color: #f8f9fa; }
        .status-pass { background-color: #d4edda; color: #155724; }
        .status-fail { background-color: #f8d7da; color: #721c24; }
        .status-warn { background-color: #fff3cd; color: #856404; }
        .status-submitted-yes { color: #155724; font-weight: bold; }
        .status-submitted-no { color: #721c24; font-weight: bold; }
        details { margin-top: 10px; }
        summary { font-weight: bold; cursor: pointer; }
        .reasoning { padding: 10px; background-color: #f1f1f1; border-radius: 5px; margin-top: 5px; white-space: pre-wrap; font-family: monospace; }
        .chart-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .chart-container { padding: 10px; border: 1px solid #eee; border-radius: 8px; background: #fff; }
    </style>
    """

    # --- HTML Body Construction ---
    html_body_parts = []

    # Header
    html_body_parts.append(f"""<h1>Rule Evaluation Report</h1>
    <p style='text-align:center;'><strong>Claim ID:</strong> {claim_id} | <strong>Procedure:</strong> {procedure} | <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    """)

    # Charts Section
    html_body_parts.append("<h2>Summary Charts</h2><div class='chart-grid'>")
    if charts.get('submission_status'):
        html_body_parts.append(f"<div class='chart-container'>{charts['submission_status']}</div>")
    if charts.get('l1_values'):
        html_body_parts.append(f"<div class='chart-container'>{charts['l1_values']}</div>")
    if charts.get('l2_evaluation'):
        html_body_parts.append(f"<div class='chart-container'>{charts['l2_evaluation']}</div>")
    html_body_parts.append("</div>")

    # L1 & L2 Rules Table
    html_body_parts.append("""
    <h2>Detailed Rule Evaluation</h2>
    <table>
        <thead>
            <tr>
                <th>Rule Level</th>
                <th>Rule ID / Description</th>
                <th>Status</th>
                <th>Details / Reasoning</th>
            </tr>
        </thead>
        <tbody>
    """)

    # L1 Rows
    for item in l1_results:
        status_class = "status-submitted-yes" if 'Yes' in item['status_text'] else "status-submitted-no"
        details_html = ""
        if item.get('l1_rules'):
            details_list = [f"<li><em>{l1.get('description', 'N/A')}:</em> <code>{l1.get('value', 'N/A')}</code></li>" for l1 in item['l1_rules']]
            details_html = f"<ul>{''.join(details_list)}</ul>"

        html_body_parts.append(f"""
        <tr>
            <td>L1</td>
            <td><b>{item['rule_id']}:</b> {item['question']}</td>
            <td><span class='{status_class}'>{item['status_text']}</span></td>
            <td>{details_html}</td>
        </tr>
        """)

    # L2 Rows
    if l2_results:
        for result in l2_results:
            decision = result.get('gemini_evaluation', 'Cannot Determine')
            row_class = ''
            if decision == 'Pass': row_class = 'status-pass'
            elif decision == 'Fail': row_class = 'status-fail'
            else: row_class = 'status-warn'

            reasoning = result.get('raw_evaluation', 'No reasoning provided.')
            reasoning_html = f"<details><summary>View Reasoning</summary><div class='reasoning'>{reasoning}</div></details>"

            html_body_parts.append(f"""
            <tr class='{row_class}'>
                <td>L2</td>
                <td>{result['description']}</td>
                <td><b>{decision}</b></td>
                <td>{reasoning_html}</td>
            </tr>
            """)

    html_body_parts.append("</tbody></table>")

    # --- Final HTML Document ---
    final_html_body = "\n".join(html_body_parts)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Rule Report for {claim_id}</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        {html_style}
    </head>
    <body>
        {final_html_body}
    </body>
    </html>
    """

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return filename
    except Exception as e:
        return str(e)
