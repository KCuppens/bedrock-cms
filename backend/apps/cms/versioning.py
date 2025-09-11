"""
Versioning and audit models for the CMS.

This module provides content versioning, autosave, and audit trail functionality.
"""

import uuid
from datetime import timedelta
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

if TYPE_CHECKING:
    from .models import Page


User = get_user_model()


class PageRevision(models.Model):
    """
    Store snapshots of page content for versioning and autosave.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page = models.ForeignKey(
        'cms.Page',
        on_delete=models.CASCADE,
        related_name='revisions',
        help_text="Page this revision belongs to"
    )
    snapshot = models.JSONField(
        help_text="Complete page data snapshot including blocks, seo, and metadata"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='page_revisions',
        help_text="User who created this revision"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_published_snapshot = models.BooleanField(
        default=False,
        help_text="True if this revision represents a published state"
    )
    is_autosave = models.BooleanField(
        default=False,
        help_text="True if this revision was created by autosave"
    )
    comment = models.TextField(
        blank=True,
        help_text="Optional comment about this revision"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['page', '-created_at']),
            models.Index(fields=['page', 'is_published_snapshot']),
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['is_published_snapshot', '-created_at']),
        ]
        verbose_name = 'Page Revision'
        verbose_name_plural = 'Page Revisions'
    
    def __str__(self):
        snapshot_type = "Published" if self.is_published_snapshot else ("Autosave" if self.is_autosave else "Manual")
        return f"{self.page.title} - {snapshot_type} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
    
    @classmethod
    def create_snapshot(cls, page: 'Page', user: User = None, is_published: bool = False, 
                       is_autosave: bool = False, comment: str = "") -> 'PageRevision':
        """
        Create a new revision snapshot of a page.
        
        Args:
            page: Page to snapshot
            user: User creating the snapshot
            is_published: Whether this is a published snapshot
            is_autosave: Whether this is an autosave snapshot
            comment: Optional comment
            
        Returns:
            Created PageRevision instance
        """
        # Create complete snapshot of page data
        snapshot_data = {
            'title': page.title,
            'slug': page.slug,
            'path': page.path,
            'blocks': page.blocks,
            'seo': page.seo,
            'status': page.status,
            'published_at': page.published_at.isoformat() if page.published_at else None,
            'parent_id': page.parent.id if page.parent else None,
            'position': page.position,
            'locale_id': page.locale.id if page.locale else None,
            'group_id': str(page.group_id),
            'preview_token': str(page.preview_token),
            'created_at': page.created_at.isoformat(),
            'updated_at': page.updated_at.isoformat(),
        }
        
        # Create the revision with explicit field values
        revision_data = {
            'page': page,
            'snapshot': snapshot_data,
            'created_by': user,
            'is_published_snapshot': bool(is_published) if is_published is not None else False,
            'is_autosave': bool(is_autosave) if is_autosave is not None else False,
        }
        
        # Only add comment if it's provided and not empty
        if comment:
            revision_data['comment'] = comment
            
        return cls.objects.create(**revision_data)
    
    @classmethod
    def should_create_autosave(cls, page: 'Page', user: User) -> bool:
        """
        Check if an autosave revision should be created.
        
        Throttles autosave creation to max one per minute per page per user.
        
        Args:
            page: Page to check
            user: User making changes
            
        Returns:
            True if autosave should be created
        """
        if not user:
            return False
        
        # Check for recent autosave by this user
        since = timezone.now() - timedelta(seconds=60)
        recent_autosave = cls.objects.filter(
            page=page,
            created_by=user,
            is_autosave=True,
            created_at__gte=since
        ).exists()
        
        return not recent_autosave
    
    def restore_to_page(self) -> 'Page':
        """
        Restore this revision's content to the page (as draft).
        
        Returns:
            Updated Page instance
        """
        snapshot = self.snapshot
        page = self.page
        
        # Restore content fields (excluding metadata that shouldn't change)
        page.title = snapshot.get('title', page.title)
        page.slug = snapshot.get('slug', page.slug)
        page.blocks = snapshot.get('blocks', [])
        page.seo = snapshot.get('seo', {})
        
        # Always restore as draft unless it was a published snapshot
        if not self.is_published_snapshot:
            page.status = 'draft'
            page.published_at = None
        
        page.save()
        return page
    
    def get_block_count(self) -> int:
        """Get the number of blocks in this revision."""
        return len(self.snapshot.get('blocks', []))


class AuditEntry(models.Model):
    """
    Audit log entry for tracking user actions.
    """
    
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('publish', 'Publish'),
        ('unpublish', 'Unpublish'),
        ('move', 'Move'),
        ('revert', 'Revert'),
        ('duplicate', 'Duplicate'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_entries',
        help_text="User who performed the action"
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        help_text="Type of action performed"
    )
    
    # Generic relation to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # For backward compatibility with the TODO spec
    model_label = models.CharField(
        max_length=100,
        help_text="App.Model format (e.g., 'cms.Page')"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Metadata about the action
    meta = models.JSONField(
        default=dict,
        help_text="Additional metadata about the action"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['actor', '-created_at']),
            models.Index(fields=['content_type', 'object_id', '-created_at']),
            models.Index(fields=['model_label', 'object_id', '-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]
        verbose_name = 'Audit Entry'
        verbose_name_plural = 'Audit Entries'
    
    def __str__(self):
        actor_name = self.actor.email if self.actor else "System"
        return f"{actor_name} performed {self.action} on {self.model_label}#{self.object_id}"
    
    @classmethod
    def log(cls, actor: User, action: str, obj: models.Model, 
            meta: Dict[str, Any] = None, request = None) -> 'AuditEntry':
        """
        Create an audit log entry.
        
        Args:
            actor: User performing the action
            action: Action being performed
            obj: Object being acted upon
            meta: Additional metadata
            request: HTTP request (for IP/user agent)
            
        Returns:
            Created AuditEntry instance
        """
        if meta is None:
            meta = {}
        
        # Extract request metadata
        ip_address = None
        user_agent = ''
        if request:
            ip_address = cls._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Get model label
        model_label = f"{obj._meta.app_label}.{obj._meta.model_name}"
        
        return cls.objects.create(
            actor=actor,
            action=action,
            content_object=obj,
            model_label=model_label,
            object_id=obj.pk,
            meta=meta,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def _get_client_ip(request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class RevisionDiffer:
    """
    Utility class for computing diffs between page revisions.
    """
    
    @staticmethod
    def diff_revisions(old_revision: PageRevision, new_revision: PageRevision) -> Dict[str, Any]:
        """
        Compare two revisions and return a diff.
        
        Args:
            old_revision: Earlier revision
            new_revision: Later revision
            
        Returns:
            Dict containing diff information
        """
        old_data = old_revision.snapshot
        new_data = new_revision.snapshot
        
        diff = {
            'old_revision_id': old_revision.id,  # Return UUID object, not string
            'new_revision_id': new_revision.id,  # Return UUID object, not string
            'created_at': new_revision.created_at.isoformat(),
            'changes': {}
        }
        
        # Compare basic fields
        basic_fields = ['title', 'slug', 'path', 'status', 'published_at']
        for field in basic_fields:
            old_val = old_data.get(field)
            new_val = new_data.get(field)
            if old_val != new_val:
                diff['changes'][field] = {
                    'old': old_val,
                    'new': new_val
                }
        
        # Compare SEO
        old_seo = old_data.get('seo', {})
        new_seo = new_data.get('seo', {})
        if old_seo != new_seo:
            diff['changes']['seo'] = {
                'old': old_seo,
                'new': new_seo
            }
        
        # Compare blocks (detailed block-level diff)
        block_diff = RevisionDiffer._diff_blocks(
            old_data.get('blocks', []),
            new_data.get('blocks', [])
        )
        if block_diff['has_changes']:
            diff['changes']['blocks'] = block_diff
        
        diff['has_changes'] = len(diff['changes']) > 0
        
        return diff
    
    @staticmethod
    def _diff_blocks(old_blocks: List[Dict], new_blocks: List[Dict]) -> Dict[str, Any]:
        """
        Compare block arrays and return detailed diff.
        
        Args:
            old_blocks: Original blocks
            new_blocks: Updated blocks
            
        Returns:
            Dict containing block-level changes
        """
        diff = {
            'has_changes': False,
            'added': [],
            'removed': [],
            'modified': [],
            'reordered': False
        }
        
        # Simple length check
        if len(old_blocks) != len(new_blocks):
            diff['has_changes'] = True
        
        # Compare each block position
        max_len = max(len(old_blocks), len(new_blocks))
        
        for i in range(max_len):
            old_block = old_blocks[i] if i < len(old_blocks) else None
            new_block = new_blocks[i] if i < len(new_blocks) else None
            
            if old_block is None and new_block is not None:
                # Block added
                diff['added'].append({
                    'index': i,
                    'block': new_block
                })
                diff['has_changes'] = True
                
            elif old_block is not None and new_block is None:
                # Block removed
                diff['removed'].append({
                    'index': i,
                    'block': old_block
                })
                diff['has_changes'] = True
                
            elif old_block != new_block:
                # Block modified
                diff['modified'].append({
                    'index': i,
                    'old': old_block,
                    'new': new_block
                })
                diff['has_changes'] = True
        
        return diff
    
    @staticmethod
    def diff_current_page(page: 'Page', revision: PageRevision) -> Dict[str, Any]:
        """
        Compare current page state with a revision.
        
        Args:
            page: Current page
            revision: Revision to compare against
            
        Returns:
            Dict containing diff information
        """
        # Create a temporary revision-like snapshot of current page
        current_data = {
            'title': page.title,
            'slug': page.slug,
            'path': page.path,
            'blocks': page.blocks,
            'seo': page.seo,
            'status': page.status,
            'published_at': page.published_at.isoformat() if page.published_at else None,
        }
        
        # Create temporary revision object for diffing
        current_revision = PageRevision(
            id=uuid.uuid4(),
            snapshot=current_data,
            created_at=timezone.now()
        )
        
        diff = RevisionDiffer.diff_revisions(revision, current_revision)
        # Override the new_revision_id to None since it's the current page state
        diff['old_revision_id'] = revision.id  # Keep as UUID, not string
        diff['new_revision_id'] = None
        return diff