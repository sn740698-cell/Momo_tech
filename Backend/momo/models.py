import uuid
from django.db import models
from django.utils import timezone


class CompanionSession(models.Model):
    """
    Tracks companion active runtime session, usage stats, and client telemetry.
    """
    session_id = models.CharField(max_length=64, unique=True, default=uuid.uuid4, db_index=True)
    user_name = models.CharField(max_length=64, default="User")
    active_app = models.CharField(max_length=128, blank=True, default="")
    idle_seconds = models.IntegerField(default=0)
    total_messages = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    last_active_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Session {self.session_id[:8]} ({self.user_name})"

    @property
    def session_duration_minutes(self) -> int:
        now = timezone.now()
        delta = now - self.started_at
        return int(delta.total_seconds() // 60)


class DeviceConnection(models.Model):
    """
    Tracks registered physical ESP32 robots, connection health, battery, and signal strength.
    """
    device_id = models.CharField(max_length=64, unique=True, db_index=True)
    device_type = models.CharField(max_length=32, default="ESP32")
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    is_online = models.BooleanField(default=False)
    battery_pct = models.IntegerField(null=True, blank=True)
    rssi = models.IntegerField(null=True, blank=True)
    firmware_version = models.CharField(max_length=32, default="1.0.0")
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "ONLINE" if self.is_online else "OFFLINE"
        return f"[{status}] {self.device_id} ({self.device_type})"


class WorkflowExecution(models.Model):
    """
    Persists multi-agent RAG workflow execution runs with tenant isolation boundaries.
    """
    execution_id = models.CharField(max_length=64, unique=True, db_index=True)
    tenant_id = models.CharField(max_length=64, default="default", db_index=True)
    project_id = models.CharField(max_length=64, default="default", db_index=True)
    user_id = models.CharField(max_length=64, default="default")
    request_input = models.TextField()
    status = models.CharField(max_length=32, default="pending", db_index=True)
    is_valid = models.BooleanField(default=False)
    confidence = models.FloatField(default=0.0)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=2)
    final_output = models.TextField(blank=True, default="")
    evaluation_result = models.JSONField(default=dict, blank=True)
    retrieved_sources = models.JSONField(default=list, blank=True)
    plan = models.JSONField(default=dict, blank=True)
    errors = models.JSONField(default=list, blank=True)
    duration_seconds = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.status}] {self.execution_id} ({self.tenant_id}/{self.project_id})"

