from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from apps.cms.seo import SeoSettings
from apps.cms.serializers.seo import SeoSettingsSerializer
from apps.i18n.models import Locale


class SeoSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing SEO settings per locale.
    """
    queryset = SeoSettings.objects.select_related('locale', 'default_og_asset').all()
    serializer_class = SeoSettingsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter by active locales."""
        queryset = super().get_queryset()
        
        # Filter by locale code if provided
        locale_code = self.request.query_params.get('locale')
        if locale_code:
            queryset = queryset.filter(locale__code=locale_code)
        
        # Filter by active locales
        active_only = self.request.query_params.get('active_only')
        if active_only and active_only.lower() == 'true':
            queryset = queryset.filter(locale__is_active=True)
        
        return queryset.order_by('locale__code')
    
    def list(self, request, *args, **kwargs):
        """List all SEO settings or create defaults for missing locales."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Check if we should include missing locales with defaults
        include_defaults = request.query_params.get('include_defaults', 'false').lower() == 'true'
        
        if include_defaults:
            # Get all active locales
            all_locales = Locale.objects.filter(is_active=True)
            existing_locale_ids = set(queryset.values_list('locale_id', flat=True))
            
            # Create default entries for missing locales
            defaults = []
            for locale in all_locales:
                if locale.id not in existing_locale_ids:
                    defaults.append({
                        'id': None,
                        'locale': locale.id,
                        'locale_code': locale.code,
                        'locale_name': locale.name,
                        'title_suffix': '',
                        'default_description': '',
                        'default_og_asset': None,
                        'default_og_image_url': None,
                        'robots_default': 'index,follow',
                        'jsonld_default': []
                    })
            
            return Response({
                'count': len(serializer.data) + len(defaults),
                'results': serializer.data + defaults
            })
        
        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        })
    
    def retrieve(self, request, pk=None):
        """Get SEO settings for a specific locale by locale ID or code."""
        # Try to get by primary key first
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except:
            pass
        
        # Try to get by locale code
        locale_code = pk
        try:
            locale = Locale.objects.get(code=locale_code)
            instance = SeoSettings.objects.get(locale=locale)
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Locale.DoesNotExist:
            return Response(
                {'error': f'Locale with code {locale_code} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except SeoSettings.DoesNotExist:
            # Return default settings for this locale
            return Response({
                'id': None,
                'locale': locale.id,
                'locale_code': locale.code,
                'locale_name': locale.name,
                'title_suffix': '',
                'default_description': '',
                'default_og_asset': None,
                'default_og_image_url': None,
                'robots_default': 'index,follow',
                'jsonld_default': []
            })
    
    def create(self, request, *args, **kwargs):
        """Create SEO settings for a locale."""
        locale_id = request.data.get('locale_id') or request.data.get('locale')
        
        if not locale_id:
            return Response(
                {'error': 'locale or locale_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if settings already exist for this locale
        if SeoSettings.objects.filter(locale_id=locale_id).exists():
            return Response(
                {'error': f'SEO settings already exist for this locale'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Clear cache
        cache.delete(f'seo_settings_{locale_id}')
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        """Update SEO settings."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Clear cache
        cache.delete(f'seo_settings_{instance.locale_id}')
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_locale(self, request):
        """Get SEO settings by locale code."""
        locale_code = request.query_params.get('code')
        
        if not locale_code:
            return Response(
                {'error': 'locale code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            locale = Locale.objects.get(code=locale_code)
            settings = SeoSettings.objects.get(locale=locale)
            serializer = self.get_serializer(settings)
            return Response(serializer.data)
        except Locale.DoesNotExist:
            return Response(
                {'error': f'Locale {locale_code} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except SeoSettings.DoesNotExist:
            # Return defaults
            return Response({
                'locale': locale.id,
                'locale_code': locale.code,
                'locale_name': locale.name,
                'title_suffix': '',
                'default_description': '',
                'default_og_asset': None,
                'robots_default': 'index,follow',
                'jsonld_default': []
            })
    
    @action(detail=False, methods=['post'])
    def duplicate(self, request):
        """Duplicate SEO settings from one locale to another."""
        source_locale_id = request.data.get('source_locale')
        target_locale_id = request.data.get('target_locale')
        
        if not source_locale_id or not target_locale_id:
            return Response(
                {'error': 'source_locale and target_locale are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if target already exists
        if SeoSettings.objects.filter(locale_id=target_locale_id).exists():
            return Response(
                {'error': 'SEO settings already exist for target locale'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get source settings
            source = SeoSettings.objects.get(locale_id=source_locale_id)
            
            # Create duplicate
            duplicate = SeoSettings.objects.create(
                locale_id=target_locale_id,
                title_suffix=source.title_suffix,
                default_description=source.default_description,
                default_og_asset=source.default_og_asset,
                robots_default=source.robots_default,
                jsonld_default=source.jsonld_default
            )
            
            serializer = self.get_serializer(duplicate)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except SeoSettings.DoesNotExist:
            return Response(
                {'error': 'Source SEO settings not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """Bulk update SEO settings for multiple locales."""
        updates = request.data.get('updates', [])
        
        if not updates:
            return Response(
                {'error': 'No updates provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = []
        errors = []
        
        for update in updates:
            locale_id = update.get('locale') or update.get('locale_id')
            if not locale_id:
                errors.append({'error': 'locale is required for each update'})
                continue
            
            try:
                instance, created = SeoSettings.objects.get_or_create(
                    locale_id=locale_id,
                    defaults={
                        'title_suffix': update.get('title_suffix', ''),
                        'default_description': update.get('default_description', ''),
                        'robots_default': update.get('robots_default', 'index,follow'),
                        'jsonld_default': update.get('jsonld_default', [])
                    }
                )
                
                if not created:
                    # Update existing
                    for field in ['title_suffix', 'default_description', 'robots_default', 'jsonld_default']:
                        if field in update:
                            setattr(instance, field, update[field])
                    instance.save()
                
                serializer = self.get_serializer(instance)
                results.append(serializer.data)
                
                # Clear cache
                cache.delete(f'seo_settings_{locale_id}')
                
            except Exception as e:
                errors.append({
                    'locale_id': locale_id,
                    'error': str(e)
                })
        
        return Response({
            'updated': results,
            'errors': errors
        })
    
    @action(detail=False, methods=['get'])
    def preview(self, request):
        """Preview how meta tags will look for a given page."""
        locale_code = request.query_params.get('locale', 'en')
        page_title = request.query_params.get('page_title', 'Page Title')
        page_description = request.query_params.get('page_description', '')
        
        try:
            locale = Locale.objects.get(code=locale_code)
            settings = SeoSettings.objects.get(locale=locale)
        except (Locale.DoesNotExist, SeoSettings.DoesNotExist):
            # Use defaults
            title_suffix = ' | Bedrock CMS'
            default_description = ''
            default_og_image = ''
        else:
            title_suffix = settings.title_suffix
            default_description = settings.default_description
            default_og_image = settings.default_og_asset.url if settings.default_og_asset else ''
        
        # Format meta title
        meta_title = f"{page_title}{title_suffix}"
        
        # Use page description or fall back to default
        meta_description = page_description or default_description
        
        return Response({
            'title': meta_title,
            'description': meta_description,
            'og:title': meta_title,
            'og:description': meta_description,
            'og:image': default_og_image,
            'twitter:title': meta_title,
            'twitter:description': meta_description,
            'twitter:image': default_og_image
        })