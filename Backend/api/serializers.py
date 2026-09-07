"""
Django REST Framework serializers for MOMO API.
"""
from rest_framework import serializers
from memory.models import MemoryItem, MessageLog, UserPreference


class MemoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemoryItem
        fields = ['id', 'key', 'value', 'confidence', 'created_at', 'updated_at']


class MessageLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageLog
        fields = ['id', 'role', 'content', 'expression', 'animation', 'thinking', 'session_id', 'created_at']


class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = ['key', 'value', 'updated_at']


class PrivacySettingsSerializer(serializers.Serializer):
    camera_enabled = serializers.BooleanField(required=False)
    microphone_enabled = serializers.BooleanField(required=False)
    memory_enabled = serializers.BooleanField(required=False)
    activity_tracking_enabled = serializers.BooleanField(required=False)


class FinancialInsightSerializer(serializers.Serializer):
    invoice_number = serializers.CharField()
    invoice_total = serializers.FloatField()
    amount_paid = serializers.FloatField()
    balance_due = serializers.FloatField()
    currency = serializers.CharField(default="INR")
    due_date = serializers.CharField(allow_null=True, required=False)
    payment_status = serializers.CharField()
    confidence = serializers.FloatField(default=1.0)
    line_items = serializers.ListField(child=serializers.DictField(), required=False)
    notes = serializers.CharField(allow_null=True, required=False)
