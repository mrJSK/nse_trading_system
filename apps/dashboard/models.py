# apps/dashboard/models.py
from django.db import models
from django.contrib.auth.models import User
import json

class TaskExecution(models.Model):
    TASK_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    task_name = models.CharField(max_length=200)
    command = models.TextField()
    parameters = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='pending')
    output = models.TextField(blank=True)
    error_log = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    # ✅ FIXED: Make executed_by optional
    executed_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']

class DashboardWidget(models.Model):
    name = models.CharField(max_length=100)
    widget_type = models.CharField(max_length=50)
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    config = models.JSONField(default=dict)
