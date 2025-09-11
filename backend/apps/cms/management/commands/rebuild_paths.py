from django.core.management.base import BaseCommand
from django.db import transaction
from apps.cms.models import Page
from apps.i18n.models import Locale


class Command(BaseCommand):
    help = 'Rebuild page paths and resequence positions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--locale',
            type=str,
            help='Locale code to rebuild (default: all locales)'
        )
        parser.add_argument(
            '--root',
            type=int,
            help='Root page ID to rebuild subtree (default: rebuild all)'
        )

    def handle(self, *args, **options):
        locale_code = options.get('locale')
        root_id = options.get('root')

        # Filter by locale if provided
        locales = Locale.objects.all()
        if locale_code:
            locales = locales.filter(code=locale_code)
            if not locales.exists():
                self.stdout.write(
                    self.style.ERROR(f'Locale "{locale_code}" not found')
                )
                return

        for locale in locales:
            self.stdout.write(f'Processing locale: {locale.code}')
            
            # Get pages to rebuild
            pages_query = Page.objects.filter(locale=locale)
            if root_id:
                try:
                    root_page = Page.objects.get(id=root_id, locale=locale)
                    # Get root and all descendants
                    pages_query = pages_query.filter(
                        path__startswith=root_page.path
                    )
                except Page.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'Root page {root_id} not found for locale {locale.code}')
                    )
                    continue

            with transaction.atomic():
                # Rebuild paths for all pages
                updated_count = 0
                for page in pages_query.select_for_update():
                    old_path = page.path
                    new_path = page.compute_path()
                    if old_path != new_path:
                        page.path = new_path
                        page.save(update_fields=['path'])
                        updated_count += 1

                self.stdout.write(f'  Updated {updated_count} page paths')

                # Resequence positions for each parent group
                parent_ids = set(pages_query.values_list('parent_id', flat=True))
                for parent_id in parent_ids:
                    Page.siblings_resequence(parent_id)

                self.stdout.write(f'  Resequenced positions for {len(parent_ids)} parent groups')

        self.stdout.write(
            self.style.SUCCESS('Successfully rebuilt paths and positions')
        )