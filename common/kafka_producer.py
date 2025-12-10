"""
Kafka producer for event broadcasting
"""
import json
from typing import Dict, Any, Optional

try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    KafkaProducer = None
    KafkaError = Exception

from .config import Config
from .logger import setup_logger

logger = setup_logger(__name__)

class DepositEventProducer:
    """Kafka producer for deposit events"""
    
    def __init__(self):
        if not KAFKA_AVAILABLE:
            logger.warning("Kafka not available - events will be logged only")
            self.producer = None
            self.topic = Config.KAFKA_DEPOSIT_TOPIC
            return
            
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                **Config.KAFKA_PRODUCER_CONFIG
            )
            self.topic = Config.KAFKA_DEPOSIT_TOPIC
            logger.info(f"Kafka producer initialized: {Config.KAFKA_BOOTSTRAP_SERVERS}")
        except Exception as e:
            logger.warning(f"Failed to initialize Kafka producer: {e}")
            self.producer = None
            self.topic = Config.KAFKA_DEPOSIT_TOPIC
    
    def send_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """
        Send deposit event to Kafka
        
        Args:
            event_type: Type of event (detected, pending, confirmed, etc.)
            data: Event data
        
        Returns:
            True if sent successfully, False otherwise
        """
        event = {
            "event_type": event_type,
            "timestamp": data.get("timestamp"),
            "chain": data.get("chain"),
            "user_id": data.get("user_id"),
            "tx_hash": data.get("tx_hash"),
            "amount": data.get("amount"),
            "status": data.get("status"),
            "deposit_address": data.get("deposit_address"),
            "confirmations": data.get("confirmations", 0),
            "metadata": data.get("metadata", {})
        }
        
        # If Kafka not available, just log the event
        if not self.producer:
            logger.info(f"Event (no Kafka): {event_type} | {event}")
            return True
        
        try:
            future = self.producer.send(self.topic, value=event)
            record_metadata = future.get(timeout=10)
            
            logger.info(
                f"Event sent: {event_type} | "
                f"Topic: {record_metadata.topic} | "
                f"Partition: {record_metadata.partition} | "
                f"Offset: {record_metadata.offset}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Kafka event: {e}")
            logger.info(f"Event (failed): {event_type} | {event}")
            return False
    
    def send_deposit_detected(self, data: Dict[str, Any]):
        """Send deposit detected event"""
        self.send_event("deposit.detected", data)
    
    def send_deposit_pending(self, data: Dict[str, Any]):
        """Send deposit pending event"""
        self.send_event("deposit.pending", data)
    
    def send_deposit_confirming(self, data: Dict[str, Any]):
        """Send deposit confirming event"""
        self.send_event("deposit.confirming", data)
    
    def send_deposit_confirmed(self, data: Dict[str, Any]):
        """Send deposit confirmed event"""
        self.send_event("deposit.confirmed", data)
    
    def send_deposit_sweeping(self, data: Dict[str, Any]):
        """Send deposit sweeping event"""
        self.send_event("deposit.sweeping", data)
    
    def send_deposit_completed(self, data: Dict[str, Any]):
        """Send deposit completed event"""
        self.send_event("deposit.completed", data)
    
    def send_deposit_failed(self, data: Dict[str, Any]):
        """Send deposit failed event"""
        self.send_event("deposit.failed", data)
    
    def close(self):
        """Close producer connection"""
        if self.producer:
            try:
                self.producer.flush()
                self.producer.close()
            except Exception as e:
                logger.error(f"Error closing Kafka producer: {e}")
