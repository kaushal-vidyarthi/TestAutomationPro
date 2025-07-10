"""
HTML report generator for test execution results
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
from jinja2 import Template, Environment, FileSystemLoader
import base64
import os

class HTMLReporter:
    """Generates comprehensive HTML reports for test execution results"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.reports_dir = Path(config.get('reports_dir', 'reports'))
        self.html_reports_dir = self.reports_dir / 'html'
        self.templates_dir = Path(__file__).parent.parent / 'templates'
        
        # Create directories
        self.html_reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True
        )
        
        # Add custom filters
        self._setup_jinja_filters()
    
    def _setup_jinja_filters(self):
        """Setup custom Jinja2 filters"""
        
        def format_duration(seconds):
            """Format duration in human-readable format"""
            if not seconds:
                return "0s"
            
            if seconds < 1:
                return f"{int(seconds * 1000)}ms"
            elif seconds < 60:
                return f"{seconds:.1f}s"
            elif seconds < 3600:
                minutes = int(seconds // 60)
                remaining_seconds = seconds % 60
                return f"{minutes}m {remaining_seconds:.1f}s"
            else:
                hours = int(seconds // 3600)
                remaining_minutes = int((seconds % 3600) // 60)
                return f"{hours}h {remaining_minutes}m"
        
        def format_timestamp(timestamp):
            """Format timestamp for display"""
            if isinstance(timestamp, str):
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    return dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    return timestamp
            elif isinstance(timestamp, datetime):
                return timestamp.strftime("%Y-%m-%d %H:%M:%S")
            return str(timestamp)
        
        def status_class(status):
            """Get CSS class for status"""
            status_classes = {
                'Passed': 'status-passed',
                'Failed': 'status-failed',
                'Error': 'status-failed',
                'Skipped': 'status-skipped',
                'Running': 'status-running',
                'Pending': 'status-pending'
            }
            return status_classes.get(status, 'status-unknown')
        
        def percentage(value, total):
            """Calculate percentage"""
            if total == 0:
                return 0
            return round((value / total) * 100, 1)
        
        def truncate_text(text, length=100):
            """Truncate text to specified length"""
            if not text:
                return ""
            if len(text) <= length:
                return text
            return text[:length] + "..."
        
        def embed_image(image_path):
            """Embed image as base64 data URI"""
            try:
                if not image_path or not Path(image_path).exists():
                    return ""
                
                with open(image_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode()
                
                # Determine MIME type
                ext = Path(image_path).suffix.lower()
                mime_types = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.svg': 'image/svg+xml'
                }
                mime_type = mime_types.get(ext, 'image/png')
                
                return f"data:{mime_type};base64,{image_data}"
            except Exception as e:
                logging.warning(f"Failed to embed image {image_path}: {e}")
                return ""
        
        # Register filters
        self.jinja_env.filters['format_duration'] = format_duration
        self.jinja_env.filters['format_timestamp'] = format_timestamp
        self.jinja_env.filters['status_class'] = status_class
        self.jinja_env.filters['percentage'] = percentage
        self.jinja_env.filters['truncate_text'] = truncate_text
        self.jinja_env.filters['embed_image'] = embed_image
    
    async def generate_execution_report(self, report_data: Dict[str, Any]) -> Path:
        """Generate comprehensive HTML execution report"""
        try:
            # Prepare report data
            processed_data = self._process_report_data(report_data)
            
            # Load template
            template = self.jinja_env.get_template('report_template.html')
            
            # Generate HTML content
            html_content = template.render(**processed_data)
            
            # Generate filename
            execution_id = report_data.get('execution_id', 'unknown')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_execution_{execution_id}_{timestamp}.html"
            
            # Write report file
            report_path = self.html_reports_dir / filename
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logging.info(f"Generated HTML report: {report_path}")
            return report_path
            
        except Exception as e:
            logging.error(f"Failed to generate HTML report: {e}")
            raise
    
    def _process_report_data(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and enhance report data for template rendering"""
        processed_data = {
            'report_title': f"Test Execution Report - {report_data.get('execution_id', 'Unknown')}",
            'generation_time': datetime.now(),
            'execution_id': report_data.get('execution_id'),
            'execution_time': report_data.get('execution_time'),
            'summary': report_data.get('summary', {}),
            'results': [],
            'charts_data': {},
            'environment_info': self._get_environment_info(),
            'config': self.config
        }
        
        # Process test results
        results = report_data.get('results', [])
        processed_results = []
        
        for result in results:
            processed_result = {
                'test_case_id': result.test_case_id,
                'execution_id': result.execution_id,
                'status': result.status,
                'start_time': result.start_time,
                'end_time': result.end_time,
                'duration': result.duration,
                'error_message': result.error_message,
                'stack_trace': result.stack_trace,
                'screenshots': result.screenshots,
                'logs': result.logs,
                'performance_metrics': result.performance_metrics,
                'step_results': result.step_results
            }
            processed_results.append(processed_result)
        
        processed_data['results'] = processed_results
        
        # Generate charts data
        processed_data['charts_data'] = self._generate_charts_data(processed_results, processed_data['summary'])
        
        # Add statistics
        processed_data['statistics'] = self._calculate_statistics(processed_results)
        
        return processed_data
    
    def _get_environment_info(self) -> Dict[str, Any]:
        """Get environment information for the report"""
        import platform
        import sys
        
        return {
            'python_version': sys.version,
            'platform': platform.platform(),
            'hostname': platform.node(),
            'processor': platform.processor(),
            'browser': self.config.get('browser', 'Unknown'),
            'headless': self.config.get('headless', False),
            'parallel_workers': self.config.get('parallel_workers', 1)
        }
    
    def _generate_charts_data(self, results: List[Dict[str, Any]], summary: Dict[str, Any]) -> Dict[str, Any]:
        """Generate data for charts and visualizations"""
        charts_data = {}
        
        # Status distribution pie chart
        charts_data['status_distribution'] = {
            'labels': ['Passed', 'Failed', 'Error', 'Skipped'],
            'data': [
                summary.get('passed', 0),
                summary.get('failed', 0),
                summary.get('errors', 0),
                summary.get('skipped', 0)
            ],
            'colors': ['#28a745', '#dc3545', '#fd7e14', '#6c757d']
        }
        
        # Duration timeline
        timeline_data = []
        for result in results:
            if result.get('start_time') and result.get('duration'):
                timeline_data.append({
                    'test_id': result['test_case_id'],
                    'start_time': result['start_time'].isoformat() if isinstance(result['start_time'], datetime) else result['start_time'],
                    'duration': result['duration'],
                    'status': result['status']
                })
        
        charts_data['timeline'] = timeline_data
        
        # Performance metrics
        if results:
            perf_data = []
            for result in results:
                metrics = result.get('performance_metrics', {})
                if metrics:
                    perf_data.append({
                        'test_id': result['test_case_id'],
                        'load_time': metrics.get('load_time', 0),
                        'dom_ready': metrics.get('dom_ready', 0),
                        'memory_usage': metrics.get('memory_usage', 0)
                    })
            
            charts_data['performance'] = perf_data
        
        return charts_data
    
    def _calculate_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate additional statistics for the report"""
        if not results:
            return {}
        
        durations = [r.get('duration', 0) for r in results if r.get('duration')]
        
        stats = {
            'total_tests': len(results),
            'avg_duration': sum(durations) / len(durations) if durations else 0,
            'min_duration': min(durations) if durations else 0,
            'max_duration': max(durations) if durations else 0,
            'fastest_test': None,
            'slowest_test': None
        }
        
        # Find fastest and slowest tests
        if durations:
            min_duration = min(durations)
            max_duration = max(durations)
            
            for result in results:
                if result.get('duration') == min_duration:
                    stats['fastest_test'] = result
                if result.get('duration') == max_duration:
                    stats['slowest_test'] = result
        
        # Error analysis
        error_types = {}
        for result in results:
            if result.get('status') in ['Failed', 'Error'] and result.get('error_message'):
                error_msg = result['error_message']
                # Categorize errors by type
                if 'timeout' in error_msg.lower():
                    error_types['Timeout'] = error_types.get('Timeout', 0) + 1
                elif 'element not found' in error_msg.lower():
                    error_types['Element Not Found'] = error_types.get('Element Not Found', 0) + 1
                elif 'assertion' in error_msg.lower():
                    error_types['Assertion Failed'] = error_types.get('Assertion Failed', 0) + 1
                else:
                    error_types['Other'] = error_types.get('Other', 0) + 1
        
        stats['error_types'] = error_types
        
        return stats
    
    def generate_summary_report(self, executions: List[Dict[str, Any]]) -> Path:
        """Generate summary report for multiple executions"""
        try:
            # Process data for summary
            summary_data = {
                'report_title': 'Test Execution Summary',
                'generation_time': datetime.now(),
                'executions': executions,
                'overall_stats': self._calculate_overall_stats(executions),
                'trends': self._calculate_trends(executions),
                'environment_info': self._get_environment_info()
            }
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_summary_{timestamp}.html"
            
            # Use a simplified template or create inline HTML
            html_content = self._generate_summary_html(summary_data)
            
            # Write report file
            report_path = self.html_reports_dir / filename
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logging.info(f"Generated summary report: {report_path}")
            return report_path
            
        except Exception as e:
            logging.error(f"Failed to generate summary report: {e}")
            raise
    
    def _calculate_overall_stats(self, executions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall statistics across multiple executions"""
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_duration = 0
        
        for execution in executions:
            summary = execution.get('summary', {})
            total_tests += summary.get('total', 0)
            total_passed += summary.get('passed', 0)
            total_failed += summary.get('failed', 0)
            total_duration += summary.get('total_duration', 0)
        
        return {
            'total_executions': len(executions),
            'total_tests': total_tests,
            'total_passed': total_passed,
            'total_failed': total_failed,
            'overall_pass_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0,
            'total_duration': total_duration,
            'avg_execution_duration': total_duration / len(executions) if executions else 0
        }
    
    def _calculate_trends(self, executions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate trends over time"""
        if len(executions) < 2:
            return {}
        
        # Sort by execution time
        sorted_executions = sorted(
            executions, 
            key=lambda x: x.get('execution_time', datetime.min)
        )
        
        trends = {
            'pass_rate_trend': [],
            'duration_trend': [],
            'test_count_trend': []
        }
        
        for execution in sorted_executions:
            summary = execution.get('summary', {})
            execution_time = execution.get('execution_time')
            
            if execution_time:
                trends['pass_rate_trend'].append({
                    'time': execution_time.isoformat() if isinstance(execution_time, datetime) else execution_time,
                    'value': summary.get('pass_rate', 0)
                })
                trends['duration_trend'].append({
                    'time': execution_time.isoformat() if isinstance(execution_time, datetime) else execution_time,
                    'value': summary.get('total_duration', 0)
                })
                trends['test_count_trend'].append({
                    'time': execution_time.isoformat() if isinstance(execution_time, datetime) else execution_time,
                    'value': summary.get('total', 0)
                })
        
        return trends
    
    def _generate_summary_html(self, data: Dict[str, Any]) -> str:
        """Generate summary HTML when template is not available"""
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{data['report_title']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f8f9fa; padding: 20px; border-radius: 5px; }}
                .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
                .stat-card {{ background: white; border: 1px solid #ddd; padding: 15px; border-radius: 5px; flex: 1; }}
                .executions {{ margin: 20px 0; }}
                .execution {{ background: #f8f9fa; margin: 10px 0; padding: 15px; border-radius: 5px; }}
                .status-passed {{ color: #28a745; }}
                .status-failed {{ color: #dc3545; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{data['report_title']}</h1>
                <p>Generated: {data['generation_time'].strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <h3>Total Executions</h3>
                    <p>{data['overall_stats'].get('total_executions', 0)}</p>
                </div>
                <div class="stat-card">
                    <h3>Total Tests</h3>
                    <p>{data['overall_stats'].get('total_tests', 0)}</p>
                </div>
                <div class="stat-card">
                    <h3>Overall Pass Rate</h3>
                    <p>{data['overall_stats'].get('overall_pass_rate', 0):.1f}%</p>
                </div>
            </div>
            
            <div class="executions">
                <h2>Recent Executions</h2>
                {self._generate_executions_html(data['executions'])}
            </div>
        </body>
        </html>
        """
        return html
    
    def _generate_executions_html(self, executions: List[Dict[str, Any]]) -> str:
        """Generate HTML for executions list"""
        html_parts = []
        
        for execution in executions[-10:]:  # Show last 10 executions
            summary = execution.get('summary', {})
            execution_time = execution.get('execution_time', '')
            
            html_parts.append(f"""
                <div class="execution">
                    <h4>Execution {execution.get('execution_id', 'Unknown')}</h4>
                    <p>Time: {execution_time}</p>
                    <p>Tests: {summary.get('total', 0)} | 
                       <span class="status-passed">Passed: {summary.get('passed', 0)}</span> | 
                       <span class="status-failed">Failed: {summary.get('failed', 0)}</span></p>
                    <p>Duration: {summary.get('total_duration', 0):.2f}s</p>
                </div>
            """)
        
        return ''.join(html_parts)
    
    def export_report_data(self, report_data: Dict[str, Any], format: str = 'json') -> Path:
        """Export report data in various formats"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if format.lower() == 'json':
                filename = f"test_data_{timestamp}.json"
                export_path = self.reports_dir / filename
                
                # Serialize datetime objects
                serializable_data = self._make_serializable(report_data)
                
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(serializable_data, f, indent=2)
                    
            elif format.lower() == 'csv':
                filename = f"test_results_{timestamp}.csv"
                export_path = self.reports_dir / filename
                
                self._export_to_csv(report_data, export_path)
                
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logging.info(f"Exported report data to: {export_path}")
            return export_path
            
        except Exception as e:
            logging.error(f"Failed to export report data: {e}")
            raise
    
    def _make_serializable(self, obj):
        """Make object JSON serializable"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._make_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            return self._make_serializable(obj.__dict__)
        else:
            return obj
    
    def _export_to_csv(self, report_data: Dict[str, Any], export_path: Path):
        """Export test results to CSV format"""
        import csv
        
        results = report_data.get('results', [])
        
        with open(export_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'test_case_id', 'execution_id', 'status', 'start_time', 
                'end_time', 'duration', 'error_message'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                row = {
                    'test_case_id': getattr(result, 'test_case_id', ''),
                    'execution_id': getattr(result, 'execution_id', ''),
                    'status': getattr(result, 'status', ''),
                    'start_time': getattr(result, 'start_time', ''),
                    'end_time': getattr(result, 'end_time', ''),
                    'duration': getattr(result, 'duration', ''),
                    'error_message': getattr(result, 'error_message', '')
                }
                writer.writerow(row)
    
    def cleanup_old_reports(self, days: int = 30) -> int:
        """Clean up old report files"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted_count = 0
            
            for report_file in self.html_reports_dir.glob('*.html'):
                if report_file.stat().st_mtime < cutoff_date.timestamp():
                    report_file.unlink()
                    deleted_count += 1
            
            logging.info(f"Cleaned up {deleted_count} old report files")
            return deleted_count
            
        except Exception as e:
            logging.error(f"Failed to cleanup old reports: {e}")
            return 0
