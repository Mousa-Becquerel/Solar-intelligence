#!/usr/bin/env python3
"""
Memory Monitor for PV Market Analysis Flask App
Tracks memory usage and helps identify memory leaks
"""

import psutil
import time
import os
import gc
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import threading
import signal
import sys
import csv

class MemoryMonitor:
    def __init__(self, pid=None, interval=2):
        self.pid = pid or os.getpid()
        self.interval = interval
        self.running = False
        self.data = []
        self.start_time = datetime.now()
        
        print(f"CRITICAL: Monitoring interval: {self.interval} seconds")
        
        # Memory thresholds (MB)
        self.memory_warning_threshold = 300
        self.memory_critical_threshold = 400
        
        # Memory leak detection
        self.memory_leak_threshold = 50  # MB growth in 10 data points
        self.memory_history = []
        
        # File to store monitoring data
        self.log_file = f"memory_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Control flags
        self.force_stop = False
        
        # Alert tracking
        self.alert_count = 0
        self.last_alert_time = None
        
    def get_process_memory(self):
        """Get memory usage for the target process"""
        try:
            process = psutil.Process(self.pid)
            memory_info = process.memory_info()
            
            return {
                'timestamp': datetime.now(),
                'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size in MB
                'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size in MB
                'cpu_percent': process.cpu_percent(),
                'memory_percent': process.memory_percent(),
                'num_threads': process.num_threads(),
                'open_files': len(process.open_files()),
            }
        except psutil.NoSuchProcess:
            return None
            
    def get_system_memory(self):
        """Get system memory statistics"""
        memory = psutil.virtual_memory()
        return {
            'total_gb': memory.total / 1024 / 1024 / 1024,
            'available_gb': memory.available / 1024 / 1024 / 1024,
            'used_percent': memory.percent,
            'free_gb': memory.free / 1024 / 1024 / 1024
        }
    
    def get_python_memory_details(self):
        """Get Python-specific memory details"""
        if self.pid == os.getpid():
            # Only if monitoring current process
            try:
                import tracemalloc
                if tracemalloc.is_tracing():
                    current, peak = tracemalloc.get_traced_memory()
                    return {
                        'traced_current_mb': current / 1024 / 1024,
                        'traced_peak_mb': peak / 1024 / 1024
                    }
            except:
                pass
        return {}
    
    def get_memory_info(self):
        """Get detailed memory information"""
        try:
            # Process memory
            process = psutil.Process()
            proc_mem = process.memory_info()
            
            # System memory
            sys_mem = psutil.virtual_memory()
            
            return {
                'timestamp': datetime.now(),
                'rss_mb': proc_mem.rss / 1024 / 1024,
                'vms_mb': proc_mem.vms / 1024 / 1024,
                'memory_percent': process.memory_percent(),
                'system_available_gb': sys_mem.available / 1024 / 1024 / 1024,
                'system_used_percent': sys_mem.percent
            }
        except Exception as e:
            print(f"Error getting memory info: {e}")
            return None
    
    def check_memory_alerts(self, mem_info):
        """Check for memory alerts and warnings"""
        if not mem_info:
            return
            
        rss_mb = mem_info['rss_mb']
        
        # Check for high memory usage
        if rss_mb > self.memory_critical_threshold:
            print(f"CRITICAL: HIGH MEMORY USAGE: {rss_mb:.1f}MB RSS")
            self.alert_count += 1
            self.last_alert_time = datetime.now()
        elif rss_mb > self.memory_warning_threshold:
            print(f"WARNING: Memory usage: {rss_mb:.1f}MB RSS")
        
        # Check for memory leaks
        self.memory_history.append(rss_mb)
        if len(self.memory_history) > 10:
            self.memory_history.pop(0)
            
        if len(self.memory_history) >= 10:
            # Check if memory has grown significantly
            memory_trend = self.memory_history[-1] - self.memory_history[0]
            if memory_trend > self.memory_leak_threshold:
                print(f"ALERT: POTENTIAL MEMORY LEAK DETECTED: +{memory_trend:.1f}MB growth in recent data")
            elif memory_trend > self.memory_leak_threshold / 2:
                print(f"WARNING: MODERATE MEMORY GROWTH: +{memory_trend:.1f}MB in recent data")
    
    def monitor_loop(self):
        """Main monitoring loop"""
        print(f"Starting memory monitoring (PID: {os.getpid()})")
        
        # Create CSV file with headers
        with open(self.log_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'rss_mb', 'vms_mb', 'memory_percent', 'system_available_gb', 'system_used_percent'])
        
        start_time = datetime.now()
        
        while self.running and not self.force_stop:
            try:
                mem_info = self.get_memory_info()
                if mem_info:
                    # Log to console
                    print(f"Memory: RSS={mem_info['rss_mb']:.1f}MB, "
                          f"VMS={mem_info['vms_mb']:.1f}MB, "
                          f"Sys Available={mem_info['system_available_gb']:.1f}GB")
                    
                    # Check for alerts
                    self.check_memory_alerts(mem_info)
                    
                    # Log to CSV
                    with open(self.log_file, 'a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([
                            mem_info['timestamp'].isoformat(),
                            mem_info['rss_mb'],
                            mem_info['vms_mb'],
                            mem_info['memory_percent'],
                            mem_info['system_available_gb'],
                            mem_info['system_used_percent']
                        ])
                
                time.sleep(self.interval)
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(self.interval)
        
        # Final report
        runtime = (datetime.now() - start_time).total_seconds()
        print(f"Memory monitoring stopped. Runtime: {runtime:.1f} seconds")
        
        # Generate analysis report
        self.generate_analysis_report()
    
    def generate_analysis_report(self):
        """Generate analysis report from collected data"""
        try:
            # Read the CSV data
            df = pd.read_csv(self.log_file)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            if len(df) == 0:
                print("No data collected for analysis")
                return
            
            print("\nTREND: MEMORY ANALYSIS REPORT")
            print("=" * 50)
            
            # Basic statistics
            print(f"Data Points Collected: {len(df)}")
            print(f"CHART: Monitoring Duration: {(df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).total_seconds():.1f} seconds")
            print(f"TREND: Peak RSS Memory: {df['rss_mb'].max():.1f} MB")
            print(f"TREND: Peak VMS Memory: {df['vms_mb'].max():.1f} MB")
            print(f"TREND: Average RSS Memory: {df['rss_mb'].mean():.1f} MB")
            print(f"TREND: Memory Growth: {df['rss_mb'].iloc[-1] - df['rss_mb'].iloc[0]:+.1f} MB")
            
            # Memory trend analysis
            if len(df) >= 10:
                recent_growth = df['rss_mb'].iloc[-5:].mean() - df['rss_mb'].iloc[:5].mean()
                if recent_growth > 20:
                    print(f"ALERT: POTENTIAL MEMORY LEAK DETECTED: +{recent_growth:.1f}MB growth in recent data")
                elif recent_growth > 10:
                    print(f"WARNING: MODERATE MEMORY GROWTH: +{recent_growth:.1f}MB in recent data")
                else:
                    print(f"Memory trend: {recent_growth:+.1f}MB (stable)")
            
            # Alert summary
            if self.alert_count > 0:
                print(f"Total Alerts Generated: {self.alert_count}")
                if self.last_alert_time:
                    print(f"Last Alert: {self.last_alert_time}")
            
            # Generate plot if matplotlib is available
            try:
                import matplotlib.pyplot as plt
                
                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
                
                # Memory usage over time
                ax1.plot(df['timestamp'], df['rss_mb'], label='RSS Memory (MB)', color='blue')
                ax1.plot(df['timestamp'], df['vms_mb'], label='VMS Memory (MB)', color='orange', alpha=0.7)
                ax1.axhline(y=self.memory_warning_threshold, color='yellow', linestyle='--', label='Warning Threshold')
                ax1.axhline(y=self.memory_critical_threshold, color='red', linestyle='--', label='Critical Threshold')
                ax1.set_ylabel('Memory (MB)')
                ax1.set_title('Memory Usage Over Time')
                ax1.legend()
                ax1.grid(True, alpha=0.3)
                
                # System memory
                ax2.plot(df['timestamp'], df['system_available_gb'], label='System Available (GB)', color='green')
                ax2.plot(df['timestamp'], df['system_used_percent'], label='System Used (%)', color='red')
                ax2.set_ylabel('System Memory')
                ax2.set_xlabel('Time')
                ax2.set_title('System Memory Metrics')
                ax2.legend()
                ax2.grid(True, alpha=0.3)
                
                plt.tight_layout()
                
                # Save plot
                plot_filename = f"memory_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                plt.savefig(plot_filename, dpi=150, bbox_inches='tight')
                plt.close()
                
                print(f"CHART: Memory plot saved to: {plot_filename}")
                
            except ImportError:
                print("Matplotlib not available for plotting")
            except Exception as e:
                print(f"Error generating plot: {e}")
                
        except Exception as e:
            print(f"Error generating analysis report: {e}")
    
    def start(self):
        """Start monitoring in a separate thread"""
        if self.running:
            print("Monitoring already running")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("Memory monitoring started")
    
    def stop(self):
        """Stop monitoring"""
        if not self.running:
            print("Monitoring not running")
            return
        
        print("Stopping memory monitoring...")
        self.running = False
        
        # Wait for thread to finish (with timeout)
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=5.0)
        
        print("Memory monitoring stopped")
    
    def force_stop_monitoring(self):
        """Force stop monitoring immediately"""
        print("Force stopping memory monitoring...")
        self.force_stop = True
        self.running = False

def find_flask_process():
    """Find running Flask process"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if 'app.py' in cmdline or 'flask' in cmdline.lower():
                return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor memory usage of PV Market Analysis Flask app')
    parser.add_argument('--pid', type=int, help='Process ID to monitor (auto-detect if not specified)')
    parser.add_argument('--interval', type=float, default=2, help='Monitoring interval in seconds (default: 2)')
    parser.add_argument('--auto-find', action='store_true', help='Auto-find Flask process')
    
    args = parser.parse_args()
    
    # Determine PID
    target_pid = args.pid
    if not target_pid and args.auto_find:
        target_pid = find_flask_process()
        if target_pid:
            print(f"🔍 Auto-detected Flask process: PID {target_pid}")
        else:
            print("❌ No Flask process found. Please specify --pid manually")
            return
    elif not target_pid:
        target_pid = os.getpid()
        print(f"🔍 Monitoring current process: PID {target_pid}")
    
    # Setup signal handler for graceful shutdown
    monitor = MemoryMonitor(target_pid, args.interval)
    
    def signal_handler(signum, frame):
        print("\n🛑 Stopping monitor...")
        monitor.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start monitoring
    monitor.start()

if __name__ == "__main__":
    main() 