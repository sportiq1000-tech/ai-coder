"""
Security monitoring and logging system
Tracks blocked requests, attack patterns, and security events
"""
import json
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path
from collections import defaultdict
import hashlib
from utils.logger import logger


class SecurityMonitor:
    """
    Monitors and logs security events for analysis
    Helps identify attack patterns and false positives
    """
    
    def __init__(self, log_file: str = "logs/security_events.jsonl"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory stats (recent 1000 events)
        self.recent_events = []
        self.max_recent = 1000
        
        # Counters
        self.stats = {
            'total_blocks': 0,
            'prompt_injection_blocks': 0,
            'secret_extraction_blocks': 0,
            'by_pattern': defaultdict(int),
            'by_endpoint': defaultdict(int),
            'by_ip': defaultdict(int),
        }
        
        logger.info(f"SecurityMonitor initialized: {self.log_file}")
    
    def log_blocked_request(
        self,
        request_id: str,
        endpoint: str,
        client_ip: str,
        api_key_user: Optional[str],
        input_data: str,
        block_reason: str,
        matched_pattern: Optional[str] = None,
        attack_type: str = "unknown"
    ):
        """
        Log a blocked request for security analysis
        
        Args:
            request_id: Unique request identifier
            endpoint: API endpoint targeted
            client_ip: Client IP address
            api_key_user: Username from API key (if authenticated)
            input_data: The input that triggered the block (truncated for safety)
            block_reason: Human-readable reason
            matched_pattern: The regex pattern that matched
            attack_type: Type of attack (prompt_injection, secret_extraction, etc.)
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "event_type": "blocked_request",
            "attack_type": attack_type,
            "endpoint": endpoint,
            "client_ip": client_ip,
            "api_key_user": api_key_user or "anonymous",
            "input_hash": hashlib.sha256(input_data.encode()).hexdigest()[:16],
            "input_preview": input_data[:200] + ("..." if len(input_data) > 200 else ""),
            "block_reason": block_reason,
            "matched_pattern": matched_pattern,
        }
        
        # Write to file (append-only JSON Lines)
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(event) + '\n')
        except Exception as e:
            logger.error(f"Failed to write security log: {e}")
        
        # Update in-memory stats
        self.stats['total_blocks'] += 1
        if attack_type == "prompt_injection":
            self.stats['prompt_injection_blocks'] += 1
        elif attack_type == "secret_extraction":
            self.stats['secret_extraction_blocks'] += 1
        
        if matched_pattern:
            self.stats['by_pattern'][matched_pattern] += 1
        
        self.stats['by_endpoint'][endpoint] += 1
        self.stats['by_ip'][client_ip] += 1
        
        # Keep recent events in memory
        self.recent_events.append(event)
        if len(self.recent_events) > self.max_recent:
            self.recent_events.pop(0)
        
        # Log to application logger
        logger.warning(
            f"🚨 SECURITY BLOCK [{request_id}]: {attack_type} on {endpoint} "
            f"from {client_ip} ({api_key_user}) - Pattern: {matched_pattern}"
        )
    
    def log_suspicious_activity(
        self,
        request_id: str,
        endpoint: str,
        client_ip: str,
        activity_type: str,
        details: str
    ):
        """Log suspicious but not blocked activity"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "event_type": "suspicious_activity",
            "activity_type": activity_type,
            "endpoint": endpoint,
            "client_ip": client_ip,
            "details": details,
        }
        
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(event) + '\n')
        except Exception as e:
            logger.error(f"Failed to write security log: {e}")
        
        logger.info(f"⚠️ SUSPICIOUS [{request_id}]: {activity_type} - {details}")
    
    def get_recent_events(self, limit: int = 100) -> List[Dict]:
        """Get recent security events from memory"""
        return self.recent_events[-limit:]
    
    def get_stats(self) -> Dict:
        """Get current security statistics"""
        return {
            "total_blocks": self.stats['total_blocks'],
            "prompt_injection_blocks": self.stats['prompt_injection_blocks'],
            "secret_extraction_blocks": self.stats['secret_extraction_blocks'],
            "top_patterns": dict(sorted(
                self.stats['by_pattern'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]),
            "blocks_by_endpoint": dict(self.stats['by_endpoint']),
            "top_attacking_ips": dict(sorted(
                self.stats['by_ip'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]),
        }
    
    def get_events_from_file(
        self,
        limit: int = 100,
        attack_type: Optional[str] = None,
        endpoint: Optional[str] = None
    ) -> List[Dict]:
        """Read security events from log file with filters"""
        events = []
        
        try:
            if not self.log_file.exists():
                return []
            
            with open(self.log_file, 'r') as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        
                        # Apply filters
                        if attack_type and event.get("attack_type") != attack_type:
                            continue
                        if endpoint and event.get("endpoint") != endpoint:
                            continue
                        
                        events.append(event)
                    except json.JSONDecodeError:
                        continue
            
            # Return most recent events
            return events[-limit:]
        
        except Exception as e:
            logger.error(f"Failed to read security log: {e}")
            return []
    
    def analyze_attack_patterns(self) -> Dict:
        """Analyze attack patterns for trends"""
        events = self.get_events_from_file(limit=1000)
        
        if not events:
            return {"message": "No security events recorded yet"}
        
        # Group by hour
        hourly_attacks = defaultdict(int)
        attack_types = defaultdict(int)
        targeted_endpoints = defaultdict(int)
        
        for event in events:
            # Parse timestamp
            ts = datetime.fromisoformat(event['timestamp'])
            hour_key = ts.strftime("%Y-%m-%d %H:00")
            hourly_attacks[hour_key] += 1
            
            # Count attack types
            attack_types[event.get('attack_type', 'unknown')] += 1
            
            # Count endpoints
            targeted_endpoints[event.get('endpoint', 'unknown')] += 1
        
        return {
            "total_events": len(events),
            "hourly_trend": dict(sorted(hourly_attacks.items())[-24:]),  # Last 24 hours
            "attack_type_distribution": dict(attack_types),
            "most_targeted_endpoints": dict(sorted(
                targeted_endpoints.items(),
                key=lambda x: x[1],
                reverse=True
            )),
            "analysis_period": f"Last {len(events)} events"
        }


# Global instance
security_monitor = SecurityMonitor()