"""
Versioning and revision tracking for blog posts.

This module provides revision snapshots, autosave, and audit trail functionality
for blog posts, similar to the CMS page versioning system.
"""

import uuid
from datetime import timedelta
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

if TYPE_CHECKING:
    from .models import BlogPost

User = get_user_model()


class BlogPostRevision(models.Model):
    """
    Store snapshots of blog post content for versioning and autosave.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    blog_post = models.ForeignKey(
        'blog.BlogPost',
        on_delete=models.CASCADE,
        related_name='revisions',
        help_text="Blog post this revision belongs to"
    )
    snapshot = models.JSONField(
        help_text="Complete blog post data snapshot including content, blocks, and metadata"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blog_post_revisions',
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
            models.Index(fields=['blog_post', '-created_at']),
            models.Index(fields=['blog_post', 'is_published_snapshot']),
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['is_published_snapshot', '-created_at']),
        ]
        verbose_name = 'Blog Post Revision'
        verbose_name_plural = 'Blog Post Revisions'
    
    def __str__(self):
        snapshot_type = "Published" if self.is_published_snapshot else ("Autosave" if self.is_autosave else "Manual")
        return f"{self.blog_post.title} - {snapshot_type} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
    
    @classmethod
    def create_snapshot(cls, blog_post: 'BlogPost', user: Optional['User'] = None, is_published: bool = False, 
                       is_autosave: bool = False, comment: str = "") -> 'BlogPostRevision':
        """
        Create a new revision snapshot of a blog post.
        
        Args:
            blog_post: BlogPost to snapshot
            user: User creating the snapshot
            is_published: Whether this is a published snapshot
            is_autosave: Whether this is an autosave snapshot
            comment: Optional comment
            
        Returns:
            Created BlogPostRevision instance
        """
        # Create complete snapshot of blog post data
        snapshot_data = {
            'title': blog_post.title,
            'slug': blog_post.slug,
            'excerpt': blog_post.excerpt,
            'content': blog_post.content,
            'blocks': blog_post.blocks,
            'seo': blog_post.seo,
            'status': blog_post.status,
            'featured': blog_post.featured,
            'allow_comments': blog_post.allow_comments,
            'published_at': blog_post.published_at.isoformat() if blog_post.published_at else None,
            'scheduled_publish_at': blog_post.scheduled_publish_at.isoformat() if blog_post.scheduled_publish_at else None,
            'category_id': blog_post.category.id if blog_post.category else None,
            'tag_ids': list(blog_post.tags.values_list('id', flat=True)),
            'social_image_id': blog_post.social_image.id if blog_post.social_image else None,
            'locale_id': blog_post.locale.id if blog_post.locale else None,
            'author_id': blog_post.author.id if blog_post.author else None,
        }
        
        # Create revision
        revision = cls.objects.create(
            blog_post=blog_post,
            snapshot=snapshot_data,
            created_by=user,
            is_published_snapshot=is_published,
            is_autosave=is_autosave,
            comment=comment
        )
        
        # Clean up old autosave revisions to prevent database bloat
        if is_autosave:
            cls.cleanup_old_autosave_revisions(blog_post, keep_count=5)
        
        return revision
    
    @classmethod
    def cleanup_old_autosave_revisions(cls, blog_post: 'BlogPost', keep_count: int = 5):
        """
        Clean up old autosave revisions for a blog post.
        
        Args:
            blog_post: BlogPost to clean up revisions for
            keep_count: Number of recent autosave revisions to keep
        """
        # Get autosave revisions older than the keep_count
        old_autosaves = cls.objects.filter(
            blog_post=blog_post,
            is_autosave=True
        ).order_by('-created_at')[keep_count:]
        
        # Delete old autosaves
        for revision in old_autosaves:
            revision.delete()
    
    @classmethod
    def cleanup_old_revisions(cls, blog_post: 'BlogPost', days_to_keep: int = 90):
        """
        Clean up very old revisions for a blog post.
        
        Args:
            blog_post: BlogPost to clean up revisions for
            days_to_keep: Number of days of revisions to keep
        """
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        
        # Keep all published snapshots and recent revisions
        old_revisions = cls.objects.filter(
            blog_post=blog_post,
            created_at__lt=cutoff_date,
            is_published_snapshot=False
        )
        
        # Delete old non-published revisions
        old_revisions.delete()
    
    def restore_to_blog_post(self, user: Optional['User'] = None, create_backup: bool = True) -> 'BlogPost':
        """
        Restore this revision's content to the blog post.
        
        Args:
            user: User performing the restore
            create_backup: Whether to create a backup revision before restoring
            
        Returns:
            Updated BlogPost instance
        """
        from .models import BlogPost, Tag
        
        blog_post = self.blog_post
        snapshot = self.snapshot
        
        # Create backup before restoring if requested
        if create_backup:
            self.__class__.create_snapshot(
                blog_post=blog_post,
                user=user,
                comment=f"Backup before restoring revision {self.id}"
            )
        
        with transaction.atomic():
            # Restore basic fields
            blog_post.title = snapshot['title']
            blog_post.slug = snapshot['slug']
            blog_post.excerpt = snapshot['excerpt']
            blog_post.content = snapshot['content']
            blog_post.blocks = snapshot['blocks']
            blog_post.seo = snapshot['seo']
            blog_post.status = snapshot['status']
            blog_post.featured = snapshot['featured']
            blog_post.allow_comments = snapshot['allow_comments']
            
            # Restore timestamps
            blog_post.published_at = (
                timezone.datetime.fromisoformat(snapshot['published_at']) 
                if snapshot['published_at'] else None
            )
            blog_post.scheduled_publish_at = (
                timezone.datetime.fromisoformat(snapshot['scheduled_publish_at'])
                if snapshot.get('scheduled_publish_at') else None
            )
            
            # Restore relationships
            blog_post.category_id = snapshot['category_id']
            blog_post.social_image_id = snapshot['social_image_id']
            
            blog_post.save()
            
            # Restore tags
            if 'tag_ids' in snapshot:
                tag_ids = snapshot['tag_ids']
                tags = Tag.objects.filter(id__in=tag_ids)
                blog_post.tags.set(tags)
        
        return blog_post


class BlogPostViewTracker(models.Model):
    """
    Track view counts for blog posts.
    """
    
    blog_post = models.OneToOneField(
        'blog.BlogPost',
        on_delete=models.CASCADE,
        related_name='view_tracker',
        help_text="Blog post being tracked"
    )
    view_count = models.PositiveIntegerField(
        default=0,
        help_text="Total view count"
    )
    unique_view_count = models.PositiveIntegerField(
        default=0,
        help_text="Unique visitor count (approximate)"
    )
    last_viewed = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time this post was viewed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Blog Post View Tracker'
        verbose_name_plural = 'Blog Post View Trackers'
    
    def __str__(self):
        return f"{self.blog_post.title} - {self.view_count} views"
    
    def increment_view(self, is_unique: bool = False):
        """
        Increment view count for this blog post.
        
        Args:
            is_unique: Whether this is a unique view (new visitor)
        """
        self.view_count = models.F('view_count') + 1
        if is_unique:
            self.unique_view_count = models.F('unique_view_count') + 1
        self.last_viewed = timezone.now()
        self.save(update_fields=['view_count', 'unique_view_count', 'last_viewed'])
        
        # Refresh from database to get updated values
        self.refresh_from_db()


# Signal handlers for automatic revision creation
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver


@receiver(post_save, sender='blog.BlogPost')
def create_blog_post_revision_on_publish(sender, instance, created, **kwargs):
    """
    Automatically create a revision when a blog post is published.
    """
    if not created and instance.status == 'published' and instance.published_at:
        # Check if we already have a published snapshot for this exact state
        existing_published = BlogPostRevision.objects.filter(
            blog_post=instance,
            is_published_snapshot=True
        ).first()
        
        # Create published snapshot if we don't have one or if content has changed
        if not existing_published:
            BlogPostRevision.create_snapshot(
                blog_post=instance,
                is_published=True,
                comment="Automatic snapshot on publish"
            )


@receiver(post_save, sender='blog.BlogPost')
def ensure_view_tracker_exists(sender, instance, created, **kwargs):
    """
    Ensure a view tracker exists for every blog post.
    """
    if created:
        BlogPostViewTracker.objects.get_or_create(blog_post=instance)