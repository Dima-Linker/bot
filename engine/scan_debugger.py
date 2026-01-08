#!/usr/bin/env python3
"""
Scan Debug Reporter - Diagnostic tool for scanner coverage issues
Creates detailed scan reports to identify bottlenecks
"""

import time
from collections import defaultdict, Counter
from typing import Dict, List, Tuple

class ScanDebugger:
    """Tracks and reports scan metrics for diagnostic purposes"""
    
    def __init__(self):
        self.reset_metrics()
    
    def reset_metrics(self):
        """Reset all metrics for new scan"""
        self.scan_start_time = time.time()
        self.symbols_total = 0
        self.symbols_processed_ok = 0
        self.symbols_failed = 0
        self.error_reasons = Counter()
        self.alerts_by_module = Counter()
        self.alerts_sent_by_module = Counter()
        self.unique_symbols_sent = set()
        self.symbols_alert_count = Counter()
        self.kline_calls = 0
        self.api_errors = 0
        self.timeout_errors = 0
        self.rate_limit_hits = 0
    
    def set_total_symbols(self, count: int):
        """Set the expected total symbol count"""
        self.symbols_total = count
    
    def record_symbol_success(self, symbol: str):
        """Record successful symbol processing"""
        self.symbols_processed_ok += 1
    
    def record_symbol_failure(self, symbol: str, error_reason: str):
        """Record symbol processing failure"""
        self.symbols_failed += 1
        self.error_reasons[error_reason] += 1
    
    def record_alert_generated(self, module: str, symbol: str | None = None):
        """Record alert generation"""
        self.alerts_by_module[module] += 1
        if symbol:
            self.symbols_alert_count[symbol] += 1
            self.unique_symbols_sent.add(symbol)
    
    def record_alert_sent(self, module: str):
        """Record alert actually sent"""
        self.alerts_sent_by_module[module] += 1
    
    def record_api_call(self):
        """Record API call made"""
        self.kline_calls += 1
    
    def record_api_error(self, error_type: str):
        """Record API error"""
        self.api_errors += 1
        if 'timeout' in error_type.lower():
            self.timeout_errors += 1
        elif 'rate' in error_type.lower() or '429' in error_type:
            self.rate_limit_hits += 1
    
    def generate_debug_report(self) -> Dict:
        """Generate comprehensive debug report"""
        duration = time.time() - self.scan_start_time
        
        # Top 10 symbols by alert count
        top_symbols = self.symbols_alert_count.most_common(10)
        
        report = {
            'scan_duration_seconds': round(duration, 2),
            'symbols_total': self.symbols_total,
            'symbols_processed_ok': self.symbols_processed_ok,
            'symbols_failed': self.symbols_failed,
            'processing_success_rate': round((self.symbols_processed_ok / self.symbols_total * 100) if self.symbols_total > 0 else 0, 1),
            'error_reasons': dict(self.error_reasons),
            'alerts_generated_by_module': dict(self.alerts_by_module),
            'alerts_sent_by_module': dict(self.alerts_sent_by_module),
            'unique_symbols_sent': len(self.unique_symbols_sent),
            'top10_symbols_by_alerts': [(symbol, count) for symbol, count in top_symbols],
            'api_metrics': {
                'kline_calls': self.kline_calls,
                'api_errors': self.api_errors,
                'timeout_errors': self.timeout_errors,
                'rate_limit_hits': self.rate_limit_hits
            }
        }
        
        return report
    
    def generate_simple_summary(self) -> str:
        """Generate simple console summary"""
        report = self.generate_debug_report()
        
        summary = f"""
[SCAN-DEBUG-REPORT]
Duration: {report['scan_duration_seconds']}s
Symbols: {report['symbols_processed_ok']}/{report['symbols_total']} processed ({report['processing_success_rate']}%)
Failed: {report['symbols_failed']} symbols
Unique symbols with alerts: {report['unique_symbols_sent']}

Errors:
"""
        for reason, count in report['error_reasons'].items():
            summary += f"  {reason}: {count}\n"
        
        summary += "\nAlerts by module:\n"
        for module, count in report['alerts_generated_by_module'].items():
            sent = report['alerts_sent_by_module'].get(module, 0)
            summary += f"  {module}: {count} generated, {sent} sent\n"
        
        if report['top10_symbols_by_alerts']:
            summary += "\nTop symbols by alerts:\n"
            for symbol, count in report['top10_symbols_by_alerts'][:5]:
                summary += f"  {symbol}: {count} alerts\n"
        
        return summary.strip()

# Global instance
scan_debugger = ScanDebugger()

def get_scan_debugger() -> ScanDebugger:
    """Get global scan debugger instance"""
    return scan_debugger

__all__ = ['ScanDebugger', 'get_scan_debugger']