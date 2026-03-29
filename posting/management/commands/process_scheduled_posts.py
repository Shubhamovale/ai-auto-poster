from django.core.management.base import BaseCommand

from posting.tasks import publish_due_posts_task


class Command(BaseCommand):
    help = "Publish all scheduled posts that are due."

    def handle(self, *args, **options):
        processed = publish_due_posts_task()
        if not processed:
            self.stdout.write(self.style.SUCCESS("No scheduled posts are due."))
            return

        self.stdout.write(self.style.SUCCESS(f"Processed {len(processed)} post(s)."))
