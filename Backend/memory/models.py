from django.db import models


class UserPreference(models.Model):
    """
    Key-value store for user personality settings, companion behaviors, and preferences.
    """
    key = models.CharField(max_length=128, unique=True, db_index=True)
    value = models.TextField(help_text="JSON string or plain text preference value")
    category = models.CharField(max_length=64, default="general", db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'key']

    def __str__(self):
        return f"{self.category}:{self.key} = {self.value[:30]}"


class FactMemory(models.Model):
    """
    Long-term remembered facts about the user (e.g. name, favorite tools, hobbies, goals).
    """
    FACT_TYPES = [
        ('identity', 'Identity / Personal Info'),
        ('preference', 'Preference / Like / Dislike'),
        ('project', 'Project / Task Info'),
        ('habit', 'Habit / Schedule'),
        ('general', 'General Fact'),
    ]

    fact_type = models.CharField(max_length=32, choices=FACT_TYPES, default='general', db_index=True)
    content = models.TextField(help_text="The factual statement or memory snippet")
    confidence = models.FloatField(default=1.0, help_text="Confidence score from 0.0 to 1.0")
    source = models.CharField(max_length=64, default="conversation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"[{self.fact_type}] {self.content[:50]}"


class ChatHistory(models.Model):
    """
    Persistent multi-turn chat messages with companion emotional metadata.
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]

    session_id = models.CharField(max_length=64, default='default', db_index=True)
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField()
    expression = models.CharField(max_length=32, default='normal')
    animation = models.CharField(max_length=32, default='none')
    thinking = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.session_id}] {self.role}: {self.content[:40]}"


# Compatibility aliases
MemoryItem = FactMemory
MessageLog = ChatHistory

